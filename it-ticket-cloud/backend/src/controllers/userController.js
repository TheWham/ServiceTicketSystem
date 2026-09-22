// User Controller —— 用户查询 + Mock 登录
const pool = require('../db');

// GET /api/v1/users —— 获取用户列表(派单选择、测试用)
async function listUsers(req, res, next) {
  try {
    const { role } = req.query;
    let sql = 'SELECT user_id, name, role, department FROM user WHERE status = ?';
    const params = ['active'];
    if (role) { sql += ' AND role = ?'; params.push(role); }
    sql += ' ORDER BY role, name';

    const [rows] = await pool.query(sql, params);
    res.json({ code: 0, msg: 'success', data: rows });
  } catch (err) { next(err); }
}

// GET /api/v1/users/me —— 获取当前用户信息
async function getMe(req, res) {
  res.json({ code: 0, msg: 'success', data: req.currentUser });
}

// GET /api/v1/users/login-options —— Mock 登录选项(列出所有活跃用户)
async function loginOptions(req, res, next) {
  try {
    const [rows] = await pool.query(
      `SELECT user_id, name, role, department FROM user WHERE status = ?
       ORDER BY CASE role WHEN 'employee' THEN 1 WHEN 'engineer' THEN 2 WHEN 'supervisor' THEN 3 ELSE 4 END, name`,
      ['active']
    );
    res.json({ code: 0, msg: 'success', data: rows });
  } catch (err) { next(err); }
}

// POST /api/v1/drafts —— 保存/更新草稿
async function saveDraft(req, res, next) {
  try {
    const userId = req.currentUser.user_id;
    const { title, category, description, priority, attachment_urls, asset_id, expected_finish_time } = req.body;

    await pool.query(
      `INSERT INTO ticket_draft (user_id, title, category, description, priority, attachment_urls, asset_id, expected_finish_time)
       VALUES (?,?,?,?,?,?,?,?)
       ON CONFLICT(user_id) DO UPDATE SET
         title = excluded.title,
         category = excluded.category,
         description = excluded.description,
         priority = excluded.priority,
         attachment_urls = excluded.attachment_urls,
         asset_id = excluded.asset_id,
         expected_finish_time = excluded.expected_finish_time,
         updated_at = datetime('now','localtime')`,
      [userId, title || null, category || null, description || null, priority || '中',
       attachment_urls ? JSON.stringify(attachment_urls) : null, asset_id || null, expected_finish_time || null]
    );

    res.json({ code: 0, msg: '草稿已保存' });
  } catch (err) { next(err); }
}

// GET /api/v1/drafts —— 获取当前用户草稿
async function getDraft(req, res, next) {
  try {
    const [rows] = await pool.query('SELECT * FROM ticket_draft WHERE user_id = ?', [req.currentUser.user_id]);
    if (rows.length === 0) return res.json({ code: 0, msg: 'success', data: null });

    const draft = rows[0];
    if (draft.attachment_urls && typeof draft.attachment_urls === 'string') {
      draft.attachment_urls = JSON.parse(draft.attachment_urls);
    }
    res.json({ code: 0, msg: 'success', data: draft });
  } catch (err) { next(err); }
}

// DELETE /api/v1/drafts —— 删除草稿(提交成功后)
async function deleteDraft(req, res, next) {
  try {
    await pool.query('DELETE FROM ticket_draft WHERE user_id = ?', [req.currentUser.user_id]);
    res.json({ code: 0, msg: '草稿已清除' });
  } catch (err) { next(err); }
}

module.exports = { listUsers, getMe, loginOptions, saveDraft, getDraft, deleteDraft };