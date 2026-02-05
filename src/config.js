const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const config = {
  botToken: process.env.BOT_TOKEN || '',
  business: {
    name: process.env.BUSINESS_NAME || "Wani's Club Level Up",
    address:
      process.env.BUSINESS_ADDRESS ||
      '101, 1st floor, Padma Vishwa Orchid, Cricket Ground, opposite Doctor BS Moonje Marg, above Pepperfry Showroom, Mahatma Nagar, Parijat Nagar, Nashik, Maharashtra 422005',
    phone: process.env.BUSINESS_PHONE || '09158243377',
    email: process.env.BUSINESS_EMAIL || '',
    website: process.env.BUSINESS_WEBSITE || '',
    gstin: process.env.BUSINESS_GSTIN || '',
    logoUrl:
      process.env.BUSINESS_LOGO_URL ||
      'https://scontent-sin11-1.xx.fbcdn.net/v/t39.30808-6/581796178_856849056684939_633268110531278084_n.jpg?_nc_cat=104&ccb=1-7&_nc_sid=6ee11a&_nc_ohc=e3yjwr7CT24Q7kNvwG8xlLB&_nc_oc=Adnub4AL_OZeBoynqaGVd3zKXXqRPvVGV1Ni1CWDsVl7U95LCALwNzaU_CUnV7lEb-8&_nc_zt=23&_nc_ht=scontent-sin11-1.xx&_nc_gid=OOY39Sr1uRYdO5VNOzyhWw&oh=00_Afu6unQqOnTRS8yDIIleIJM121FWMGraxkS59RUUSSn-7g&oe=698A2AC0',
  },
  invoice: {
    paymentDueDays: Number(process.env.INVOICE_PAYMENT_DUE_DAYS || 7),
    includeReturnRefund: String(process.env.TERMS_INCLUDE_RETURN_REFUND || 'false').toLowerCase() === 'true',
    returnRefundText:
      process.env.TERMS_RETURN_REFUND_TEXT ||
      'Returns/refunds are subject to prior approval and policy conditions.',
  },
  payment: {
    upiId: process.env.PAYMENT_UPI_ID || '',
    bankName: process.env.PAYMENT_BANK_NAME || '',
    accountNo: process.env.PAYMENT_ACCOUNT_NO || '',
    ifsc: process.env.PAYMENT_IFSC || '',
    razorpayLink: process.env.PAYMENT_RAZORPAY_LINK || '',
  },
  tmpDir: path.join(__dirname, '..', 'tmp'),
};

module.exports = config;
