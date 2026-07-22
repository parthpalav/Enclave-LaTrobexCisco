/**
 * Custom Console Logger for CrowdShield Server
 */

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  bgRed: '\x1b[41m',
};

const logger = {
  info: (tag, message = '') => {
    const time = new Date().toLocaleTimeString();
    console.log(`${colors.cyan}[${tag}]${colors.reset} ${message} ${colors.dim}(${time})${colors.reset}`);
  },

  success: (tag, message = '') => {
    const time = new Date().toLocaleTimeString();
    console.log(`${colors.green}[${tag}]${colors.reset} ${message} ${colors.dim}(${time})${colors.reset}`);
  },

  warn: (tag, message = '') => {
    const time = new Date().toLocaleTimeString();
    console.log(`${colors.yellow}[${tag}]${colors.reset} ${message} ${colors.dim}(${time})${colors.reset}`);
  },

  alert: (tag, message = '') => {
    const time = new Date().toLocaleTimeString();
    console.log(`${colors.bgRed}${colors.white}${colors.bright} [${tag}] ${colors.reset} ${colors.red}${message}${colors.reset} ${colors.dim}(${time})${colors.reset}`);
  },

  metrics: (devices, count, status) => {
    let statusColor = colors.green;
    if (status === 'WARNING') statusColor = colors.yellow;
    if (status === 'DANGER') statusColor = colors.red;

    console.log(
      `${colors.dim}[Telemetry]${colors.reset} Connected Devices: ${colors.bright}${devices}${colors.reset} | Crowd Count: ${colors.bright}${count}${colors.reset} | Status: ${statusColor}${colors.bright}${status}${colors.reset}`
    );
  }
};

module.exports = logger;
