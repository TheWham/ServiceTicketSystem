// Upload Controller —— 工单附件上传（multer 磁盘存储）
const path = require('path');
const fs = require('fs');
const multer = require('multer');

// 上传目录: backend/uploads/
const UPLOAD_DIR = path.join(__dirname, '..', '..', 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const ALLOWED_MIME = ['image/jpeg', 'image/jpg', 'image/png'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

const storage = multer.diskStorage({
  destination(req, file, cb) {
    cb(null, UPLOAD_DIR);
  },
  filename(req, file, cb) {
    // 生成唯一文件名，避免覆盖与中文/特殊字符问题
    const ext = path.extname(file.originalname).toLowerCase() || '.png';
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}${ext}`;
    cb(null, unique);
  }
});

const fileFilter = (req, file, cb) => {
  if (ALLOWED_MIME.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error('仅支持 jpg/jpeg/png 图片格式'));
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_SIZE }
}).array('files', 3);

// POST /api/v1/uploads —— 上传附件（field 名 files，最多 3 张）
async function uploadFiles(req, res, next) {
  upload(req, res, (err) => {
    if (err) {
      // multer 错误统一走参数错误码
      if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
          return res.status(400).json({ code: 40001, msg: '单个文件不能超过 5MB', data: null });
        }
        if (err.code === 'LIMIT_UNEXPECTED_FILE') {
          return res.status(400).json({ code: 40001, msg: '最多上传 3 个文件', data: null });
        }
        return res.status(400).json({ code: 40001, msg: `上传失败: ${err.message}`, data: null });
      }
      // fileFilter 等自定义错误
      return res.status(400).json({ code: 40001, msg: err.message || '上传失败', data: null });
    }

    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ code: 40001, msg: '未接收到文件', data: null });
    }

    const urls = req.files.map(f => `/uploads/${f.filename}`);
    res.json({ code: 0, msg: 'success', data: { urls } });
  });
}

module.exports = { upload: uploadFiles };
