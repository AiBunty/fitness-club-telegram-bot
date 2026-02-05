const fs = require('fs');
const path = require('path');
const { Telegraf } = require('telegraf');
const config = require('./config');
const logger = require('./utils/logger');
const { validateInvoiceData, validateReceiptData } = require('./utils/validate');
const { generateInvoicePdf } = require('./invoice/invoiceGenerator');
const { generateReceiptPdf, buildReceiptFromInvoice, computeTotals } = require('./receipt/receiptGenerator');
const sampleData = require('./invoice/sampleInvoiceData.json');

const ensureTmp = () => {
  if (!fs.existsSync(config.tmpDir)) {
    fs.mkdirSync(config.tmpDir, { recursive: true });
  }
};

const buildSampleInvoiceData = (ctx) => {
  const user = ctx.from || {};
  const username = user.username ? `@${user.username}` : '@unknown';
  return {
    ...sampleData,
    customer: {
      ...sampleData.customer,
      name: user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : sampleData.customer.name,
      telegramUsername: username,
      telegramUserId: String(user.id || sampleData.customer.telegramUserId),
    },
  };
};

const createBot = () => {
  if (!config.botToken) {
    throw new Error('BOT_TOKEN is missing. Please set it in .env');
  }

  const bot = new Telegraf(config.botToken);

  bot.start((ctx) => {
    ctx.reply(
      'Welcome! Use /invoice to generate a sample invoice PDF.\n' +
        'Admin flow for custom invoices will be added next.'
    );
  });

  bot.command('invoice', async (ctx) => {
    ensureTmp();

    const data = buildSampleInvoiceData(ctx);
    const validation = validateInvoiceData(data);
    if (!validation.ok) {
      logger.error('Invoice validation failed: %j', validation.errors);
      await ctx.reply('Invoice data validation failed. Please contact admin.');
      return;
    }

    const fileName = `INVOICE_${data.invoice.invoiceId}.pdf`;
    const outputPath = path.join(config.tmpDir, fileName);

    try {
      await generateInvoicePdf(data, config, outputPath);
      await ctx.replyWithDocument({
        source: fs.createReadStream(outputPath),
        filename: fileName,
      });
    } catch (err) {
      logger.error('Invoice generation failed: %s', err.message);
      await ctx.reply('Failed to generate invoice. Please try again later.');
    } finally {
      if (fs.existsSync(outputPath)) {
        fs.unlinkSync(outputPath);
      }
    }
  });

  bot.command('receipt', async (ctx) => {
    ensureTmp();

    const invoiceData = buildSampleInvoiceData(ctx);
    const totals = computeTotals(invoiceData.items, invoiceData.charges);
    const receiptData = buildReceiptFromInvoice(invoiceData, {
      ...invoiceData.receipt,
      amountPaid: Number(invoiceData.receipt?.amountPaid || totals.summary.grandTotal),
    });

    const validation = validateReceiptData(receiptData, totals.summary.grandTotal);
    if (!validation.ok) {
      logger.error('Receipt validation failed: %j', validation.errors);
      await ctx.reply('Receipt data validation failed. Please contact admin.');
      return;
    }

    const fileName = `RECEIPT_${receiptData.receipt.receiptId}_FOR_${receiptData.invoice.invoiceId}.pdf`;
    const outputPath = path.join(config.tmpDir, fileName);

    try {
      await generateReceiptPdf(receiptData, config, outputPath);
      await ctx.replyWithDocument({
        source: fs.createReadStream(outputPath),
        filename: fileName,
      });
    } catch (err) {
      logger.error('Receipt generation failed: %s', err.message);
      await ctx.reply('Failed to generate receipt. Please try again later.');
    } finally {
      if (fs.existsSync(outputPath)) {
        fs.unlinkSync(outputPath);
      }
    }
  });

  // Stub for future admin JSON payload ingestion
  bot.command('invoice_json', async (ctx) => {
    await ctx.reply('Admin JSON ingestion stub. Hook your admin flow here.');
  });

  return bot;
};

const start = async () => {
  try {
    const bot = createBot();
    await bot.launch();
    logger.info('Bot started.');
  } catch (err) {
    logger.error('Bot failed to start: %s', err.message);
    process.exit(1);
  }
};

start();

process.once('SIGINT', () => process.exit(0));
process.once('SIGTERM', () => process.exit(0));
