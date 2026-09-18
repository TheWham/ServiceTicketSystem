// Asset Controller —— 资产查询（员工名下设备 / 单条资产）
const pool = require('../db');

const BASE_SELECT = `
  SELECT a.asset_id, a.model, a.owner_id, a.status, u.name AS owner_name
  FROM asset a
  LEFT JOIN user u ON a.owner_id = u.user_id
`;

// GET /api/v1/assets —— 资产列表，支持按 user_id（owner_id）过滤
async function listAssets(req, res, next) {
  try {
    const { user_id } = req.query;
    let sql = BASE_SELECT;
    const params = [];
    if (user_id) {
      sql += ' WHERE a.owner_id = ?';
      params.push(user_id);
    }
    sql += ' ORDER BY a.asset_id';

    const [rows] = await pool.query(sql, params);
    res.json({ code: 0, msg: 'success', data: rows });
  } catch (err) { next(err); }
}

// GET /api/v1/assets/:id —— 单条资产
async function getAsset(req, res, next) {
  try {
    const { id } = req.params;
    const [rows] = await pool.query(`${BASE_SELECT} WHERE a.asset_id = ?`, [id]);

    if (rows.length === 0) {
      return res.status(404).json({ code: 40400, msg: '资产不存在', data: null });
    }
    res.json({ code: 0, msg: 'success', data: rows[0] });
  } catch (err) { next(err); }
}

module.exports = { listAssets, getAsset };
