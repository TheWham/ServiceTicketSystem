// Mock 认证中间件 —— 从请求头 X-User-Id 获取当前用户
const pool = require('../db');

async function mockAuth(req, res, next) {
  const userId = req.headers['x-user-id'];
  if (!userId) {
    return res.status(401).json({ code: 40100, msg: '缺少 X-User-Id 请求头，请先模拟登录' });
  }
  try {
    const [rows] = await pool.query('SELECT user_id, name, role, department FROM `user` WHERE user_id = ? AND status = ?', [userId, 'active']);
    if (rows.length === 0) {
      return res.status(401).json({ code: 40101, msg: '用户不存在或已禁用' });
    }
    req.currentUser = rows[0];
    next();
  } catch (err) {
    next(err);
  }
}

// 角色守卫
function requireRole(...roles) {
  return (req, res, next) => {
    if (!roles.includes(req.currentUser.role)) {
      return res.status(403).json({ code: 40300, msg: `需要 ${roles.join(' 或 ')} 权限` });
    }
    next();
  };
}

module.exports = { mockAuth, requireRole };