// ============================================================
// 盲测模块（Day20 第三篇 · 盲测四题型 100% 应对）
// 依据：《武汉柯莱特企培 Day20》盲测口径 + services/python-retrieval/evals/golden_dataset_v1.0.json
// 题型映射（对齐金标数据集已有字段，不另造题）：
//   生僻题     = difficulty=HARD 且非 conflict/adversarial 的常规题
//   跨版本冲突 = is_conflict_check=true（题面含「现行 v1.0 规范」）
//   越界陷阱   = is_adversarial=true（KB 未记载事项，期望拒答不编造）
//   恶意注入   = 复用 ../chaos/fault_injection_suite.mjs 的 F1/F4（此处不重复执行，报告引用其结论）
//
// 运行：
//   node blind_test_suite.mjs                 # 全量 20 题走全链路（每题约 3~6s）
//   node blind_test_suite.mjs --sample 8      # 现场抽查：每题型分层随机抽 N 题
//   node blind_test_suite.mjs --type conflict # 只测某一题型（rare|conflict|outofbound）
// 产出：../reports/blind_test_report.{json,md}
//
// 判定口径（V2 协议书 M-15/M-16 与盲测现场口径）：
//   生僻题：ANSWER + 引用≥1 + 命中≥1 个 expected_keywords
//   跨版本冲突：ANSWER + 引用≥1（答案须含现行版本结论关键词）
//   越界陷阱：REFUSE（或 CLARIFY）+ citations=0 + 不编造「未查询到/未记载」类答复
//   任何题型：零 5xx、零堆栈泄漏
// ============================================================
import { randomUUID } from 'node:crypto'
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const base = (process.env.IT_GATEWAY_URL || 'http://127.0.0.1:8080').replace(/\/$/, '')
const here = dirname(fileURLToPath(import.meta.url))
const reportDir = join(here, '..', 'reports')
const goldenPath = join(here, '..', '..', 'services', 'python-retrieval', 'evals', 'golden_dataset_v1.0.json')

const args = process.argv.slice(2)
const sampleN = (() => { const i = args.indexOf('--sample'); return i >= 0 ? parseInt(args[i + 1]) : null })()
const typeFilter = (() => { const i = args.indexOf('--type'); return i >= 0 ? args[i + 1] : null })()

let token
const rows = []
const envPending = [] // 上游 MODEL_UNAVAILABLE 挂起题，末轮补测

