import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'
import * as editing from '../src/utils/ticketEditing.js'
import { ticketToForm, ticketTypeLabel, ticketNatureLabel, editableTicketPayload, canWithdrawTicket } from '../src/utils/ticketEditing.js'

test('withdraw is available only to the owner of an active ticket', () => {
  for (const status of ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE']) {
    assert.equal(canWithdrawTicket({ creator_id: 'U1', status }, 'U1'), true)
    assert.equal(canWithdrawTicket({ creator_id: 'U1', status }, 'OTHER'), false)
  }
  for (const status of ['CANCELLED', 'COMPLETED', 'CLOSED', undefined]) {
    assert.equal(canWithdrawTicket({ creator_id: 'U1', status }, 'U1'), false)
  }
})

test('editing restores all submitted fields and normalizes empty optional values', () => {
  const ticket = { ticket_id: 'T1', nature: 'SERVICE_REQUEST', category_id: 'C1', title: '软件安装',
    description: '安装客户端', impact_description: '本人', urgency_description: '今天',
    location: '301', contact: '123', asset_id: null, status: 'IN_PROGRESS', attachments: ['A1'] }
  assert.deepEqual(ticketToForm(ticket), { nature: 'SERVICE_REQUEST', category_id: 'C1', title: '软件安装',
    description: '安装客户端', impact_description: '本人', urgency_description: '今天', location: '301', contact: '123', asset_id: '' })
  assert.equal(ticket.asset_id, null)
})

test('category display uses historical snapshot and supports legacy or incomplete responses', () => {
  assert.equal(ticketTypeLabel({ category_snapshot: '硬件/打印机', category_name: '已改名', category_id: 'C1' }), '硬件/打印机')
  assert.equal(ticketTypeLabel({ category_name: '网络' }), '网络')
  assert.equal(ticketTypeLabel({ category_id: 'C1' }), 'C1')
  assert.equal(ticketTypeLabel({}), '未记录')
  assert.equal(ticketNatureLabel('INCIDENT'), '故障报修')
  assert.equal(ticketNatureLabel('SERVICE_REQUEST'), '服务申请')
})

test('saving includes only editable content and final attachment IDs, never timing or state fields', () => {
  const payload = editableTicketPayload({ nature: 'INCIDENT', category_id: 'C1', title: ' 标题 ', description: ' 描述 ',
    impact_description: ' 影响 ', urgency_description: ' 紧急 ', location: ' ', contact: '', asset_id: ' PC01 ',
    status: 'NEW', priority: 'HIGH', created_at: 'tomorrow', source_session_id: 'S1' }, ['A2', 'A3'])
  assert.deepEqual(payload, { title: '标题', description: '描述', impact_description: '影响', urgency_description: '紧急',
    location: null, contact: null, asset_id: 'PC01', attachments: ['A2', 'A3'] })
  assert.deepEqual(editableTicketPayload({}, []).attachments, [])
})

