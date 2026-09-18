const { Router } = require('express');
const assetController = require('../controllers/assetController');

const router = Router();

router.get('/', assetController.listAssets);
router.get('/:id', assetController.getAsset);

module.exports = router;
