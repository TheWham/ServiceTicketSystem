<template>
  <div class="kb-admin-container">
    <header class="page-head">
      <div><h1>知识库</h1><p>维护知识文章，审核内容并管理发布。</p></div>
      <el-button type="primary" :icon="UploadFilled" @click="activeTab = 'ingest'">上传文档</el-button>
    </header>

    <main class="kb-main-body">
      <el-tabs v-model="activeTab" class="kb-tabs">
      <el-tab-pane label="知识文章" name="lifecycle">
        <el-card shadow="never" class="box-card">
          <template #header>
            <div class="card-header-flex">
              <div class="card-header-title">
                <el-icon><Notebook /></el-icon>
                <span>知识文章列表</span>
              </div>
              <div class="list-toolbar">
                <el-input v-model="articleSearch" :prefix-icon="Search" clearable aria-label="搜索本页文章" placeholder="搜索本页文章" class="article-search" />
                <el-radio-group v-model="listQuery.status" size="small" @change="fetchArticles(1)">
                  <el-radio-button value="">全部</el-radio-button>
                  <el-radio-button value="DRAFT">草稿</el-radio-button>
                  <el-radio-button value="PENDING_REVIEW">待审核</el-radio-button>
                  <el-radio-button value="PUBLISHED">已发布</el-radio-button>
                  <el-radio-button value="OFFLINE">已下线</el-radio-button>
                </el-radio-group>
                <el-button size="small" :loading="listLoading" @click="fetchArticles()">刷新</el-button>
              </div>
            </div>
          </template>

          <div v-if="listError" class="error-state" role="alert">{{ listError }} <el-button @click="fetchArticles()">重试</el-button></div>
          <el-table
            v-if="!listError"
            :data="filteredArticles"
            @row-click="row => openDetail(row.articleId)"
            v-loading="listLoading"
            row-key="articleId"
            :empty-text="listLoading ? '正在加载文章…' : articleSearch.trim() ? '本页没有匹配的文章' : '暂无知识文章，请先上传文档'"
          >
            <el-table-column prop="articleId" label="文章ID" min-width="210" show-overflow-tooltip />
            <el-table-column prop="categoryId" label="分类" width="90" align="center" />
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.riskLevel === 'HIGH' ? 'danger' : 'info'" size="small" effect="plain">
                  {{ row.riskLevel === 'HIGH' ? '高风险' : '常规' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="currentVersionId" label="当前版本" min-width="190" show-overflow-tooltip />
            <el-table-column prop="updatedAt" label="更新时间" width="150">
              <template #default="{ row }">{{ formatTime(row.updatedAt) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click.stop="openDetail(row.articleId)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!listError" class="pager-row">
            <el-pagination
              v-model:current-page="listQuery.page"
              v-model:page-size="listQuery.pageSize"
              :total="articleTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              background
              @size-change="fetchArticles(1)"
              @current-change="fetchArticles()"
            />
          </div>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="上传与处理记录" name="ingest">
      <el-row :gutter="20">
        <!-- 左侧：文档上传与参数配置 -->
        <el-col :xs="24" :lg="9">
          <el-card shadow="never" class="box-card upload-card">
            <template #header>
              <div class="card-header-title">
                <el-icon><UploadFilled /></el-icon>
                <span>上传文档</span>
              </div>
            </template>

            <el-form label-position="top" size="default">
              <el-form-item label="选择文档 (.md, .txt)">
                <el-upload
                  drag
                  action="#"
                  :auto-upload="false"
                  :limit="1"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                  accept=".md,.txt,.markdown"
                  class="kb-uploader"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    拖拽 Markdown 或 TXT 文档到此处，或 <em>点击选取</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip">
                      支持 Markdown (.md) 与 纯文本 (.txt) 文件，单文件上限 20MB
                    </div>
                  </template>
                </el-upload>
              </el-form-item>

              <el-form-item label="文档标题（选填）">
                <el-input
                  v-model="uploadForm.title"
                  placeholder="留空则使用文档标题或文件名"
                  clearable
                />
              </el-form-item>

              <el-form-item label="所属知识分类" required>
                <div v-if="categoryLoading" role="status" class="category-state">正在加载分类…</div>
                <div v-else-if="categoryError" role="alert" class="error-state">{{ categoryError }} <el-button @click="fetchCategories">重试分类</el-button></div>
                <div v-else-if="!categories.length" class="category-state">暂无可用分类 <el-button @click="fetchCategories">刷新分类</el-button></div>
                <el-select v-else v-model="uploadForm.categoryId" placeholder="请选择分类" style="width: 100%">
                  <el-option v-for="category in categories" :key="category.category_id" :label="category.name" :value="category.category_id" />
                </el-select>
              </el-form-item>

              <el-collapse class="advanced-params">
                <el-collapse-item title="高级设置">
              <el-form-item label="入库方式">
                <el-radio-group v-model="uploadForm.publishNow">
                  <el-radio :value="false">存为草稿</el-radio>
                  <el-radio :value="true">直接发布</el-radio>
                </el-radio-group>
                <div v-if="uploadForm.publishNow" class="quick-warn">
                  直接发布后，文章立即可供搜索和客服引用。
                </div>
              </el-form-item>

                  <el-button :loading="isInitEs" @click="handleInitEsIndex">初始化 ES 索引</el-button>
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="目标切片大小 (字符数)">
                        <el-input-number
                          v-model="uploadForm.chunkSize"
                          :min="100"
                          :max="2000"
                          :step="50"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="切片重叠大小 (字符数)">
                        <el-input-number
                          v-model="uploadForm.chunkOverlap"
                          :min="0"
                          :max="500"
                          :step="10"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-collapse-item>
              </el-collapse>

              <div v-if="uploadError" class="error-state" role="alert">{{ uploadError }}</div>
              <div class="upload-action-bar">
                <el-button
                  type="primary"
                  size="large"
                  :loading="isProcessing"
                  :disabled="!selectedFile || categoryLoading || !!categoryError || !uploadForm.categoryId"
                  class="submit-btn"
                  @click="submitUploadAndProcess"
                >
                  <el-icon v-if="!isProcessing"><Cpu /></el-icon>
                  {{ isProcessing ? '正在处理…' : '上传并处理' }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <!-- 历史处理记录列表 -->
          <el-card shadow="never" class="box-card history-card" style="margin-top: 16px;">
            <template #header>
              <div class="card-header-flex">
                <div class="card-header-title">
                  <el-icon><Clock /></el-icon>
                  <span>最近处理记录</span>
                </div>
                <el-button link type="primary" size="small" @click="fetchRecentTraces">
                  刷新
                </el-button>
              </div>
            </template>
            <div v-if="historyLoading" class="empty-hint" role="status">正在加载处理记录…</div>
            <div v-else-if="historyError" class="error-state" role="alert">{{ historyError }} <el-button @click="fetchRecentTraces">重试</el-button></div>
            <div v-else-if="historyTraces.length === 0" class="empty-hint">
              暂无处理记录
            </div>
            <div v-else class="history-list">
              <button
                type="button"
                v-for="item in historyTraces"
                :key="item.traceId"
                class="history-item"
                :class="{ active: currentTrace?.traceId === item.traceId }"
                @click="loadTrace(item)"
              >
                <div class="history-item-top">
                  <span class="history-name">{{ item.documentName }}</span>
                  <el-tag :type="getStageTagType(item.status)" size="small">
                    {{ traceStatusLabel(item.status) }}
                  </el-tag>
                </div>
                <div class="history-item-meta">
                  <span>{{ item.chunks?.length || 0 }} 个切片</span>
                  <span>耗时 {{ item.totalDurationMs }}ms</span>
                  <span>{{ formatTime(item.startTime) }}</span>
                </div>
              </button>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：链路过程与切片明细 -->
        <el-col :xs="24" :lg="15">
          <!-- 链路总览卡片 -->
          <el-card shadow="never" class="box-card trace-card">
            <template #header>
              <div class="card-header-flex">
                <div class="card-header-title">
                  <el-icon><Connection /></el-icon>
                  <span>文档处理详情</span>
                </div>
                <span v-if="currentTrace" class="trace-id-badge">
                  记录编号：<code>{{ currentTrace.traceId }}</code>
                </span>
              </div>
            </template>

            <div v-if="!currentTrace" class="empty-trace-container">
              <el-empty description="上传文档或选择一条记录，查看处理结果" />
            </div>

            <div v-else>
              <!-- 概览指标行 -->
              <div class="trace-summary-banner">
                <div class="summary-metric">
                  <span class="label">文档名称</span>
                  <span class="value doc-title">{{ currentTrace.documentName }}</span>
                </div>
                <div class="summary-metric">
                  <span class="label">切片总数</span>
                  <span class="value highlight">{{ currentTrace.chunks?.length || 0 }} 块</span>
                </div>
                <div class="summary-metric">
                  <span class="label">处理耗时</span>
                  <span class="value">{{ currentTrace.totalDurationMs }} ms</span>
                </div>
                <div class="summary-metric">
                  <span class="label">处理状态</span>
                  <el-tag :type="getStageTagType(currentTrace.status)" effect="plain">{{ traceStatusLabel(currentTrace.status) }}</el-tag>
                </div>
              </div>

              <details class="advanced-trace"><summary>高级处理明细</summary>
              <!-- 链路步骤时间线 -->
              <div class="timeline-section">
                <h3 class="section-heading">处理步骤</h3>
                <el-timeline>
                  <el-timeline-item
                    v-for="(stage, idx) in currentTrace.stages"
                    :key="idx"
                    :type="getStageTagType(stage.status)"
                    :timestamp="`耗时: ${stage.durationMs}ms`"
                    placement="top"
                  >
                    <el-card class="stage-inner-card" shadow="never">
                      <div class="stage-title-row">
                        <span class="stage-name">【步骤 {{ idx + 1 }}】{{ stage.stageName }}</span>
                        <el-tag :type="getStageTagType(stage.status)" size="small">
                          {{ traceStatusLabel(stage.status) }}
                        </el-tag>
                      </div>
                      <p class="stage-desc">{{ stage.description }}</p>
                      <div class="stage-msg" :class="stage.status?.toLowerCase()">
                        <el-icon v-if="stage.status === 'SUCCESS'"><Check /></el-icon>
                        <span>{{ stage.message }}</span>
                      </div>
                      <!-- 指标卡 -->
                      <div v-if="stage.metrics" class="stage-metrics-grid">
                        <div v-for="(v, k) in stage.metrics" :key="k" class="metric-chip">
                          <span class="m-key">{{ formatMetricKey(k) }}:</span>
                          <span class="m-val">{{ v }}</span>
                        </div>
                      </div>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
              </div>

              <el-divider />

              <!-- 切片详情与内容预览 -->
              <div class="chunks-section">
                <div class="chunks-header">
                  <h3 class="section-heading">内容分段</h3>
                  <el-input
                    v-model="chunkSearchKeyword"
                    placeholder="搜索切片文本或标题..."
                    prefix-icon="Search"
                    size="small"
                    clearable
                    style="width: 240px"
                  />
                </div>

                <div class="chunk-list-container">
                  <el-collapse v-model="activeChunkNames">
                    <el-collapse-item
                      v-for="(chunk, cIdx) in filteredChunks"
                      :key="chunk.chunkId"
                      :name="chunk.chunkId"
                    >
                      <template #title>
                        <div class="chunk-collapse-title">
                          <span class="chunk-index">#{{ chunk.chunkIndex }}</span>
                          <span class="chunk-section-title">{{ chunk.title || '段落切片' }}</span>
                          <div class="chunk-tags">
                            <el-tag size="small" type="info">{{ chunk.charCount }} 字</el-tag>
                            <el-tag size="small" type="warning">约 {{ chunk.tokenCountEstimate }} Tokens</el-tag>
                            <el-tag size="small" type="success" effect="plain" v-if="chunk.hasVector || chunk.vectorDimensions">
                              {{ chunk.vectorDimensions || 1024 }} 维向量
                            </el-tag>
                            <el-tag size="small" :type="chunk.esDocId ? 'success' : 'info'">ES: {{ chunk.esDocId || '未确认' }}</el-tag>
                          </div>
                        </div>
                      </template>

                      <div class="chunk-body">
                        <div class="chunk-meta-bar">
                          <span><strong>切片ID:</strong> <code>{{ chunk.chunkId }}</code></span>
                          <el-button link type="primary" size="small" @click="copyText(chunk.content)">
                            复制本段切片
                          </el-button>
                        </div>
                        <pre class="chunk-content-view">{{ chunk.content }}</pre>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
              </details>
            </div>
          </el-card>
        </el-col>
      </el-row>
      </el-tab-pane>

      </el-tabs>
    </main>

    <!-- 知识详情与生命周期操作抽屉 -->
    <el-drawer
      :model-value="drawerVisible"
      @update:model-value="value => { if (!value) closeDetail() }"
      :title="`知识详情 · ${detail?.article?.articleId || ''}`"
      size="min(680px, 100vw)"
      :destroy-on-close="true"
    >
      <div class="drawer-body">
        <div v-if="detailLoading" role="status"><el-skeleton :rows="6" animated /></div>
        <div v-else-if="detailError" class="error-state" role="alert">{{ detailError }} <el-button @click="loadDetail(selectedArticleId)">重试</el-button></div>
        <template v-if="detail && detail.article">
          <el-descriptions title="文章信息" :column="2" border size="small">
            <el-descriptions-item label="文章ID" :span="2">{{ detail.article.articleId }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(detail.article.status)" effect="plain">
                {{ statusLabel(detail.article.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              {{ detail.article.riskLevel === 'HIGH' ? '高风险' : '常规' }}
            </el-descriptions-item>
            <el-descriptions-item label="分类">{{ detail.article.categoryId }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(detail.article.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatTime(detail.article.updatedAt) }}</el-descriptions-item>
          </el-descriptions>

          <template v-if="detail.currentVersion">
            <el-descriptions title="当前版本" :column="2" border size="small" class="mt-16">
              <el-descriptions-item label="版本ID" :span="2">{{ detail.currentVersion.versionId }}</el-descriptions-item>
              <el-descriptions-item label="版本号">v{{ detail.currentVersion.versionNo }}</el-descriptions-item>
              <el-descriptions-item label="标题" :span="2">{{ detail.currentVersion.title }}</el-descriptions-item>
              <el-descriptions-item label="作者">{{ detail.currentVersion.authorId }}</el-descriptions-item>
              <el-descriptions-item label="审核人">{{ detail.currentVersion.reviewerId || '—' }}</el-descriptions-item>
              <el-descriptions-item label="发布时间">{{ formatTime(detail.currentVersion.publishedAt) || '—' }}</el-descriptions-item>
              <el-descriptions-item label="变更说明">{{ detail.currentVersion.changeNote || '—' }}</el-descriptions-item>
              <el-descriptions-item v-if="detail.currentVersion.platformReviewerId" label="平台复核人">
                {{ detail.currentVersion.platformReviewerId }}
              </el-descriptions-item>
              <el-descriptions-item v-if="detail.currentVersion.platformReviewDecision" label="复核结论">
                {{ detail.currentVersion.platformReviewDecision }}
              </el-descriptions-item>
            </el-descriptions>
          </template>

          <h3 class="section-heading">流转记录</h3>
          <el-empty
            v-if="!detail.transitions || detail.transitions.length === 0"
            description="暂无流转记录"
            :image-size="60"
          />
          <el-timeline v-else>
            <el-timeline-item
              v-for="t in detail.transitions"
              :key="t.transitionId"
              :timestamp="formatTime(t.occurredAt)"
              :type="statusTagType(t.toStatus)"
              placement="top"
            >
              <div class="transition-title">
                <el-tag size="small" effect="plain">{{ eventLabel(t.eventCode) }}</el-tag>
                <span class="transition-flow">{{ statusLabel(t.fromStatus) }} → {{ statusLabel(t.toStatus) }}</span>
              </div>
              <div class="transition-meta">操作人：{{ t.operatorId }}（{{ roleLabel(t.operatorRole) }}）</div>
              <div v-if="t.reason" class="transition-reason">原因：{{ t.reason }}</div>
            </el-timeline-item>
          </el-timeline>
        </template>
      </div>

      <template #footer>
        <div v-if="detail && detail.article" class="drawer-actions">
          <el-alert
            v-if="detail.article.status === 'OFFLINE'"
            type="info"
            :closable="false"
            title="已下线文章需发布新版本后才能重新使用。"
            class="mb-12"
          />
          <el-button
            v-if="canSubmitReview"
            type="primary"
            :loading="actionLoading"
            @click="doSubmit"
          >提交审核</el-button>
          <el-button
            v-if="canManageKnowledge && detail.article.status === 'PENDING_REVIEW'"
            type="success"
            :loading="actionLoading"
            :disabled="!canPublish"
            aria-describedby="knowledge-review-hint"
            @click="doPublish"
          >{{ publishLabel }}</el-button>
          <el-button
            v-if="canReject"
            type="danger"
            plain
            :loading="actionLoading"
            @click="doReject"
          >驳回</el-button>
          <el-button
            v-if="canManagePublished"
            type="danger"
            :loading="actionLoading"
            @click="doOffline"
          >下线</el-button>
          <el-button
            v-if="canManagePublished"
            type="warning"
            plain
            :loading="actionLoading"
            @click="doReindex"
          >修复检索</el-button>
          <div v-if="detail.article.status === 'PENDING_REVIEW'" id="knowledge-review-hint" class="self-review-hint" role="status">
            {{ reviewHint }}
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UploadFilled,
  Cpu,
  Clock,
  Connection,
  Check,
  Search,
  Notebook
} from '@element-plus/icons-vue'
import { ragApi, categoryApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ---- 响应式状态定义 ----
/** 当前选中的待上传文件对象 */
const selectedFile = ref(null)
/** 文档上传与切片处理中 Loading 状态 */
const isProcessing = ref(false)
/** ES 索引初始化中 Loading 状态 */
const isInitEs = ref(false)
/** 当前展示的全链路追踪报告实体 */
const currentTrace = ref(null)
/** 历史追踪记录列表 */
const historyTraces = ref([])
/** 切片手风琴展开的切片 ID 集合 */
const activeChunkNames = ref([])
/** 切片内容搜索过滤关键词 */
const chunkSearchKeyword = ref('')

// ---- 生命周期管理状态 ----
/** 当前页签：ingest 上传工作台 / lifecycle 生命周期管理 */
const activeTab = ref('lifecycle')
/** 知识列表查询条件 */
const listQuery = ref({ status: '', page: 1, pageSize: 10 })
/** 知识文章列表 */
const articles = ref([])
/** 文章总数（分页） */
const articleTotal = ref(0)
/** 列表加载中 */
const listLoading = ref(false)
/** 详情抽屉可见性 */
const drawerVisible = ref(false)
/** 详情加载中 */
const detailLoading = ref(false)
/** 生命周期动作执行中 */
const actionLoading = ref(false)
/** 当前详情（文章 + 当前版本 + 流转审计） */
const detail = ref(null)
const canManageKnowledge = computed(() => !!userStore.currentUser?.user_id &&
  ['KNOWLEDGE_ADMIN', 'PLATFORM_ADMIN'].includes(userStore.currentUser.role))
const isPlatformAdmin = computed(() => userStore.currentUser?.role === 'PLATFORM_ADMIN')
const isHighRisk = computed(() => detail.value?.article?.riskLevel === 'HIGH')
const isCurrentAuthor = computed(() => !!userStore.currentUser?.user_id &&
  detail.value?.currentVersion?.authorId === userStore.currentUser.user_id)
const canSubmitReview = computed(() => detail.value?.article?.status === 'DRAFT' &&
  !!userStore.currentUser?.user_id && ['KNOWLEDGE_ADMIN', 'PLATFORM_ADMIN', 'ENGINEER'].includes(userStore.currentUser.role))
const canReject = computed(() => canManageKnowledge.value && detail.value?.article?.status === 'PENDING_REVIEW')
const canManagePublished = computed(() => canManageKnowledge.value && detail.value?.article?.status === 'PUBLISHED')
const publishBlockedReason = computed(() => {
  if (!canManageKnowledge.value) return '需要知识库管理员或平台管理员权限。'
  if (detail.value?.article?.status !== 'PENDING_REVIEW') return '仅待审核文章可以发布。'
  if (!detail.value.currentVersion) return '当前版本信息不完整，请刷新详情后重试。'
  if (isCurrentAuthor.value) return isHighRisk.value
    ? '你是当前版本的作者，不能自审。请由其他平台管理员复核发布。'
    : '你是当前版本的作者，不能自审。请由其他管理员审核发布。'
  if (isHighRisk.value && !isPlatformAdmin.value) return '高风险文章须由平台管理员复核发布，请移交平台管理员处理。'
  return ''
})
const canPublish = computed(() => !publishBlockedReason.value)
const publishLabel = computed(() => {
  if (isCurrentAuthor.value) return '不可自审'
  if (isHighRisk.value) return isPlatformAdmin.value ? '平台复核并发布' : '等待平台管理员复核'
  return '审核发布'
})
const reviewHint = computed(() => publishBlockedReason.value || (isHighRisk.value
  ? '请核对高风险内容，确认后以平台管理员身份复核发布。'
  : '作者不能发布自己编写的当前版本。'))
const listError = ref('')
const detailError = ref('')
const historyError = ref('')
const historyLoading = ref(false)
const uploadError = ref('')
const articleSearch = ref('')
const selectedArticleId = ref('')
const categories = ref([])
const categoryLoading = ref(false)
const categoryError = ref('')
let categoryRequest = 0
let listRequest = 0
let detailRequest = 0
let historyRequest = 0
let detailPromise = Promise.resolve()
let disposed = false
const filteredArticles = computed(() => {
  const keyword = articleSearch.value.trim().toLocaleLowerCase()
  return articles.value.filter(article => !keyword || [article.articleId, article.title, article.categoryId, article.currentVersionId]
    .some(value => String(value || '').toLocaleLowerCase().includes(keyword)))
})

/** 上传表单及切片策略配置 */
const uploadForm = ref({
  title: '',           // 自定义文档标题（留空自动解析）
  categoryId: '',     // 由当前有效的叶子分类选择，不预设历史分类 ID
  publishNow: false,   // 默认存为草稿；直接发布跳过审核，仅供快速验证
  chunkSize: 500,      // 目标切片大小（字符）
  chunkOverlap: 50     // 切片重叠大小（字符）
})

/**
 * 手动触发初始化/重建 ES 知识库索引
 */
async function handleInitEsIndex() {
  if (isInitEs.value) return
  isInitEs.value = true
  try {
    const res = await ragApi.initIndex(false)
    if (res?.data?.success) {
      ElMessage.success(res.data.message || 'ES 索引初始化成功')
    } else {
      ElMessage.warning(res?.data?.message || 'ES 初始化返回异常')
    }
  } catch (e) {
    ElMessage.error('初始化 ES 索引失败: ' + (e.message || '网络错误'))
  } finally {
    isInitEs.value = false
  }
}

// 页面加载时自动拉取最近执行的历史链路与知识列表
onMounted(() => {
  fetchRecentTraces()
  fetchArticles(1)
})

/** 文件选择回调 */
function handleFileChange(file) {
  selectedFile.value = file.raw
}

/** 文件移除回调 */
function handleFileRemove() {
  selectedFile.value = null
}

async function fetchCategories() {
  const request = ++categoryRequest
  categoryLoading.value = true
  categoryError.value = ''
  categories.value = []
  try {
    const res = await categoryApi.leaf()
    if (request !== categoryRequest) return
    if (!Array.isArray(res?.data) || res.data.some(category => !category.category_id || !category.name || !category.status)) {
      throw new Error('分类数据异常，请重试')
    }
    categories.value = res.data.filter(category => category.status === 'ACTIVE')
    if (!categories.value.some(category => category.category_id === uploadForm.value.categoryId)) uploadForm.value.categoryId = ''
  } catch (e) {
    if (request === categoryRequest) {
      categoryError.value = e.message || '分类加载失败'
      uploadForm.value.categoryId = ''
    }
  } finally {
    if (request === categoryRequest) categoryLoading.value = false
  }
}
watch(activeTab, tab => { if (tab === 'ingest') fetchCategories() })

/**
 * 提交文档上传并触发切片与 ES 入库全流程
 */
async function submitUploadAndProcess() {
  if (isProcessing.value) return
  uploadError.value = ''
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要上传的文档')
    return
  }
  if (categoryLoading.value || categoryError.value || !categories.value.some(category => category.category_id === uploadForm.value.categoryId)) {
    ElMessage.warning('请选择当前可用的知识分类')
    return
  }

  isProcessing.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (uploadForm.value.title) formData.append('title', uploadForm.value.title)
  if (uploadForm.value.categoryId) formData.append('categoryId', uploadForm.value.categoryId)
  formData.append('publishNow', uploadForm.value.publishNow)
  formData.append('chunkSize', uploadForm.value.chunkSize)
  formData.append('chunkOverlap', uploadForm.value.chunkOverlap)

  try {
    const res = await ragApi.uploadDocument(formData)
    if (disposed) return
    if (!res?.data?.trace) throw new Error('文档处理结果异常，请查看处理记录后重试')
    if (res.data) {
      loadTrace(res.data.trace)
      if (res.data.trace.status === 'FAILED') throw new Error(res.data.message || '文档处理失败，请查看处理明细')
      if (res.data.trace.status !== 'SUCCESS') {
        ElMessage.warning(res.data.message || '文档处理尚未完成，请查看处理记录')
      } else if (res.data.article?.status === 'DRAFT') {
        ElMessage.success('已存为草稿，可在知识文章中提交审核')
      } else {
        ElMessage.success('文档处理完成')
      }
      fetchRecentTraces()
      fetchArticles(1)
      if (res.data.trace?.chunks?.length > 0) {
        activeChunkNames.value = [res.data.trace.chunks[0].chunkId]
      }
    }
  } catch (err) {
    if (!disposed) {
      uploadError.value = err.message || '文档处理失败'
      fetchRecentTraces()
    }
  } finally {
    isProcessing.value = false
  }
}

async function fetchRecentTraces() {
  const request = ++historyRequest
  historyLoading.value = true
  historyError.value = ''
  try {
    const res = await ragApi.listTraces()
    if (request !== historyRequest) return
    if (!Array.isArray(res?.data)) throw new Error('处理记录数据异常')
    historyTraces.value = res.data
    if (!currentTrace.value && res.data.length) loadTrace(res.data[0])
  } catch (e) {
    if (request === historyRequest) historyError.value = e.message || '处理记录加载失败'
  } finally {
    if (request === historyRequest) historyLoading.value = false
  }
}
function loadTrace(trace) {
  currentTrace.value = trace
  activeChunkNames.value = trace.chunks?.length ? [trace.chunks[0].chunkId] : []
  chunkSearchKeyword.value = ''
}
function traceStatusLabel(status) {
  return { SUCCESS: '处理完成', WARNING: '需要关注', FAILED: '处理失败', RUNNING: '处理中', PENDING: '等待处理', SKIPPED: '已跳过' }[status] || status || '状态未确认'
}

// ================= 知识生命周期管理 =================

function statusLabel(s) {
  const map = { DRAFT: '草稿', PENDING_REVIEW: '待审核', PUBLISHED: '已发布', OFFLINE: '已下线' }
  return map[s] || s
}

function statusTagType(s) {
  if (s === 'PUBLISHED') return 'success'
  if (s === 'PENDING_REVIEW') return 'warning'
  if (s === 'OFFLINE') return 'danger'
  return 'info'
}

function eventLabel(code) {
  const map = {
    KNOWLEDGE_SUBMIT_REVIEW: '提交审核',
    KNOWLEDGE_PUBLISH: '审核发布',
    KNOWLEDGE_REJECT: '驳回',
    KNOWLEDGE_OFFLINE: '下线'
  }
  return map[code] || code
}

function roleLabel(role) {
  return { PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员', ENGINEER: '工程师', EMPLOYEE: '员工', SYSTEM: '系统' }[role] || role
}

async function fetchArticles(page) {
  if (page) listQuery.value.page = page
  const request = ++listRequest
  listLoading.value = true
  listError.value = ''
  articles.value = []
  articleTotal.value = 0
  try {
    const res = await ragApi.listArticles({
      status: listQuery.value.status || undefined,
      page: listQuery.value.page, pageSize: listQuery.value.pageSize
    })
    if (request !== listRequest) return
    if (!Array.isArray(res?.data?.records) || !Number.isFinite(res.data.total)) throw new Error('知识列表数据异常')
    articles.value = res.data.records
    articleTotal.value = res.data.total
  } catch (e) {
    if (request === listRequest) listError.value = e.message || '加载知识列表失败'
  } finally {
    if (request === listRequest) listLoading.value = false
  }
}
async function openDetail(id) {
  if (!id || disposed) return
  if (selectedArticleId.value !== id) {
    ++detailRequest
    detail.value = null
    detailError.value = ''
    detailLoading.value = true
    drawerVisible.value = true
  }
  const navigate = route.query.article ? router.replace : router.push
  await navigate({ query: { ...route.query, article: id } })
  if (!disposed && route.query.article === id) return detailPromise
}
async function loadDetail(id) {
  if (!id || disposed) return
  const request = ++detailRequest
  selectedArticleId.value = id
  activeTab.value = 'lifecycle'
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  detailError.value = ''
  try {
    const res = await ragApi.getArticle(id)
    if (request !== detailRequest) return
    if (!res?.data?.article) throw new Error('知识详情数据异常')
    detail.value = res.data
  } catch (e) {
    if (request === detailRequest) detailError.value = e.message || '加载知识详情失败'
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}
function resetDetail() {
  ++detailRequest
  selectedArticleId.value = ''
  drawerVisible.value = false
  detailLoading.value = false
  detail.value = null
  detailError.value = ''
}
async function closeDetail() {
  resetDetail()
  const query = { ...route.query }
  delete query.article
  await router.replace({ query })
}
async function refreshAfterAction(id) {
  if (disposed) return
  await fetchArticles()
  if (!disposed && drawerVisible.value && selectedArticleId.value === id) await loadDetail(id)
}
watch(() => route.query.article, id => {
  if (typeof id === 'string' && id) detailPromise = loadDetail(id)
  else resetDetail()
}, { immediate: true, flush: 'sync' })
onUnmounted(() => {
  disposed = true
  ++listRequest
  ++historyRequest
  ++categoryRequest
  resetDetail()
})

/** 提交审核：DRAFT ➔ PENDING_REVIEW */
async function doSubmit() {
  if (actionLoading.value || !canSubmitReview.value) return
  const id = detail.value.article.articleId
  actionLoading.value = true
  try {
    const res = await ragApi.submitArticle(id, { remark: '工作台提交审核' })
    if (res?.data) ElMessage.success(res.data.message || '已提交审核')
    await refreshAfterAction(id)
  } catch (e) {
    ElMessage.error(e.message || '提审失败')
  } finally {
    actionLoading.value = false
  }
}

/** 审核通过并发布：PENDING_REVIEW ➔ PUBLISHED，联动 ES 入库 */
async function doPublish() {
  if (actionLoading.value || !detail.value?.article) return
  if (!canPublish.value) {
    ElMessage.warning(publishBlockedReason.value)
    return
  }
  const id = detail.value.article.articleId
  const versionId = detail.value.currentVersion.versionId
  const operatorId = userStore.currentUser.user_id
  actionLoading.value = true
  let note = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入发布变更说明（可选）', '审核通过并发布', {
      confirmButtonText: '发布',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：内容已核对，可以发布',
      closeOnClickModal: false
    })
    note = value || ''
  } catch {
    actionLoading.value = false
    return
  }
  if (disposed || !canPublish.value || detail.value?.article?.articleId !== id ||
      detail.value?.currentVersion?.versionId !== versionId || userStore.currentUser?.user_id !== operatorId) {
    actionLoading.value = false
    if (!disposed) ElMessage.warning(publishBlockedReason.value || '文章或登录身份已变化，请重新确认。')
    return
  }
  try {
    const res = await ragApi.publishArticle(id, { changeNote: note })
    if (res?.data) {
      if (res.data.indexStatus !== 'INDEXED') {
        ElMessage.warning(res.data.message || '已发布，但检索更新未完成，请稍后使用「修复检索」重试')
      } else {
        ElMessage.success(res.data.message || '发布成功，文章已可检索')
      }
    }
    await refreshAfterAction(id)
  } catch (e) {
    // 作者自审 / 高风险非平台管理员复核会由服务端 403 拦截，这里原样提示
    ElMessage.error(e.message || '发布失败')
  } finally {
    actionLoading.value = false
  }
}

/** 驳回：PENDING_REVIEW ➔ DRAFT（原因必填，写入版本驳回记录） */
async function doReject() {
  if (actionLoading.value || !canReject.value) return
  const id = detail.value.article.articleId
  actionLoading.value = true
  let reason = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因（必填，写入版本驳回记录）', '驳回', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '必填',
      inputValidator: (v) => (v && v.trim().length > 0) || '驳回原因必填',
      closeOnClickModal: false
    })
    reason = value
  } catch {
    actionLoading.value = false
    return
  }
  if (disposed) { actionLoading.value = false; return }
  try {
    const res = await ragApi.rejectArticle(id, { reason })
    if (res?.data) ElMessage.success(res.data.message || '已驳回并退回草稿')
    await refreshAfterAction(id)
  } catch (e) {
    ElMessage.error(e.message || '驳回失败')
  } finally {
    actionLoading.value = false
  }
}

/** 下线：PUBLISHED ➔ OFFLINE，同步 ES 状态（AC-27：搜索与 RAG 不再返回） */
async function doOffline() {
  if (actionLoading.value || !canManagePublished.value) return
  const id = detail.value.article.articleId
  actionLoading.value = true
  let reason = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入下线原因。下线后，文章不再用于搜索和客服回答。', '下线知识', {
      confirmButtonText: '确认下线',
      cancelButtonText: '取消',
      inputPlaceholder: '必填',
      inputValidator: (v) => (v && v.trim().length > 0) || '下线原因必填',
      closeOnClickModal: false
    })
    reason = value
  } catch {
    actionLoading.value = false
    return
  }
  if (disposed) { actionLoading.value = false; return }
  try {
    const res = await ragApi.offlineArticle(id, { reason })
    if (res?.data) ElMessage.success(res.data.message || '已下线')
    await refreshAfterAction(id)
  } catch (e) {
    ElMessage.error(e.message || '下线失败')
  } finally {
    actionLoading.value = false
  }
}

