<template>
  <div class="golden-page">
    <div class="page-head">
      <div><span class="page-eyebrow">GOLDEN DATASET</span><h1 class="page-title">黄金数据集</h1><p class="page-sub">评测基准唯一真源:种子导入 + bad case 处置沉淀;导出后供 6:2:2 回归评测</p></div>
      <div class="heading-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增条目</el-button>
      </div>
    </div>

    <div class="stat-row">
      <el-tag effect="plain" size="large">有效条目 {{ stats.total ?? '—' }}</el-tag>
      <el-tag type="danger" effect="plain" size="large">对抗样本 {{ stats.adversarial ?? '—' }}</el-tag>
      <el-tag type="warning" effect="plain" size="large">bad case 沉淀 {{ stats.fromBadCase ?? '—' }}</el-tag>
    </div>

    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="load">重新加载</el-button></el-alert>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="section-title">条目列表</span>
          <div class="filter-bar">
            <el-select v-model="filterAdversarial" placeholder="全部类型" clearable style="width: 130px" @change="() => { page = 1; load() }">
              <el-option label="正常样本" :value="false" />
              <el-option label="对抗样本" :value="true" />
            </el-select>
            <el-select v-model="filterSource" placeholder="全部来源" clearable style="width: 150px" @change="() => { page = 1; load() }">
              <el-option label="种子导入" value="SEED" />
              <el-option label="bad case 沉淀" value="BAD_CASE" />
              <el-option label="手工新增" value="MANUAL" />
            </el-select>
            <el-input v-model="keyword" placeholder="搜索问题正文" clearable style="width: 220px" @keyup.enter="() => { page = 1; load() }" @clear="() => { page = 1; load() }" />
            <el-button type="primary" plain @click="() => { page = 1; load() }">查询</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" stripe :empty-text="loadError ? '黄金集加载失败，请重试' : '暂无条目'">
        <el-table-column prop="naturalKey" label="ID" width="180" show-overflow-tooltip />
        <el-table-column prop="query" label="问题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="130" show-overflow-tooltip />
        <el-table-column prop="difficulty" label="难度" width="90" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isAdversarial ? 'danger' : 'success'" size="small">{{ row.isAdversarial ? '对抗' : '正常' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            <el-tag :type="sourceTagType(row.sourceType)" size="small" effect="plain">{{ sourceMap[row.sourceType] || row.sourceType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdBy" label="创建人" width="120" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="doRemove(row)">移出</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, prev, pager, next, sizes" :total="total"
          :current-page="page" :page-size="pageSize" :page-sizes="[10, 15, 30, 50]"
          @current-change="(p) => { page = p; load() }" @size-change="(s) => { pageSize = s; page = 1; load() }" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑黄金条目' : '新增黄金条目'" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="问题正文" required>
          <el-input v-model="editForm.query" type="textarea" :rows="2" placeholder="员工视角的问题原文" />
        </el-form-item>
        <el-form-item label="标准答案" required>
          <el-input v-model="editForm.groundTruthAnswer" type="textarea" :rows="2"
            placeholder="正常样本:期望回答;对抗样本:期望拒答话术" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="editForm.category" placeholder="如 系统修复 / 越界拒答" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="难度">
              <el-select v-model="editForm.difficulty" style="width: 100%">
                <el-option label="EASY" value="EASY" /><el-option label="MEDIUM" value="MEDIUM" /><el-option label="HARD" value="HARD" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="期望关键词(逗号分隔)">
          <el-input v-model="editForm.expectedKeywords" placeholder="如: sfc /scannow,系统文件" />
        </el-form-item>
        <el-form-item label="对抗样本(回归时验证仍然拒答)">
          <el-switch v-model="editForm.isAdversarial" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { goldenCaseApi } from '../api/index.js'

const sourceMap = { SEED: '种子导入', BAD_CASE: 'bad case', MANUAL: '手工新增' }
const sourceTagType = (s) => ({ SEED: 'info', BAD_CASE: 'warning', MANUAL: 'primary' }[s] || 'info')

