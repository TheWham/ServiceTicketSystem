import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function component(name, data) {
  const source = readFileSync(new URL(`../src/components/${name}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: name })
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {} },
    '@element-plus/icons-vue': {},
    '../api/index.js': { slaApi: { byTicket: async () => ({ data }) } }
  }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`).replace('export default', 'return')
  const options = new Function('modules', code)(modules)
  return options.setup({ ticketId: 'T1' }, { expose() {} })
}

test('SLA detail recognizes canonical MET and CANCELLED states', async () => {
  const c = component('SlaTimer', { status: 'MET' })
  await c.load()
  assert.equal(c.statusLabel.value, '已达标')
  assert.equal(c.progressTip.value, '已达到 SLA 完成目标')
  c.sla.value.status = 'CANCELLED'
  assert.equal(c.statusLabel.value, '已取消')
})

test('canonical breach timestamps remain visible even after SLA completion', async () => {
  const c = component('SlaTimer', { status: 'MET', breached_at: '2026-09-29T01:00:00Z' })
  await c.load()
  assert.equal(c.isBreached.value, true)
})

test('breached SLA is visible on the ticket card', async () => {
  const c = component('SlaBadge', { status: 'BREACHED', breached_at: '2026-09-29T01:00:00Z' })
  await c.load()
  assert.equal(c.showBadge.value, true)
  assert.equal(c.countdownText.value, '已违约')
})

test('ticket-card countdown uses the eight-hour service workday', async () => {
  const c = component('SlaBadge', { status: 'RUNNING', remaining_work_seconds: 86400 })
  await c.load()
  assert.equal(c.countdownText.value, '剩 3 工作日')
})