/** 重建 RAG 索引（发布后索引失败等场景的补偿入口，RD-008） */
async function doReindex() {
  if (actionLoading.value || !canManagePublished.value) return
  const id = detail.value.article.articleId
  actionLoading.value = true
  try {
    const res = await ragApi.reindexArticle(id)
    if (res?.data) {
      if (res.data.indexStatus === 'INDEXED') {
        ElMessage.success(res.data.message || '检索修复完成')
      } else {
        ElMessage.warning(res.data.message || '检索修复未完成')
      }
    }
    await refreshAfterAction(id)
  } catch (e) {
    ElMessage.error(e.message || '检索修复失败')
  } finally {
    actionLoading.value = false
  }
}

const filteredChunks = computed(() => {
  if (!currentTrace.value?.chunks) return []
  const kw = chunkSearchKeyword.value.trim().toLowerCase()
  if (!kw) return currentTrace.value.chunks
  return currentTrace.value.chunks.filter(c =>
    (c.title && c.title.toLowerCase().includes(kw)) ||
    (c.content && c.content.toLowerCase().includes(kw))
  )
})

function getStageTagType(status) {
  if (status === 'SUCCESS') return 'success'
  if (status === 'WARNING') return 'warning'
  if (status === 'FAILED') return 'danger'
  return 'info'
}

