// KB Controller —— 模拟知识库推荐（基于 category + description 关键词命中打分）
// 预置知识库（约 10 条），覆盖硬件/软件/网络/账号等类别
const KNOWLEDGE_BASE = [
  {
    article_id: 'KB-NET-001',
    title: '办公网 VPN 无法认证排查',
    category: '网络',
    keywords: ['vpn', '连接', '认证', '无法连接', '远程'],
    solution_summary: '检查账号密码是否过期，确认 VPN 客户端版本，重置令牌后重试；仍失败请联系网络组开通权限。'
  },
  {
    article_id: 'KB-NET-002',
    title: '无线网络频繁掉线处理',
    category: '网络',
    keywords: ['wifi', '无线', '掉线', '断网', '网络不稳定'],
    solution_summary: '更新无线网卡驱动，切换 5GHz 频段，排查信道干扰；必要时更换工位附近 AP。'
  },
  {
    article_id: 'KB-NET-003',
    title: '内网服务器无法访问排查',
    category: '网络',
    keywords: ['服务器', '无法访问', 'ping', '不通', '内网'],
    solution_summary: '先 ping 网关与目标 IP，确认网段与防火墙策略，提交网络变更申请开放端口。'
  },
  {
    article_id: 'KB-ACC-001',
    title: 'ERP 账号锁定解锁',
    category: '账号',
    keywords: ['锁定', '登录', '账号', 'erp', '解锁', '密码'],
    solution_summary: '连续输错 5 次会锁定账号，联系账号管理员提交解锁工单并重置密码。'
  },
  {
    article_id: 'KB-ACC-002',
    title: '邮箱账号开通与权限变更',
    category: '账号',
    keywords: ['邮箱', '开通', '权限', '邮箱账号', '邮件'],
    solution_summary: '新员工邮箱由 HR 入职流程自动开通，权限变更需直属主管审批后提交工单。'
  },
  {
    article_id: 'KB-ACC-003',
    title: 'AD 域账号密码重置',
    category: '账号',
    keywords: ['密码', '重置', '域账号', 'ad', '忘记密码'],
    solution_summary: '凭员工号与身份证明联系服务台，验证身份后由工程师重置 AD 域密码。'
  },
  {
    article_id: 'KB-HW-001',
    title: '笔记本无法开机排查',
    category: '硬件',
    keywords: ['开机', '电源', '无法开机', '黑屏', '笔记本'],
    solution_summary: '长按电源键 10 秒强制重启，检查电源适配器与电池；仍黑屏送修硬件组。'
  },
  {
    article_id: 'KB-HW-002',
    title: '打印机卡纸/离线处理',
    category: '硬件',
    keywords: ['打印机', '卡纸', '离线', '打印', '硒鼓'],
    solution_summary: '断电后按手册取出卡纸，检查硒鼓安装与网络连接，重启打印机恢复在线。'
  },
  {
    article_id: 'KB-HW-003',
    title: '显示器无信号排查',
    category: '硬件',
    keywords: ['显示器', '无信号', '黑屏', '外接', '屏幕'],
    solution_summary: '检查信号线与接口连接，切换输入源，重新插拔显卡；必要时更换连接线。'
  },
  {
    article_id: 'KB-SW-001',
    title: 'Office 激活失败处理',
    category: '软件',
    keywords: ['office', '激活', '安装', 'office激活', '办公软件'],
    solution_summary: '确认使用公司统一账号登录并联网，卸载旧版后重装最新 Office，在线激活。'
  },
  {
    article_id: 'KB-SW-002',
    title: 'Outlook 无法收发邮件排查',
    category: '软件',
    keywords: ['outlook', '邮件', '收发', '无法收发', '客户端'],
    solution_summary: '重建邮箱配置文件，检查服务器设置与缓存大小，必要时切换 Web 端临时使用。'
  }
];

// POST /api/kb/recommend —— 知识库推荐
// 入参: { category, description, asset_id? }
async function recommend(req, res, next) {
  try {
    const { category, description } = req.body || {};
    const text = (description || '').toLowerCase();

    // 参数校验
    if (!category || typeof category !== 'string' || !text) {
      return res.status(400).json({ code: 40001, msg: '参数错误：category 与 description 为必填', data: null });
    }

    // 类别过滤
    const candidates = KNOWLEDGE_BASE.filter(k => k.category === category);

    // 关键词命中打分
    const scored = candidates
      .map(k => {
        const hitCount = k.keywords.filter(kw => text.includes(kw.toLowerCase())).length;
        const similarity = k.keywords.length ? hitCount / k.keywords.length : 0;
        return { k, hitCount, similarity };
      })
      .filter(item => item.hitCount > 0)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 3);

    const hasRecommendation = scored.length > 0;
    const recommendList = scored.map(item => ({
      article_id: item.k.article_id,
      title: item.k.title,
      similarity_score: Math.round(item.similarity * 100) / 100,
      solution_summary: item.k.solution_summary
    }));

    res.json({
      code: 0,
      msg: 'success',
      data: { has_recommendation: hasRecommendation, recommend_list: recommendList }
    });
  } catch (err) { next(err); }
}

module.exports = { recommend };