function employee() {
  const writes = [], deleted = [], savedDrafts = []
  const route = vue.reactive({ path: '/employee', query: { tab: 'list' } })
  const api = {
    ticketApi: { edit: async (...args) => writes.push(args), list: async () => ({ data: { list: [], total: 0 } }),
      detail: async () => ({ data: { ticket, flow_logs: [] } }) },
    draftApi: { save: async body => savedDrafts.push(body) }, categoryApi: {},
    attachmentApi: { upload: async () => ({ data: { attachment_id: 'NEW' } }), remove: async id => deleted.push(id) }
  }
  const modules = {
    vue: { ...vue, watch() {}, onMounted() {}, onUnmounted() {} },
    'vue-router': { useRoute: () => route, useRouter: () => ({ push: async to => { route.query = to.query } }) },
    'element-plus': { ElMessage: { success() {}, error() {}, info() {} }, ElMessageBox: {} },
    '@element-plus/icons-vue': {}, '../api/index.js': api, '../api/consultation.js': { consultationApi: {} },
    '../utils/attachmentPhotos.js': { loadPhotoUrls: async () => [], revokePhotoUrls() {} },
    '../utils/ticketEditing.js': editing, '../stores/user.js': { useUserStore: () => ({ userId: 'U1' }) },
    '../components/SlaBadge.vue': {}, '../components/SlaTimer.vue': {}
  }
  const { descriptor } = parse(readFileSync(new URL('../src/views/EmployeeView.vue', import.meta.url), 'utf8'))
  const code = compileScript(descriptor, { id: 'ticket-edit-test' }).content
    .replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
      (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+)['"]/g,
      (_, name, path) => `const ${name} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const c = new Function('modules', code)(modules).setup({}, { expose() {} })
  c.formRef.value = { validate: async () => true, clearValidate() {} }
  return { c, api, writes, deleted, savedDrafts, route }
}

const ticket = { ticket_id: 'T1', creator_id: 'U1', nature: 'INCIDENT', category_id: 'C1',
  category_snapshot: '网络/办公网络', title: '原标题', description: '原描述', impact_description: '本人',
  urgency_description: '今天', status: 'IN_PROGRESS', attachments: ['OLD'] }

test('cancel restores new-ticket draft and does not remove original ticket photos', async () => {
  const { c, deleted, savedDrafts } = employee()
  c.form.value.title = '新建草稿'
  c.photoIds.value = ['DRAFT']
  await c.startEdit(ticket)
  assert.equal(c.form.value.title, '原标题')
  c.removePhoto({ response: { attachment_id: 'OLD' } })
  assert.deepEqual(c.photoIds.value, [])
  assert.deepEqual(deleted, [])
  await c.saveDraft()
  assert.deepEqual(savedDrafts, [])
  c.cancelEdit()
  assert.equal(c.form.value.title, '新建草稿')
  assert.deepEqual(c.photoIds.value, ['DRAFT'])
  assert.equal(c.editingTicket.value, null)
})

test('a withdrawn ticket cannot enter edit mode even through a stale action', async () => {
  const { c } = employee()
  await c.startEdit({ ...ticket, status: 'CANCELLED' })
  assert.equal(c.editingTicket.value, null)
})

test('saving edited content targets original ticket and preserves new-ticket draft', async () => {
  const { c, writes } = employee()
  c.form.value.title = '新建草稿'
  await c.startEdit(ticket)
  c.form.value.title = '更新标题'
  await c.submitTicket()
  assert.equal(writes.length, 1)
  assert.equal(writes[0][0], 'T1')
  assert.equal(writes[0][1].title, '更新标题')
  assert.equal(writes[0][1].nature, undefined)
  assert.equal(c.form.value.title, '新建草稿')
  assert.equal(c.detailVisible.value, true)
})

test('save failure retains edited text for retry', async () => {
  const { c, api } = employee()
  await c.startEdit(ticket)
  api.ticketApi.edit = async () => { throw new Error('offline') }
  c.form.value.title = '未保存的修改'
  await c.submitTicket()
  assert.equal(c.form.value.title, '未保存的修改')
  assert.equal(c.editingTicket.value.ticket_id, 'T1')
  assert.match(c.submitError.value, /offline/)
  assert.equal(c.submitting.value, false)
})

test('deduplicated upload cannot steal an attachment from the backed up new-ticket draft', async () => {
  const { c, api, deleted } = employee()
  c.photoIds.value = ['DRAFT']
  await c.startEdit(ticket)
  c.photoList.value.push({ uid: 'upload-1', status: 'ready' })
  api.attachmentApi.upload = async () => ({ data: { attachment_id: 'DRAFT' } })
  await assert.rejects(c.uploadPhoto({ file: { uid: 'upload-1' } }), /新工单草稿/)
  assert.deepEqual(c.photoIds.value, ['OLD'])
  assert.deepEqual(deleted, [])
})

test('removing an in-flight upload cannot allow switching its result into a different form', async () => {
  const { c, api } = employee()
  await c.startEdit(ticket)
  let finish
  api.attachmentApi.upload = () => new Promise(resolve => { finish = resolve })
  c.photoList.value.push({ uid: 'upload-1', status: 'ready' })
  const pending = c.uploadPhoto({ file: { uid: 'upload-1' }, onSuccess() {}, onError() {} })
  c.photoList.value = []
  assert.equal(c.photoUploading.value, true)
  c.cancelEdit()
  assert.equal(c.editingTicket.value.ticket_id, 'T1')
  finish({ data: { attachment_id: 'LATE' } })
  await pending
  assert.equal(c.photoIds.value.includes('LATE'), false)
})
