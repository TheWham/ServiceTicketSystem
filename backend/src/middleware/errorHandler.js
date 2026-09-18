// 统一错误处理中间件
function errorHandler(err, req, res, _next) {
  const status = err.status || 500;
  const code = err.code || 50000;

  // 完整记录：方法、路径、用户、错误码、消息、堆栈
  console.error(
    `[ERROR] ${req.method} ${req.originalUrl} | user=${req.headers['x-user-id'] || '-'} | ` +
    `${status}/${code} | ${err.message}`
  );
  if (status >= 500) {
    console.error('  堆栈:', err.stack);
    if (req.body && Object.keys(req.body).length) {
      // 不打印可能敏感的完整内容，只打印字段名
      console.error('  请求字段:', Object.keys(req.body).join(', '));
    }
  }

  res.status(status).json({
    code,
    msg: err.message || '服务器内部错误',
    data: null
  });
}

module.exports = errorHandler;