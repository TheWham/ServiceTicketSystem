/**
 * 知识图谱因果推导（GraphRAG）数据解析工具
 * 从 AI 客服检索引用的 snippet 中解析刚性拓扑因果链、识别实体与多跳推导事实
 */

export function hasGraphReasoning(msg) {
  if (!msg) return false
  if (msg.citations && msg.citations.length) {
    if (msg.citations.some(
      c => c.snippet && (c.snippet.includes('【知识图谱因果推导】') || c.snippet.includes('拓扑因果推导链'))
    )) {
      return true
    }
  }
  const content = msg.content || msg.answerText || ''
  if (content.includes('【知识图谱因果推导】') || content.includes('拓扑因果推导链')) {
    return true
  }
  // 智能兜底：如果回答内容涉及典型级联穿透排查（如 691 + AD/邮箱失效，或者跨卡因果分析），且包含卡片引用，激活图谱推导
  if (msg.citations && msg.citations.length && (
    (content.includes('691') && (content.includes('凭据失效') || content.includes('域账号') || content.includes('AD'))) ||
    (content.includes('502') && (content.includes('SSL VPN') || content.includes('报销') || content.includes('ERP'))) ||
    (content.includes('蓝屏') && (content.includes('Minidump') || content.includes('dump') || content.includes('dmp'))) ||
    (content.includes('DNS') && content.includes('NXDOMAIN')) ||
    (content.includes('APPCRASH') && content.includes('运行库'))
  )) {
    return true
  }
  return false
}

export function parseGraphReasoning(msg) {
  if (!hasGraphReasoning(msg)) return null

  let targetCitation = (msg.citations || []).find(
    c => c.snippet && (c.snippet.includes('【知识图谱因果推导】') || c.snippet.includes('拓扑因果推导链'))
  )
  let text = targetCitation ? (targetCitation.snippet || '') : (msg.content || msg.answerText || '')

  // 1. 提取识别的种子实体
  let entities = []
  const entityMatch = text.match(/•\s*识别关联实体[：:]\s*([^•\n]+)/)
  if (entityMatch) {
    entities = entityMatch[1]
      .trim()
      .split(/[、,，\s]+/)
      .map(s => s.trim())
      .filter(Boolean)
  }

  // 2. 提取拓扑因果推导链
  let rawChains = []
  const chainMatch = text.match(/•\s*拓扑因果推导链[：:]\s*([\s\S]*?)(?=•\s*排查处置建议|---|#|$)/)
  if (chainMatch) {
    const raw = chainMatch[1].trim()
    // 按 "- " 或行分割各条推导事实
    rawChains = raw
      .split(/\s+-\s+/)
      .map(s => s.trim().replace(/^[-•]\s*/, ''))
      .filter(Boolean)
  }

  // 结构化解析每一跳
  const parsedChains = rawChains.map((c, idx) => {
    let tag = '因果推导'
    let content = c
    const tagMatch = c.match(/^[【\[]([^】\]]+)[】\]]\s*(.*)/)
    if (tagMatch) {
      tag = tagMatch[1]
      content = tagMatch[2]
    }

    // 匹配 "源实体 ──(关系)──> 目标实体" 或 "源实体 -> 目标实体"
    const relMatch = content.match(/^(.*?)\s*(?:──\((.*?)\)──>|--\((.*?)\)-->|─+\((.*?)\)─+>|──>|->)\s*(.*)$/)
    if (relMatch) {
      const src = relMatch[1].trim()
      const rel = (relMatch[2] || relMatch[3] || relMatch[4] || '关联').trim()
      const tgt = relMatch[5].trim()
      return {
        step: idx + 1,
        tag,
        src,
        rel,
        tgt,
        raw: c,
        isCausal: rel.includes('根因') || rel.includes('诱发') || rel.includes('导致'),
        isAction: rel.includes('处置') || rel.includes('排查') || rel.includes('动作'),
        isDeprecated: rel.includes('废止') || rel.includes('替代')
      }
    }

    return {
      step: idx + 1,
      tag,
      src: '',
      rel: '',
      tgt: '',
      raw: c,
      isCausal: false,
      isAction: false,
      isDeprecated: false
    }
  })

  // 3. 提取排查处置建议
  let suggestion = '建议优先顺延图谱因果链处置根因节点。'
  const sugMatch = text.match(/•\s*排查处置建议[：:]\s*([^•\n---]+)/)
  if (sugMatch) {
    suggestion = sugMatch[1].trim()
  }

  // 4. 提取穿透关联的知识卡片列表
  const cards = (msg.citations || []).map(cit => ({
    articleId: cit.articleId || '',
    title: cit.title || '',
    versionId: cit.versionId || '',
    score: cit.score != null ? cit.score : 1.0,
    hasGraph: cit === targetCitation
  }))

  // 推导最佳工作台场景 (cmdb / replaces / sys_crash / dns / bsod / vpn / custom)
  let scene = 'custom'
  const allText = text + ' ' + (msg.content || '')
  if (allText.includes('报销') || allText.includes('ERP') || allText.includes('502') || allText.includes('财务')) {
    scene = 'cmdb'
  } else if (allText.includes('废止') || allText.includes('替代') || allText.includes('次数') || allText.includes('规章')) {
    scene = 'replaces'
  } else if (allText.includes('APPCRASH') || allText.includes('闪退') || allText.includes('运行库') || allText.includes('1000')) {
    scene = 'sys_crash'
  } else if (allText.includes('DNS') || allText.includes('NXDOMAIN')) {
    scene = 'dns'
  } else if (allText.includes('蓝屏') || allText.includes('BSOD')) {
    scene = 'bsod'
  } else if (allText.includes('VPN') || allText.includes('691')) {
    scene = 'vpn'
  }

  return {
    detected: true,
    entities,
    chains: parsedChains,
    suggestion,
    cards,
    scene,
    rawText: text
  }
}
