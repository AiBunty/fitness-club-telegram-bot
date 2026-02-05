const fs = require('fs');
const path = require('path');
const axios = require('axios');
const Handlebars = require('handlebars');
const dayjs = require('dayjs');
const puppeteer = require('puppeteer');
const { formatINR, round2 } = require('../utils/money');
const logger = require('../utils/logger');

const templatePath = path.join(__dirname, 'receiptTemplate.html');
const stylesPath = path.join(__dirname, 'receiptStyles.css');

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
  const computedItems = items.map((item) => {
    const qty = Number(item.qty || 0);
    const rate = Number(item.rate || 0);
    const discountPercent = Number(item.discountPercent || 0);
    const gstPercent = Number(item.gstPercent || 0);

    const taxable = round2(qty * rate * (1 - discountPercent / 100));
    const gstAmount = round2(taxable * (gstPercent / 100));
    const lineTotal = round2(taxable + gstAmount);

    return {
      ...item,
      taxable,
      gstAmount,
      lineTotal,
    };
  });

  const subtotal = round2(computedItems.reduce((sum, i) => sum + i.taxable, 0));
  const gstTotal = round2(computedItems.reduce((sum, i) => sum + i.gstAmount, 0));
  const shipping = round2(Number(charges.shipping || 0) + Number(charges.serviceCharge || 0));
  const grandTotal = round2(subtotal + gstTotal + shipping);

  return { computedItems, summary: { subtotal, gstTotal, shipping, grandTotal } };
};

const buildReceiptFromInvoice = (invoiceData, receiptOverrides = {}) => {
  const invoiceId = invoiceData?.invoice?.invoiceId || '';
  const receiptDate = receiptOverrides.receiptDate || dayjs().format('YYYY-MM-DD');

  return {
    ...invoiceData,
    receipt: {
      receiptId: receiptOverrides.receiptId || `RCPT-${dayjs().format('YYYYMMDD-HHmm')}`,
      receiptDate,
      paymentMethod: receiptOverrides.paymentMethod || 'UPI',
      transactionId: receiptOverrides.transactionId || '',
      amountPaid: receiptOverrides.amountPaid,
      paymentNotes: receiptOverrides.paymentNotes || '',
    },
    invoice: {
      ...invoiceData.invoice,
      invoiceId,
    },
  };
};

const validateReceiptData = (data, invoiceGrandTotal) => {
  const errors = [];
  const receipt = data.receipt || {};
  const invoiceId = data.invoice?.invoiceId || '';

  if (!receipt.receiptId) errors.push('receiptId is required');
  if (!receipt.receiptDate) errors.push('receiptDate is required');
  if (!receipt.paymentMethod) errors.push('paymentMethod is required');
  if (!invoiceId) errors.push('invoiceId is required');

  const amountPaid = Number(receipt.amountPaid || 0);
  if (amountPaid <= 0) errors.push('amountPaid must be greater than 0');

  if (typeof invoiceGrandTotal === 'number' && amountPaid > 0) {
    const diff = Math.abs(amountPaid - invoiceGrandTotal);
    if (diff > 0.01) {
      errors.push('amountPaid does not match invoice grand total');
    }
  }

  return { ok: errors.length === 0, errors };
};

const renderReceiptHtml = async (data, config) => {
  const template = fs.readFileSync(templatePath, 'utf8');
  const styles = fs.readFileSync(stylesPath, 'utf8');

  const logoUrl = await toDataUrl(data.business.logoUrl || config.business.logoUrl);
  const { summary } = computeTotals(data.items, data.charges);

  const amountPaid = round2(Number(data.receipt.amountPaid || summary.grandTotal));
  const balanceDue = round2(Math.max(summary.grandTotal - amountPaid, 0));

  const viewModel = {
    styles,
    logoUrl,
    business: {
      ...config.business,
      ...data.business,
    },
    customer: data.customer,
    invoice: data.invoice,
    receipt: {
      ...data.receipt,
      paymentMethod: data.receipt.paymentMethod || 'UPI',
      transactionId: data.receipt.transactionId || 'N/A',
    },
    summary: {
      grandTotal: formatINR(summary.grandTotal),
      amountPaid: formatINR(amountPaid),
      balanceDue: formatINR(balanceDue),
      gstInfo: summary.gstTotal > 0 ? formatINR(summary.gstTotal) : 'Yes',
    },
    terms: [
      'This is a system-generated receipt; signature not required.',
      `For queries contact: ${config.business.phone}`,
      'Disputes subject to Nashik jurisdiction.',
    ],
    generatedOn: dayjs().format('YYYY-MM-DD HH:mm'),
  };

  const compile = Handlebars.compile(template, { noEscape: true });
  return compile(viewModel);
};

const generateReceiptPdf = async (data, config, outputPath) => {
  const totals = computeTotals(data.items, data.charges);
  const validation = validateReceiptData(data, totals.summary.grandTotal);
  if (!validation.ok) {
    throw new Error(`Receipt validation failed: ${validation.errors.join(', ')}`);
  }

  const html = await renderReceiptHtml(data, config);

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

module.exports = { generateReceiptPdf, buildReceiptFromInvoice, computeTotals };