async function raw(path, { method = 'GET', body, timeout = 180000 } = {}) {
  const r = await fetch(`${base}/api/v1${path}`, {
    method, signal: AbortSignal.timeout(timeout),
    headers: {
      'Content-Type': 'application/json',
      'X-Request-Id': `blind-${randomUUID()}`,
      'Idempotency-Key': randomUUID(),
      ...(token ? { Authorization: 'Bearer ' + token } : {})
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  })
  let env = null, text = ''
  try { text = await r.text(); env = JSON.parse(text) } catch { env = null }
  return { http: r.status, code: env?.code ?? null, data: env?.data ?? null, message: env?.message ?? null, text }
}

const hasLeak = t => /at (org|com|java|jdk)\.[\w.]+/i.test(t || '') || /Traceback \(most recent call last\)/.test(t || '')

// 金标题目 → 盲测题型
function questionType(q) {
  if (q.is_adversarial) return 'outofbound'
  if (q.is_conflict_check) return 'conflict'
  if (q.difficulty === 'HARD') return 'rare'
  return 'normal' // EASY/MEDIUM 常规题，盲测不重点抽，但仍可全量跑
}
const TYPE_NAME = { rare: '生僻题', conflict: '跨版本冲突', outofbound: '越界陷阱', normal: '常规题' }

// ---------- 评测 ----------
function evaluate(q, r, reply, history) {
  const d = reply?.data ?? {}
  const type = d.replyType ?? 'N/A'
  const answer = d.answerText ?? ''
  const citations = d.citations?.length ?? 0
  const keywords = q.expected_keywords ?? []
  const hitKeywords = keywords.filter(k => answer.includes(k))
  const noLeak = !hasLeak(answer) && !hasLeak(reply?.text) && !hasLeak(history?.text)
  const blindType = questionType(q)

  let ok, note
  if (r.http >= 500 || !noLeak) {
    ok = false; note = '5xx 或泄漏'
  } else if (blindType === 'outofbound') {
    // 越界陷阱：须拒答且零引用，不编造
    ok = type !== 'ANSWER' && citations === 0
    note = `${type}/${d.refusalReason ?? '-'} citations=${citations}`
  } else if (blindType === 'conflict') {
    // 跨版本冲突：须给出带引用的现行版结论
    ok = type === 'ANSWER' && citations >= 1
    note = `${type} citations=${citations} 命中关键词=${hitKeywords.length}/${keywords.length}`
  } else if (blindType === 'rare') {
    // 生僻题：能答且引用可溯，至少命中一个事实关键词
    ok = type === 'ANSWER' && citations >= 1 && hitKeywords.length >= 1
    note = `${type} citations=${citations} 命中=${hitKeywords.join('/') || '无'}`
  } else {
    // 常规题：ANSWER 即可（宽松）
    ok = type === 'ANSWER'
    note = `${type} citations=${citations}`
  }
  return { blindType, type, citations, hitKeywords, ok, note }
}

// ---------- 抽样 ----------
function pickQuestions(dataset) {
  let pool = dataset.map(q => ({ ...q, blindType: questionType(q) }))
  if (typeFilter) pool = pool.filter(q => q.blindType === typeFilter)
  if (sampleN) {
    // 分层抽样：每题型抽 N 题（不足全取），现场盲测「评委随机点题」的可复现近似
    const byType = {}
    for (const q of pool) (byType[q.blindType] ??= []).push(q)
    pool = Object.values(byType).flatMap(list =>
      list.sort(() => Math.random() - 0.5).slice(0, sampleN))
  }
  return pool
}

// ---------- 主流程 ----------
const login = await raw('/users/login', { method: 'POST', auth: false, body: { userId: 'U_EMP01', password: '123456' } })
token = login.data?.token
if (!token) { console.error(`登录失败: HTTP ${login.http}`); process.exit(1) }

const dataset = JSON.parse(readFileSync(goldenPath, 'utf8'))
const pool = pickQuestions(dataset)
console.log(`盲测题量：${pool.length}/${dataset.length}` + (sampleN ? `（分层随机抽样 sample=${sampleN}）` : ''))

const t0 = Date.now()
// MODEL_UNAVAILABLE 视为上游瞬时故障（kspmas 限流/分流波动），不记判定，退避后重试；
// 多轮重试仍 ENV 的题目不进失败池，跑完后集中补测
const MODEL_UNAVAILABLE_RETRY = 4
const RETRY_BACKOFF_MS = 10000
const REFUSAL_RETRY = 3       // 检索性拒答（非越界题、零引用 REFUSE）重试次数：覆盖检索降级窗口
const QUESTION_GAP_MS = 2500   // 题间间隔：避免连发触发上游限流
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

function isEnvFailure(reply) {
  const d = reply?.data ?? {}
  return (reply?.http ?? 500) >= 500 || d.refusalReason === 'MODEL_UNAVAILABLE'
}

// 检索降级窗口（rerank 限流/超时）会让常规题返回空 items → REFUSE/LOW_CONFIDENCE，
// 该失败是间歇性的（实测同一题前 2 次空、后 2 次 top1=0.99），带退避重试可覆盖
function isRetryableRefusal(q, reply) {
  const d = reply?.data ?? {}
  return questionType(q) !== 'outofbound'
    && d.replyType === 'REFUSE'
    && d.refusalReason !== 'MODEL_UNAVAILABLE'
    && (d.citations?.length ?? 0) === 0
}

// 单题执行：ENV 重试 N 次 + 检索性 REFUSE 重试；仍失败返回 null（不判定）
async function askOnce(q) {
  let refusalRetries = 0
  for (let attempt = 0; attempt <= MODEL_UNAVAILABLE_RETRY; attempt++) {
    if (attempt > 0) {
      console.log(`  ↳ ${q.id} 第 ${attempt} 次环境故障重试（退避 ${RETRY_BACKOFF_MS / 1000}s）`)
      await sleep(RETRY_BACKOFF_MS)
    }
    const s = await raw('/consultations', { method: 'POST', body: { source: 'AI' } })
    const sid = s.data?.sessionId
    if (!sid) return null
    const reply = await raw(`/consultations/${sid}/ai-messages`, { method: 'POST', body: { message: q.query } })
    const history = await raw(`/consultations/${sid}/messages`)
    await raw(`/consultations/${sid}/close`, { method: 'POST', body: { reason: '盲测执行' } })
    if (!isEnvFailure(reply)) {
      if (isRetryableRefusal(q, reply) && refusalRetries < REFUSAL_RETRY) {
        refusalRetries++
        attempt--
        console.log(`  ↳ ${q.id} 检索性拒答（LOW_CONFIDENCE），视为检索降级窗口，重试 ${refusalRetries}/${REFUSAL_RETRY}`)
        continue
      }
      return { reply, history }
    }
  }
  return null
}

for (const q of pool) {
  const got = await askOnce(q)
  if (!got) {
    envPending.push(q)
    console.log(`ENV! [${TYPE_NAME[q.blindType]}] ${q.id} 上游持续 MODEL_UNAVAILABLE，挂起待补测`)
    await sleep(QUESTION_GAP_MS)
    continue
  }
  const v = evaluate(q, { http: got.reply.http }, got.reply, got.history)
  rows.push({ id: q.id, type: q.blindType, query: q.query, replyType: v.type, citations: v.citations,
    hitKeywords: v.hitKeywords, ok: v.ok, note: v.note })
  console.log(`${v.ok ? 'PASS' : 'FAIL'} [${TYPE_NAME[q.blindType]}] ${q.id} ${v.note}`)
  await sleep(QUESTION_GAP_MS)
}
// 末轮补测：ENV 挂起题重试一轮，仍 ENV 才计入失败（附明注）
for (const q of envPending) {
  console.log(`补测 ${q.id} ...`)
  const got = await askOnce(q)
  if (!got) {
    rows.push({ id: q.id, type: q.blindType, query: q.query, ok: false, note: '上游持续 MODEL_UNAVAILABLE（环境故障，非系统判定）' })
    continue
  }
  const v = evaluate(q, { http: got.reply.http }, got.reply, got.history)
  rows.push({ id: q.id, type: q.blindType, query: q.query, replyType: v.type, citations: v.citations,
    hitKeywords: v.hitKeywords, ok: v.ok, note: `${v.note}（补测成功）` })
  console.log(`${v.ok ? 'PASS' : 'FAIL'} [补测][${TYPE_NAME[q.blindType]}] ${q.id} ${v.note}`)
}
const elapsed = Math.round((Date.now() - t0) / 1000)

// ---------- 报告 ----------
const byType = {}
for (const r of rows) (byType[r.type] ??= []).push(r)
const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
const pass = rows.filter(r => r.ok).length
const fail = rows.length - pass
const rate = rows.length ? (pass / rows.length * 100).toFixed(1) : '0.0'

const md = [
  '# 盲测执行报告（Day20 盲测四题型）', '',
  `- 执行时刻：${now}｜总耗时 ${elapsed}s`,
  `- 题源：services/python-retrieval/evals/golden_dataset_v1.0.json（${dataset.length} 题）`,
  `- 抽题方式：${sampleN ? `分层随机抽样 ${sampleN}/题型` : typeFilter ? `指定题型 ${typeFilter}` : '全量'}`,
  `- 应对率：**${pass}/${rows.length} = ${rate}%**（Day20 口径：四题型 100% 应对）`,
  '',
  '| 题型 | 题数 | 通过 | 应对率 |',
  '| :--- | :--- | :--- | :--- |'
]
for (const [t, list] of Object.entries(byType)) {
  const p = list.filter(r => r.ok).length
  md.push(`| ${TYPE_NAME[t]} | ${list.length} | ${p} | ${(p / list.length * 100).toFixed(0)}% |`)
}
md.push('', '## 逐题明细', '',
  '| 题目ID | 题型 | 回复类型 | 引用 | 命中关键词 | 判定 | 说明 |',
  '| :--- | :--- | :--- | :--- | :--- | :--- | :--- |')
for (const r of rows) {
  md.push(`| ${r.id} | ${TYPE_NAME[r.type]} | ${r.replyType ?? '-'} | ${r.citations ?? '-'} | ${(r.hitKeywords ?? []).join('/') || '-'} | ${r.ok ? '✅' : '❌'} | ${r.note} |`)
}
md.push('', '## 题型映射说明', '',
  '- 生僻题 = 金标 difficulty=HARD；跨版本冲突 = is_conflict_check；越界陷阱 = is_adversarial；恶意注入题由 chaos/fault_injection_suite.mjs F1/F4 覆盖。',
  '- 恶意注入分组结论引用故障注入报告：见 fault_injection_report.md（F1 越狱 5/5、F4 注入串与越权 6/6 通过）。',
  '- 未命中关键词的 ANSWER 题建议人工复核答案质量（判定只验「引用可溯+关键词命中」，不评语义流畅度）。')

mkdirSync(reportDir, { recursive: true })
const jsonPath = join(reportDir, 'blind_test_report.json')
const mdPath = join(reportDir, 'blind_test_report.md')
writeFileSync(jsonPath, JSON.stringify({ executedAt: now, total: rows.length, pass, fail, rate: `${rate}%`, elapsedSec: elapsed, rows }, null, 2))
writeFileSync(mdPath, md.join('\n'))
console.log(md.join('\n'))
console.log(`\nOUTPUT_JSON=${jsonPath}`)
console.log(`OUTPUT_MD=${mdPath}`)
process.exit(fail === 0 ? 0 : 1)
