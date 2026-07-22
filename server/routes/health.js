const express = require('express');
const router = express.Router();

/**
 * Health check endpoint
 * GET /health -> { "healthy": true }
 */
router.get('/', (req, res) => {
  res.status(200).json({ healthy: true });
});

module.exports = router;
