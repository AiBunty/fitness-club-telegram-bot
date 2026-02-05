module.exports = {
  $id: 'InvoiceSchema',
  type: 'object',
  required: ['business', 'customer', 'invoice', 'items'],
  additionalProperties: false,
  properties: {
    business: {
      type: 'object',
      required: ['name', 'address', 'phone'],
      additionalProperties: false,
      properties: {
        name: { type: 'string', minLength: 1 },
        address: { type: 'string', minLength: 1 },
        phone: { type: 'string', minLength: 1 },
        email: { type: 'string' },
        website: { type: 'string' },
        gstin: { type: 'string' },
        logoUrl: { type: 'string' },
      },
    },
    customer: {
      type: 'object',
      required: ['name', 'telegramUsername', 'telegramUserId'],
      additionalProperties: false,
      properties: {
        name: { type: 'string', minLength: 1 },
        telegramUsername: { type: 'string' },
        telegramUserId: { type: ['string', 'number'] },
        address: { type: 'string' },
      },
    },
    invoice: {
      type: 'object',
      required: ['invoiceId', 'invoiceDate', 'currency'],
      additionalProperties: false,
      properties: {
        invoiceId: { type: 'string', minLength: 1 },
        invoiceDate: { type: 'string', format: 'date' },
        dueDate: { type: 'string', format: 'date' },
        currency: { type: 'string', enum: ['INR'] },
        status: { type: 'string' },
        placeOfSupply: { type: 'string' },
      },
    },
    items: {
      type: 'array',
      minItems: 1,
      items: {
        type: 'object',
        required: ['description', 'qty', 'rate', 'discountPercent', 'gstPercent'],
        additionalProperties: false,
        properties: {
          description: { type: 'string', minLength: 1 },
          qty: { type: 'number', minimum: 0 },
          rate: { type: 'number', minimum: 0 },
          discountPercent: { type: 'number', minimum: 0, maximum: 100 },
          gstPercent: { type: 'number', minimum: 0, maximum: 100 },
        },
      },
    },
    charges: {
      type: 'object',
      additionalProperties: false,
      properties: {
        shipping: { type: 'number', minimum: 0 },
        serviceCharge: { type: 'number', minimum: 0 },
      },
    },
    payment: {
      type: 'object',
      additionalProperties: false,
      properties: {
        upiId: { type: 'string' },
        bankName: { type: 'string' },
        accountNo: { type: 'string' },
        ifsc: { type: 'string' },
        razorpayLink: { type: 'string' },
      },
    },
    terms: {
      type: 'array',
      items: { type: 'string' },
    },
    receipt: {
      type: 'object',
      additionalProperties: false,
      required: ['receiptId', 'receiptDate', 'paymentMethod', 'amountPaid'],
      properties: {
        receiptId: { type: 'string', minLength: 1 },
        receiptDate: { type: 'string', format: 'date' },
        paymentMethod: {
          type: 'string',
          enum: ['UPI', 'CARD', 'CASH', 'BANK', 'OTHER'],
        },
        transactionId: { type: 'string' },
        amountPaid: { type: 'number', minimum: 0 },
        paymentNotes: { type: 'string' },
      },
    },
  },
};
