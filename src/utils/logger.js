const { createLogger, format, transports } = require('winston');

const logger = createLogger({
  level: 'info',
  format: format.combine(
    format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    format.errors({ stack: true }),
    format.splat(),
    format.printf(({ timestamp, level, message, stack }) => {
      if (stack) return `${timestamp} [${level}] ${message}\n${stack}`;
      return `${timestamp} [${level}] ${message}`;
    })
  ),
  transports: [new transports.Console()],
});

module.exports = logger;