function formatMetricKey(key) {
  const map = {
    fileName: '原始文件名',
    fileExtension: '格式后缀',
    fileSizeBytes: '文件大小(字节)',
    extractedTitle: '提取标题',
    lineCount: '总行数',
    charCount: '总字符数',
    chunkCount: '切片总数',
    targetChunkSize: '目标切片长度',
    chunkOverlap: '重叠字符',
    totalTokensEstimate: '预估 Tokens',
    avgChunkLength: '平均切片长度',
    embeddingModel: '向量模型',
    dimensions: '向量维度',
    totalTokensUsed: '消耗 Tokens',
    batchCount: '批处理次数',
    vectorCount: '生成向量数',
    embeddingDurationMs: '向量化耗时(ms)',
    targetIndex: 'ES 目标索引',
    indexedChunks: '已入库切片数',
    esEndpoint: 'ES 服务节点',
    esStatus: 'ES 状态'
  }
  return map[key] || key
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  return isoStr.replace('T', ' ').substring(5, 19)
}

function copyText(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  }
}


</script>

<style scoped>
.kb-admin-container { min-width: 0; color: var(--ws-ink); }
.page-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }
.page-head h1 { margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -.6px; }
.page-head p { margin: 8px 0 0; color: var(--ws-muted); font-size: 13px; }
.kb-main-body { min-width: 0; }
.kb-tabs :deep(.el-tabs__item) { font-size: 13px; }
.box-card { border: 0; border-radius: 0; background: transparent; }
.box-card :deep(.el-card__header) { padding: 18px 0; }
.box-card :deep(.el-card__body) { padding: 18px 0; }
.card-header-title, .card-header-flex, .list-toolbar, .chunks-header { display: flex; align-items: center; gap: 10px; }
.card-header-title { font-size: 14px; font-weight: 600; }
.card-header-flex, .chunks-header { justify-content: space-between; flex-wrap: wrap; }
.list-toolbar { flex-wrap: wrap; }
.article-search { width: 200px; }
.pager-row { display: flex; justify-content: flex-end; margin-top: 18px; }
.error-state { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 16px 0; color: var(--el-color-danger); font-size: 13px; }
.category-state { color: var(--ws-muted); font-size: 13px; }
.kb-uploader, .submit-btn { width: 100%; }
.advanced-params { margin: 16px 0; }
.upload-action-bar { margin-top: 18px; }
.quick-warn { font-size: 12px; color: var(--el-color-warning); margin-top: 6px; }
.history-list { display: flex; flex-direction: column; max-height: 340px; overflow-y: auto; }
.history-item { display: block; width: 100%; font: inherit; text-align: left; padding: 14px 12px; border: 0; border-bottom: 1px solid var(--ws-line); background: transparent; color: var(--ws-ink); cursor: pointer; }
.history-item:hover, .history-item.active { background: var(--ws-accent-soft); }
.history-item:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: -2px; }
.history-item-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.history-name { font-size: 13px; overflow-wrap: anywhere; }
.history-item-meta { display: flex; flex-wrap: wrap; gap: 12px; color: var(--ws-muted); font-size: 11px; margin-top: 8px; }
.empty-hint { text-align: center; padding: 28px 0; font-size: 13px; color: var(--ws-muted); }
.trace-id-badge { font-size: 11px; color: var(--ws-muted); overflow-wrap: anywhere; }
.trace-summary-banner { display: flex; flex-wrap: wrap; gap: 16px 24px; padding: 0 0 20px; border-bottom: 1px solid var(--ws-line); }
.summary-metric { display: flex; flex-direction: column; gap: 8px; }
.summary-metric .label { color: var(--ws-muted); font-size: 12px; }
.summary-metric .value { font-size: 14px; font-weight: 500; overflow-wrap: anywhere; }
.doc-title { max-width: 240px; }
.advanced-trace summary { cursor: pointer; padding: 18px 0; color: var(--ws-muted); font-size: 13px; }
.section-heading { font-size: 13px; margin: 12px 0; }
.stage-inner-card { background: var(--el-fill-color-light); }
.stage-title-row { display: flex; justify-content: space-between; gap: 10px; }
.stage-name { font-weight: 600; font-size: 13px; }
.stage-desc, .stage-msg { font-size: 12px; color: var(--ws-muted); margin: 10px 0; }
.stage-msg.failed { color: var(--el-color-danger); }
.stage-msg.warning { color: var(--el-color-warning); }
.stage-msg.success { color: var(--el-color-success); }
.stage-metrics-grid, .chunk-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-chip { font-size: 11px; border: 1px solid var(--ws-line); border-radius: 4px; padding: 3px 6px; }
.m-key { color: var(--ws-muted); margin-right: 4px; }
.chunk-collapse-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; line-height: 1.5; padding: 8px 0; }
.chunk-section-title { font-size: 13px; overflow-wrap: anywhere; }
.chunk-index { color: var(--el-color-primary); font-size: 11px; }
.chunk-meta-bar { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; color: var(--ws-muted); font-size: 11px; margin-bottom: 10px; }
.chunk-content-view { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--el-fill-color-light); color: var(--ws-ink); padding: 14px; border: 1px solid var(--ws-line); border-radius: 6px; font-size: 13px; line-height: 1.7; }
.mt-16 { margin-top: 16px; }.mb-12 { margin-bottom: 12px; }
.drawer-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.self-review-hint { width: 100%; color: var(--ws-muted); font-size: 12px; line-height: 1.6; }
.transition-title { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.transition-flow { font-size: 13px; }.transition-meta, .transition-reason { font-size: 12px; color: var(--ws-muted); }
.transition-reason { background: var(--el-fill-color-light); padding: 8px; margin-top: 6px; }
@media (max-width: 640px) { .page-head h1 { font-size: 21px; }.page-head { align-items: flex-start; }.article-search { width: 100%; }.trace-summary-banner { gap: 16px; }.list-toolbar :deep(.el-radio-group) { flex-wrap: wrap; gap: 4px 0; } }
</style>