const items = ref([])
const stats = ref({})
const total = ref(0)
const page = ref(1)
const pageSize = ref(15)
const filterAdversarial = ref(null)
const filterSource = ref(null)
const keyword = ref('')
const loading = ref(false)
const loadError = ref('')

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({ id: null, query: '', groundTruthAnswer: '', category: '', difficulty: 'MEDIUM', expectedKeywords: '', isAdversarial: false })

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await goldenCaseApi.list({
      page: page.value, pageSize: pageSize.value,
      isAdversarial: filterAdversarial.value ?? undefined,
      sourceType: filterSource.value || undefined,
      keyword: keyword.value || undefined
    })
    const data = res?.data || {}
    items.value = data.items || []
    total.value = data.total || 0
    stats.value = data.stats || {}
  } catch (e) {
    loadError.value = e.message || '黄金集加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editForm.value = { id: null, query: '', groundTruthAnswer: '', category: '', difficulty: 'MEDIUM', expectedKeywords: '', isAdversarial: false }
  editVisible.value = true
}

function openEdit(row) {
  editForm.value = {
    id: row.id,
    query: row.query,
    groundTruthAnswer: row.groundTruthAnswer,
    category: row.category,
    difficulty: row.difficulty,
    expectedKeywords: (row.expectedKeywords || []).join(','),
    isAdversarial: !!row.isAdversarial
  }
  editVisible.value = true
}

async function doSave() {
  const f = editForm.value
  if (!f.query || !f.groundTruthAnswer) {
    ElMessage.warning('请填写问题正文与标准答案')
    return
  }
  saving.value = true
  try {
    await goldenCaseApi.upsert({
      id: f.id || undefined,
      query: f.query,
      groundTruthAnswer: f.groundTruthAnswer,
      category: f.category || undefined,
      difficulty: f.difficulty || undefined,
      expectedKeywords: f.expectedKeywords || undefined,
      isAdversarial: f.isAdversarial
    })
    ElMessage.success(f.id ? '条目已更新' : '条目已加入黄金数据集')
    editVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function doRemove(row) {
  try {
    await ElMessageBox.confirm(`确定把「${row.query.slice(0, 30)}…」移出黄金数据集?移出后不再参与评测。`, '移出确认', { type: 'warning' })
  } catch { return }
  try {
    await goldenCaseApi.remove(row.id)
    ElMessage.success('已移出(软删,可追溯)')
    load()
  } catch (e) {
    ElMessage.error(e.message || '移出失败')
  }
}

function formatTime(value) {
  if (!value) return '—'
  // 后端 LocalDateTime 序列化不带时区,值本身是 UTC(Times.nowUtc());补 Z 转本地时区显示
  const s = String(value)
  const hasZone = /Z$|[+-]\d{2}:?\d{2}$/.test(s)
  const d = new Date(hasZone ? s : s + 'Z')
  return isNaN(d.getTime()) ? s : d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<style scoped>
.golden-page { min-width:0; }
.page-head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px; }
.page-eyebrow { display:block; color:var(--el-color-primary); font-size:12px; font-weight:700; letter-spacing:1.4px; margin-bottom:8px; }
.page-title { margin:0; font-size:28px; line-height:1.3; color:var(--el-text-color-primary); }
.page-sub { margin:8px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); max-width:640px; }
.stat-row { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.section-title { font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.card-header { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
.filter-bar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.pager { display:flex; justify-content:flex-end; margin-top:16px; }
.page-error { margin-bottom:16px; }
:deep(.el-card) { border-radius:16px; }
:deep(.el-table .cell) { line-height:1.6; }
:deep(.el-dialog) { max-width:calc(100vw - 32px); border-radius:16px; }
@media(max-width:767px) {
  .page-head { flex-wrap:wrap; margin-bottom:20px; }
  .page-title { font-size:24px; }
  :deep(.el-card__body) { padding:16px; }
  :deep(.el-pagination) { flex-wrap:wrap; gap:8px; justify-content:center; }
}
</style>
