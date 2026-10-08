import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { computed, reactive, ref } from 'vue'

const knowledge = readFileSync(new URL('../src/views/KnowledgeAdminView.vue', import.meta.url), 'utf8')
const supervisor = readFileSync(new URL('../src/views/SupervisorView.vue', import.meta.url), 'utf8')

// Evaluate the production setup blocks with Vue reactivity and controlled API/router boundaries.
test('knowledge tab follows deep links and route history, retaining other query parameters', () => {
  const block = knowledge.match(/const activeTab = computed\(\{[\s\S]*?\n\}\)/)?.[0]
  assert.ok(block)
  const route = reactive({ path: '/knowledge-admin', query: { tab: 'lifecycle', article: 'A1' } })
  const navigations = []
  const router = { push: location => navigations.push(location) }
  const tab = new Function('computed', 'route', 'router', `${block}; return activeTab`)(computed, route, router)
  assert.equal(tab.value, 'lifecycle')
  tab.value = 'ingest'
  assert.deepEqual(navigations[0], { path: '/knowledge-admin', query: { tab: 'ingest', article: 'A1' } })
  route.query = navigations[0].query
  assert.equal(tab.value, 'ingest')
  route.query = { tab: 'lifecycle' }
  assert.equal(tab.value, 'lifecycle')
  route.query = { tab: 'invalid' }
  assert.equal(tab.value, 'ingest')
})

test('changing supervisor filters fetches page one', () => {
  const block = supervisor.match(/function applyFilters\(\) \{[\s\S]*?\n\}/)?.[0]
  assert.ok(block)
  const page = ref(7)
  const requestedPages = []
  const apply = new Function('page', 'loadTickets', `${block}; return applyFilters`)(page, () => requestedPages.push(page.value))
  apply()
  assert.equal(page.value, 1)
  assert.deepEqual(requestedPages, [1])
})
