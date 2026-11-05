import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/components/ConsultationChat.vue', import.meta.url), 'utf8')

test('ConsultationChat provides history drawer and new chat actions', () => {
  // 1. 顶部操作栏提供开启新咨询与历史会话入口
  assert.match(source, /@click="handleStartNewSession"/)
  assert.match(source, /@click="openHistoryDrawer"/)
  assert.match(source, /开启新咨询/)
  assert.match(source, /历史会话/)

  // 2. 抽屉包含最近1个月文案与切换逻辑
  assert.match(source, /v-model="historyDrawerVisible"/)
  assert.match(source, /最近咨询会话 \(近1个月\)/)
  assert.match(source, /仅展示最近 30 天内的咨询记录/)
  assert.match(source, /@click="switchSession\(s\)"/)
})

test('ConsultationChat toLocalMessage reads persisted thought stages and duration', () => {
  assert.match(source, /const persistedStages = item\.thought_stages \|\| item\.thoughtStages \|\| item\.metadata\?\.thought_stages/)
  assert.match(source, /const persistedDuration = item\.thinking_duration \|\| item\.thinkingDuration \|\| 1/)
  assert.match(source, /thoughtStages: \(persistedStages && persistedStages\.length\) \? persistedStages : stages/)
  assert.match(source, /thinkingDuration: persistedDuration/)
})
