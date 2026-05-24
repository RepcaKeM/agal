// Express skeleton with the boring-but-required middleware.
// Adapt to your framework; this is a reminder of what NOT to forget.

const express = require('express');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { authenticate, authorize } = require('./middleware/auth');

const app = express();

app.use(helmet());
app.use(express.json({ limit: '1mb' }));

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api', apiLimiter);

// Consistent response envelope.
function ok(res, data) {
  res.json({ data, meta: { timestamp: new Date().toISOString() } });
}
function fail(res, status, code, message) {
  res.status(status).json({ error: { code, message } });
}

app.get('/api/users/:id', authenticate, async (req, res, next) => {
  try {
    const user = await userService.findById(req.params.id);
    if (!user) return fail(res, 404, 'USER_NOT_FOUND', 'User not found');
    ok(res, user);
  } catch (err) {
    next(err);
  }
});

// Centralized error handler — never leak stack traces in prod.
app.use((err, req, res, next) => {
  req.log?.error({ err }, 'unhandled');
  fail(res, 500, 'INTERNAL', 'Internal server error');
});

module.exports = app;
