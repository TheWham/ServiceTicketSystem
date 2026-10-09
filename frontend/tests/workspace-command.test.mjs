import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function command() {
  const { descriptor } = parse(readFileSync(new URL('../src/components/WorkspaceSearch.vue', import.meta.url), 'utf8'))
  const compiled = compileScript(descriptor, { id: 'command' })
  const modules = { vue, 'reka-ui': {}, '@element-plus/icons-vue': {} }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, name) => `const {${names}} = modules[${JSON.stringify(name)}]`).replace('export default', 'return')
  const events = []
  const state = new Function('modules', code)(modules).setup({ modelValue: true, items: [
    { id: 'tickets', label: '工单', description: '我的工作' }, { id: 'knowledge', label: '知识', description: '知识库' }
  ] }, { expose() {}, emit: (...args) => events.push(args) })
  return { state, events }
}
test('IME confirmation and candidate arrows do not select a command or prevent composition', () => {
  const { state, events } = command()
  let prevented = 0
  for (const key of ['ArrowDown', 'Enter']) state.onKeydown({ key, isComposing: true, preventDefault() { prevented++ } })
  assert.equal(state.selected.value, 0)
  assert.equal(prevented, 0)
  assert.deepEqual(events, [])
})
test('normal command arrows and Enter choose the highlighted result', () => {
  const { state, events } = command()
  const event = key => ({ key, preventDefault() {} })
  state.onKeydown(event('ArrowDown'))
  state.onKeydown(event('Enter'))
  assert.deepEqual(events, [['update:modelValue', false], ['select', 'knowledge']])
})
