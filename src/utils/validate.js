const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const schema = require('../invoice/schema');

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const validate = ajv.compile(schema);

const validateInvoiceData = (data) => {
  const ok = validate(data);
  return {
    ok,
    errors: ok ? [] : validate.errors || [],
  };
};

const validateReceiptData = (data, invoiceGrandTotal) => {
  const errors = [];
  const receipt = data?.receipt || {};
  const invoiceId = data?.invoice?.invoiceId || '';

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

  return {
    ok: errors.length === 0,
    errors,
  };
};

module.exports = { validateInvoiceData, validateReceiptData };
