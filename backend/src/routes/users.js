const { Router } = require('express');
const uc = require('../controllers/userController');

const router = Router();

router.get('/me',            uc.getMe);
router.get('/',             uc.listUsers);

// 草稿
router.get('/drafts',       uc.getDraft);
router.post('/drafts',      uc.saveDraft);
router.delete('/drafts',    uc.deleteDraft);

module.exports = router;