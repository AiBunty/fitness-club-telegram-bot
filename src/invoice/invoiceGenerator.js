const fs = require('fs');
const path = require('path');
const axios = require('axios');
const Handlebars = require('handlebars');
const dayjs = require('dayjs');
const puppeteer = require('puppeteer');
const { formatINR, round2 } = require('../utils/money');
const logger = require('../utils/logger');

const templatePath = path.join(__dirname, 'invoiceTemplate.html');
const stylesPath = path.join(__dirname, 'invoiceStyles.css');

const toDataUrl = async (url) => {
  if (!url) return '';
  try {
    const res = await axios.get(url, { responseType: 'arraybuffer', timeout: 15000 });
    const contentType = res.headers['content-type'] || 'image/jpeg';
    const base64 = Buffer.from(res.data, 'binary').toString('base64');
    return `data:${contentType};base64,${base64}`;
  } catch (err) {
    logger.warn('Logo fetch failed, using URL directly: %s', err.message);
    return url;
  }
};

const computeTotals = (items, charges = {}) => {
  const computedItems = items.map((item, index) => {
    const qty = Number(item.qty || 0);
    const rate = Number(item.rate || 0);
    const discountPercent = Number(item.discountPercent || 0);
    const gstPercent = Number(item.gstPercent || 0);

    const taxable = round2(qty * rate * (1 - discountPercent / 100));
    const gstAmount = round2(taxable * (gstPercent / 100));
    const lineTotal = round2(taxable + gstAmount);

    return {
      ...item,
      sr: index + 1,
      taxable,
      gstAmount,
      lineTotal,
      rateFormatted: formatINR(rate),
      taxableFormatted: formatINR(taxable),
      gstAmountFormatted: formatINR(gstAmount),
      lineTotalFormatted: formatINR(lineTotal),
    };
  });

  const subtotal = round2(computedItems.reduce((sum, i) => sum + i.taxable, 0));
  const gstTotal = round2(computedItems.reduce((sum, i) => sum + i.gstAmount, 0));
  const discountTotal = round2(
    computedItems.reduce((sum, i) => {
      const base = Number(i.qty) * Number(i.rate);
      return sum + (base - i.taxable);
    }, 0)
  );

  const shipping = round2(Number(charges.shipping || 0) + Number(charges.serviceCharge || 0));
  const grandTotal = round2(subtotal + gstTotal + shipping);

  return {
    computedItems,
    summary: {
      subtotal,
      gstTotal,
      discountTotal,
      shipping,
      grandTotal,
      roundOff: 0,
    },
  };
};

const buildTerms = (data, config) => {
  if (Array.isArray(data.terms) && data.terms.length) {
    return data.terms;
  }

  const terms = [
    `Payment due within ${config.invoice.paymentDueDays} days.`,
    'This is a system-generated invoice; signature not required.',
    'Disputes subject to Nashik jurisdiction.',
  ];

  if (config.invoice.includeReturnRefund) {
    terms.push(config.invoice.returnRefundText);
  }

  return terms;
};

const renderInvoiceHtml = async (data, config) => {
  const template = fs.readFileSync(templatePath, 'utf8');
  const styles = fs.readFileSync(stylesPath, 'utf8');

  const logoUrl = await toDataUrl(data.business.logoUrl || config.business.logoUrl);

  const { computedItems, summary } = computeTotals(data.items, data.charges);

  const invoiceTitle = data.business.gstin || config.business.gstin ? 'TAX INVOICE' : 'INVOICE';
  const statusClass = String(data.invoice.status || '').toUpperCase() === 'PAID' ? 'status-paid' : 'status-unpaid';

  const hasPaymentDetails = Boolean(
    data.payment?.upiId ||
      data.payment?.bankName ||
      data.payment?.accountNo ||
      data.payment?.ifsc ||
      data.payment?.razorpayLink
  );

  const viewModel = {
    styles,
    invoiceTitle,
    statusClass,
    logoUrl,
    business: {
      ...config.business,
      ...data.business,
    },
    customer: data.customer,
    invoice: {
      ...data.invoice,
      dueDate: data.invoice.dueDate || dayjs(data.invoice.invoiceDate).add(config.invoice.paymentDueDays, 'day').format('YYYY-MM-DD'),
      placeOfSupply: data.invoice.placeOfSupply || 'N/A',
    },
    items: computedItems,
    summary: {
      subtotal: formatINR(summary.subtotal),
      discountTotal: summary.discountTotal > 0 ? formatINR(summary.discountTotal) : '',
      shipping: summary.shipping > 0 ? formatINR(summary.shipping) : '',
      gstTotal: formatINR(summary.gstTotal),
      roundOff: summary.roundOff ? formatINR(summary.roundOff) : '',
      grandTotal: formatINR(summary.grandTotal),
    },
    payment: {
      ...config.payment,
      ...data.payment,
    },
    hasPaymentDetails,
    terms: buildTerms(data, config),
    generatedOn: dayjs().format('YYYY-MM-DD HH:mm'),
  };

  const compile = Handlebars.compile(template, { noEscape: true });
  return compile(viewModel);
};

const generateInvoicePdf = async (data, config, outputPath) => {
  const html = await renderInvoiceHtml(data, config);

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle0' });

    await page.pdf({
      path: outputPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '12mm',
        right: '12mm',
        bottom: '12mm',
        left: '12mm',
      },
    });
  } finally {
    await browser.close();
  }

  return outputPath;
};

module.exports = { generateInvoicePdf };
