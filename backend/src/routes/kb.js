const { Router } = require('express');
const kbController = require('../controllers/kbController');

const router = Router();

router.post('/recommend', kbController.recommend);

module.exports = router;
