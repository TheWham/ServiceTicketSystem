import test from 'node:test'
import assert from 'node:assert/strict'
import { hasGraphReasoning, parseGraphReasoning } from '../src/utils/graphReasoning.js'

test('hasGraphReasoning: 准确识别是否命中图谱推导', () => {
  assert.equal(hasGraphReasoning(null), false)
  assert.equal(hasGraphReasoning({}), false)
  assert.equal(hasGraphReasoning({ citations: [] }), false)

  // 普通向量切片引用
  const normalMsg = {
    citations: [
      { title: 'VPN-001', snippet: '连接公司VPN失败时的常规排查步骤，如重启路由器、排查WiFi。' }
    ]
  }
  assert.equal(hasGraphReasoning(normalMsg), false)

  // 命中图谱推导的引用
  const graphMsg = {
    citations: [
      { title: 'VPN-001', snippet: '【知识图谱因果推导】 • 识别关联实体：VPN错误691、AD域账号锁定 • 拓扑因果推导链： - VPN错误691 ──(诱发根因)──> AD域账号锁定' }
    ]
  }
  assert.equal(hasGraphReasoning(graphMsg), true)

  // 典型排障 SOP 纯双路召回（如“电脑蓝屏死机怎么办”，正文包含 Minidump 和 dump，但无图谱推导前缀）
  const bsodSopMsg = {
    content: '针对电脑蓝屏死机，请按以下步骤排查：\n【第七步：解析转储文件】提取蓝屏dump，C:\\Windows\\Minidump下会有崩溃转储文件，可用BlueScreenView打开查看详细模块。',
    citations: [
      {
        articleId: 'ITKB-SYS-001',
        title: '软件及操作系统常见排障指南',
        versionId: 'ver-1792085759135-101',
        score: 0.92,
        snippet: '针对电脑蓝屏死机，请在排查前做好数据备份。第一步：记录蓝屏代码；第七步：提取蓝屏dump文件...'
      }
    ]
  }
  assert.equal(hasGraphReasoning(bsodSopMsg), false, '普通双路召回蓝屏排障SOP不应误触发图谱推导')
  assert.equal(parseGraphReasoning(bsodSopMsg), null, '普通双路召回蓝屏排障SOP解析应返回null')

  // 其他包含特征词但无图谱推导因果事实的普通回答
  const otherNormalMsg = {
    content: '拨打客服热线或查看错误代码691，可能需要联系管理员重置AD账号。',
    citations: [
      {
        articleId: 'ITKB-VPN-002',
        title: '常见网络问题',
        snippet: '普通操作手册内容'
      }
    ]
  }
  assert.equal(hasGraphReasoning(otherNormalMsg), false, '普通双路召回回答不应误触发图谱推导')
  assert.equal(parseGraphReasoning(otherNormalMsg), null)
})

