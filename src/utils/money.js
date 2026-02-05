const formatINR = (value) => {
  const amount = Number(value || 0);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

const round2 = (value) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;

module.exports = { formatINR, round2 };
