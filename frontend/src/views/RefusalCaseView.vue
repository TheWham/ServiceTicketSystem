<template>
  <div class="refusal-page">
    <div class="page-head">
      <div><span class="page-eyebrow">BAD CASE TRIAGE</span><h1 class="page-title">拒答处置</h1><p class="page-sub">AI 拒答记录实时联查,人工分诊:知识缺口进黄金集正常区,越界题进对抗区,噪音丢弃</p></div>
      <div class="heading-actions"><el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button></div>
    </div>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="load">重新加载</el-button></el-alert>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="section-title">拒答记录</span>
          <div class="filter-bar">
            <el-select v-model="filterStatus" style="width: 130px" @change="() => { page = 1; load() }">
              <el-option label="待处置" value="PENDING" />
              <el-option label="已处置" value="REVIEWED" />
              <el-option label="全部" value="ALL" />
            </el-select>
            <el-input v-model="keyword" placeholder="搜索提问关键词" clearable style="width: 220px" @keyup.enter="() => { page = 1; load() }" @clear="() => { page = 1; load() }" />
            <el-button type="primary" plain @click="() => { page = 1; load() }">查询</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" stripe :empty-text="loadError ? '拒答记录加载失败，请重试' : '当前筛选条件下暂无拒答记录'">
        <el-table-column prop="sessionId" label="会话" width="190" show-overflow-tooltip />
        <el-table-column prop="questionText" label="员工提问" min-width="260" show-overflow-tooltip />
        <el-table-column label="拒答原因" width="200">
          <template #default="{ row }">
            <el-tag :type="reasonTagType(row.refusalReason)" size="small">{{ reasonMap[row.refusalReason] || row.refusalReason || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="90">
          <template #default="{ row }">{{ row.confidence == null ? '—' : Number(row.confidence).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="sentAt" label="发生时间" width="170">
          <template #default="{ row }">{{ formatTime(row.sentAt) }}</template>
        </el-table-column>
        <el-table-column label="处置状态" width="170">
          <template #default="{ row }">
            <template v-if="row.reviewStatus === 'REVIEWED'">
              <el-tag :type="decisionTagType(row.decision)" size="small" effect="dark">{{ decisionMap[row.decision] || row.decision }}</el-tag>
            </template>
            <el-tag v-else type="warning" size="small">待处置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.reviewStatus === 'PENDING'" link type="primary" size="small" @click="openReview(row)">处置</el-button>
            <el-button v-else link size="small" @click="openReview(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, prev, pager, next, sizes" :total="total"
          :current-page="page" :page-size="pageSize" :page-sizes="[10, 15, 30, 50]"
          @current-change="(p) => { page = p; load() }" @size-change="(s) => { pageSize = s; page = 1; load() }" />
      </div>
    </el-card>

    <!-- 处置弹窗 -->
    <el-dialog v-model="reviewVisible" title="拒答案例处置" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="false">
      <template v-if="current">
        <el-descriptions :column="1" border size="small" class="case-brief">
          <el-descriptions-item label="员工提问">{{ current.questionText || '（未捕获提问原文）' }}</el-descriptions-item>
          <el-descriptions-item label="拒答原因">{{ reasonMap[current.refusalReason] || current.refusalReason || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-form :model="reviewForm" label-position="top" class="review-form">
          <el-form-item label="处置决策" required>
            <el-radio-group v-model="reviewForm.decision">
              <el-radio-button value="GOLDEN_QA">进黄金集·正常区</el-radio-button>
              <el-radio-button value="GOLDEN_REFUSAL">进黄金集·对抗区</el-radio-button>
              <el-radio-button value="DISCARD">丢弃</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <template v-if="reviewForm.decision !== 'DISCARD'">
            <el-form-item label="黄金集问题正文">
              <el-input v-model="reviewForm.goldenQuery" type="textarea" :rows="2" placeholder="缺省取员工提问原文" />
            </el-form-item>
            <el-form-item :label="reviewForm.decision === 'GOLDEN_QA' ? '标准答案（必填,补知识后的期望回答）' : '期望拒答话术（对抗区可留空用默认）'">
              <el-input v-model="reviewForm.goldenAnswer" type="textarea" :rows="2"
                :placeholder="reviewForm.decision === 'GOLDEN_QA' ? '补知识后系统应给出的标准答案' : '默认: 系统应给出确定性拒答并引导转人工/提单'" />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="分类">
                  <el-input v-model="reviewForm.category" :placeholder="reviewForm.decision === 'GOLDEN_QA' ? '知识缺口补录' : '越界拒答'" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="难度">
                  <el-select v-model="reviewForm.difficulty" style="width: 100%">
                    <el-option label="EASY" value="EASY" /><el-option label="MEDIUM" value="MEDIUM" /><el-option label="HARD" value="HARD" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item :label="reviewForm.decision === 'GOLDEN_QA' ? '期望关键词(逗号分隔)' : '拒答验证关键词(缺省: 转人工)'">
              <el-input v-model="reviewForm.expectedKeywords" placeholder="如: 转人工,不能执行操作" />
            </el-form-item>
            <el-alert v-if="reviewForm.decision === 'GOLDEN_QA'" type="info" :closable="false" show-icon
              title="GOLDEN_QA 前请先在「知识管理」补发对应知识文章并发布,再标定答案;只进黄金集不补知识会把缺陷固化成预期行为。" />
            <el-alert v-else type="warning" :closable="false" show-icon
              title="对抗样本回归时验证「仍然拒答」——这不是缺陷,是设计性拒答的正确归宿。" />
          </template>
          <el-form-item label="处置备注">
            <el-input v-model="reviewForm.reviewNote" type="textarea" :rows="2" placeholder="选填,审计追溯用" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="reviewing" :disabled="current?.reviewStatus === 'REVIEWED'" @click="doReview">提交处置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { refusalApi } from '../api/index.js'

const reasonMap = {
  NO_RELIABLE_KNOWLEDGE: '无可靠知识', LOW_CONFIDENCE: '置信度不足', CONFLICTING_KNOWLEDGE: '知识冲突',
  HIGH_RISK_TOPIC: '高风险话题', MODEL_UNAVAILABLE: '服务不可用', POLICY_BLOCKED: '策略拦截', OFF_TOPIC: '越界话题',
  OUT_OF_SCOPE: '不在能力范围'
}
const reasonTagType = (r) => ({ HIGH_RISK_TOPIC: 'danger', POLICY_BLOCKED: 'danger', OFF_TOPIC: 'info', MODEL_UNAVAILABLE: 'warning' }[r] || 'primary')
const decisionMap = { GOLDEN_QA: '已进黄金集·正常区', GOLDEN_REFUSAL: '已进对抗区', DISCARD: '已丢弃' }
const decisionTagType = (d) => ({ GOLDEN_QA: 'success', GOLDEN_REFUSAL: 'danger', DISCARD: 'info' }[d] || 'info')

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(15)
const filterStatus = ref('PENDING')
const keyword = ref('')
const loading = ref(false)
const loadError = ref('')

const reviewVisible = ref(false)
const reviewing = ref(false)
const current = ref(null)
const reviewForm = ref({ decision: 'GOLDEN_REFUSAL', goldenQuery: '', goldenAnswer: '', category: '', difficulty: 'HARD', expectedKeywords: '', reviewNote: '' })

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await refusalApi.list({ page: page.value, pageSize: pageSize.value, status: filterStatus.value, keyword: keyword.value || undefined })
    items.value = res?.data?.items || []
    total.value = res?.data?.total || 0
  } catch (e) {
    loadError.value = e.message || '拒答记录加载失败'
  } finally {
    loading.value = false
  }
}

function openReview(row) {
  current.value = row
  const adversarialFirst = ['HIGH_RISK_TOPIC', 'POLICY_BLOCKED', 'OFF_TOPIC'].includes(row.refusalReason)
  reviewForm.value = {
    decision: row.reviewStatus === 'REVIEWED' ? (row.decision || 'DISCARD') : (adversarialFirst ? 'GOLDEN_REFUSAL' : 'GOLDEN_QA'),
    goldenQuery: row.questionText || '',
    goldenAnswer: '',
    category: '',
    difficulty: 'HARD',
    expectedKeywords: adversarialFirst ? '转人工' : '',
    reviewNote: ''
  }
  reviewVisible.value = true
}

async function doReview() {
  const f = reviewForm.value
  if (!f.decision) { ElMessage.warning('请选择处置决策'); return }
  reviewing.value = true
  try {
    await refusalApi.review(current.value.messageId, {
      decision: f.decision,
      reviewNote: f.reviewNote || undefined,
      goldenQuery: f.goldenQuery || undefined,
      goldenAnswer: f.goldenAnswer || undefined,
      category: f.category || undefined,
      difficulty: f.difficulty || undefined,
      expectedKeywords: f.expectedKeywords || undefined
    })
    ElMessage.success('处置完成' + (f.decision === 'DISCARD' ? '' : ',已写入黄金数据集'))
    reviewVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '处置失败')
  } finally {
    reviewing.value = false
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
.refusal-page { min-width:0; }
.page-head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:24px; }
.page-eyebrow { display:block; color:var(--el-color-primary); font-size:12px; font-weight:700; letter-spacing:1.4px; margin-bottom:8px; }
.page-title { margin:0; font-size:28px; line-height:1.3; color:var(--el-text-color-primary); }
.page-sub { margin:8px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); max-width:640px; }
.section-title { font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.card-header { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
.filter-bar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.pager { display:flex; justify-content:flex-end; margin-top:16px; }
.page-error { margin-bottom:16px; }
.case-brief { margin-bottom:16px; }
.review-form { margin-top:4px; }
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