test('parseGraphReasoning: 完整结构化解析实体、因果链与建议', () => {
  const mockSnippet = `【知识图谱因果推导】 • 识别关联实体：移动端邮件客户端旧密码轮询、VPN错误691、AD域账号锁定 • 拓扑因果推导链： - 【因果事实】移动端邮件客户端旧密码轮询 ──(诱发根因)──> AD域账号锁定 - 【因果事实】AD域账号锁定 ──(前置排查动作)──> 自助密码重置平台 - 【因果事实】AD域账号锁定 ──(处置动作)──> AD域控制器 - 【反向关联】连续多次输入错误密码 ──(诱发根因)──> AD域账号锁定 • 排查处置建议：建议优先顺延上述因果链处置根因节点。 --- # 【VPN-001】VPN连接失败（拨号/认证失败）`

  const msg = {
    content: '您的VPN错误691与手机邮箱失效指向同一个根因：AD域账号被锁定。',
    citations: [
      {
        articleId: 'ITKB-VPN-001',
        title: 'VPN连接失败（拨号/认证失败）',
        versionId: 'ver-1792085759135-901',
        score: 0.9520,
        snippet: mockSnippet
      },
      {
        articleId: 'ITKB-ACC-001',
        title: 'AD域账号锁定与密码策略',
        versionId: 'ver-1792085759135-902',
        score: 0.8840,
        snippet: '账号被连续输错密码锁定时可在自助平台解锁'
      }
    ]
  }

  const result = parseGraphReasoning(msg)
  assert.ok(result, '应成功解析出推导结果')
  assert.equal(result.detected, true)

  // 1. 实体校验
  assert.equal(result.entities.length, 3)
  assert.ok(result.entities.includes('VPN错误691'))
  assert.ok(result.entities.includes('AD域账号锁定'))
  assert.ok(result.entities.includes('移动端邮件客户端旧密码轮询'))

  // 2. 推导链校验
  assert.equal(result.chains.length, 4)

  const step1 = result.chains[0]
  assert.equal(step1.step, 1)
  assert.equal(step1.tag, '因果事实')
  assert.equal(step1.src, '移动端邮件客户端旧密码轮询')
  assert.equal(step1.rel, '诱发根因')
  assert.equal(step1.tgt, 'AD域账号锁定')
  assert.equal(step1.isCausal, true)

  const step2 = result.chains[1]
  assert.equal(step2.step, 2)
  assert.equal(step2.src, 'AD域账号锁定')
  assert.equal(step2.rel, '前置排查动作')
  assert.equal(step2.tgt, '自助密码重置平台')
  assert.equal(step2.isAction, true)

  // 3. 建议与场景校验
  assert.equal(result.suggestion, '建议优先顺延上述因果链处置根因节点。')
  assert.equal(result.scene, 'vpn')

  // 4. 卡片列表校验
  assert.equal(result.cards.length, 2)
  assert.equal(result.cards[0].articleId, 'ITKB-VPN-001')
  assert.equal(result.cards[0].hasGraph, true)
  assert.equal(result.cards[1].articleId, 'ITKB-ACC-001')
  assert.equal(result.cards[1].hasGraph, false)
})

test('parseGraphReasoning: 正确识别 CMDB 与 废止替代场景', () => {
  const cmdbMsg = {
    content: '外网访问财务报销系统报 502',
    citations: [
      {
        articleId: 'ITKB-SYS-005',
        title: '财务报销系统',
        snippet: '【知识图谱因果推导】 • 识别关联实体：财务报销系统、SSL VPN • 拓扑因果推导链： - 财务报销系统 ──(依赖网络通道)──> SSL VPN'
      }
    ]
  }
  const cmdbRes = parseGraphReasoning(cmdbMsg)
  assert.equal(cmdbRes.scene, 'cmdb')

  const repMsg = {
    content: '密码输错几次会被锁定？',
    citations: [
      {
        articleId: 'ITKB-ACC-001',
        title: '现行账号管理制度',
        snippet: '【知识图谱因果推导】 • 识别关联实体：ITKB-ACC-001、ITKB-LEG-ACC-001 • 拓扑因果推导链： - ITKB-ACC-001 ──(废止并替代)──> ITKB-LEG-ACC-001'
      }
    ]
  }
  const repRes = parseGraphReasoning(repMsg)
  assert.equal(repRes.scene, 'replaces')

  const crashMsg = {
    content: '办公软件闪退，报错 APPCRASH 事件ID 1000',
    citations: [
      {
        articleId: 'ITKB-SYS-002',
        title: '软件闪退故障处置',
        snippet: '【知识图谱因果推导】 • 识别关联实体：软件闪退(APPCRASH)、VC++运行库 • 拓扑因果推导链： - 软件闪退(APPCRASH) ──(诱发根因)──> VC++运行库'
      }
    ]
  }
  const crashRes = parseGraphReasoning(crashMsg)
  assert.equal(crashRes.scene, 'sys_crash')
  assert.equal(crashRes.entities.includes('软件闪退(APPCRASH)'), true)

  const dnsMsg = {
    content: '微信正常但网页提示 DNS_PROBE_FINISHED_NXDOMAIN',
    citations: [
      {
        articleId: 'ITKB-NET-004',
        title: 'DNS解析失败故障排查',
        snippet: '【知识图谱因果推导】 • 识别关联实体：DNS_PROBE_FINISHED_NXDOMAIN、DNS缓存污染 • 拓扑因果推导链： - DNS缓存污染 ──(诱发根因)──> DNS_PROBE_FINISHED_NXDOMAIN'
      }
    ]
  }
  const dnsRes = parseGraphReasoning(dnsMsg)
  assert.equal(dnsRes.scene, 'dns')
  assert.equal(dnsRes.entities.includes('DNS_PROBE_FINISHED_NXDOMAIN'), true)
})
