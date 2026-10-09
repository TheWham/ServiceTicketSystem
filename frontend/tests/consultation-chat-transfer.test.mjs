import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/components/ConsultationChat.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../src/api/consultation.js', import.meta.url), 'utf8')

test('feedback transfer opens the numbered category picker before submitting', () => {
  assert.match(source, /@click="openTransfer\(msg\)"/)
  assert.match(source, /el-radio-group v-else v-model="transferForm\.categoryId"/)
  assert.match(source, /\{\{ index \+ 1 \}\}/)
  assert.doesNotMatch(source, /escalateFromFeedback/)
})

test('waiting employee can cancel the queue through the existing close API', () => {
  assert.match(source, /@click="cancelQueue"/)
  assert.match(source, /async function cancelQueue\(\)/)
  assert.match(source, /consultationApi\.close\(session\.value\.sessionId, '员工取消人工客服排队'\)/)
  assert.match(source, /员工已取消人工客服排队/)
})

test('one-click close does not ask the employee to type a reason', () => {
  assert.match(source, /consultationApi\.close\(session\.value\.sessionId, '员工主动结束咨询'\)/)
  assert.doesNotMatch(source, /prompt\('请简单说明结束原因'/)
})

test('close requests include the required reason body without prompting the employee', () => {
  assert.match(apiSource, /close: \(id, reason = '[^']+'\) => http\.post\(`\/consultations\/\$\{id\}\/close`, \{ reason \}\)/)
  assert.match(source, /consultationApi\.close\(session\.value\.sessionId, '员工取消人工客服排队'\)/)
  assert.match(source, /consultationApi\.close\(session\.value\.sessionId, '员工主动结束咨询'\)/)
  assert.doesNotMatch(source, /prompt\('请简单说明结束原因'/)
})

test('waiting state renders only the assigned engineer queue count', () => {
  assert.match(source, /consultationApi\.queueStatus\(session\.value\.sessionId\)/)
  assert.match(source, /当前排队 <strong>\{\{ queueCount \}\}<\/strong> 人/)
  assert.match(source, /queueStatus\.assigned/)
  assert.doesNotMatch(source, /engineerName|接待工程师/)
})
