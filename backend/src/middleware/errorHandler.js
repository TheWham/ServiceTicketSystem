// 统一错误处理中间件
function errorHandler(err, req, res, _next) {
  console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);
  const status = err.status || 500;
  const code = err.code || 50000;
  res.status(status).json({
    code,
    msg: err.message || '服务器内部错误',
    data: null
  });
}

module.exports = errorHandler;