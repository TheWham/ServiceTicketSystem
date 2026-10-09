<template>
  <div class="kb-admin-container">
    <header class="kb-header">
      <div class="header-left"><div class="logo-icon"><el-icon aria-hidden="true"><Notebook /></el-icon></div>
        <div class="header-titles"><span class="page-eyebrow">KNOWLEDGE WORKSPACE</span><h1 class="main-title">{{ activeTab === 'lifecycle' ? '知识管理' : '文档导入' }}</h1><p class="sub-title">{{ activeTab === 'lifecycle' ? '审核知识内容，管理发布与下线，让解答保持准确' : '导入服务文档，检查处理结果，再提交知识审核' }}</p></div>
      </div>
      <el-button v-if="activeTab === 'ingest'" :icon="Connection" :loading="isInitEs" @click="handleInitEsIndex">初始化检索索引</el-button>
    </header>

    <main class="kb-main-body">
      <el-tabs v-model="activeTab" class="kb-tabs">
      <el-tab-pane label="文档导入" name="ingest">
      <el-row :gutter="20">
        <!-- 左侧：文档上传与参数配置 -->
        <el-col :xs="24" :lg="9">
          <el-card shadow="hover" class="box-card upload-card">
            <template #header>
              <div class="card-header-title">
                <el-icon><UploadFilled /></el-icon>
                <span>导入知识文档</span>
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

              <el-form-item label="文档自定义标题 (选填)">
                <el-input
                  v-model="uploadForm.title"
                  placeholder="留空则自动从 Markdown 一级标题或文件名提取"
                  clearable
                />
              </el-form-item>

              <el-form-item label="所属知识分类">
                <el-select v-model="uploadForm.categoryId" placeholder="请选择分类" style="width: 100%">
                  <el-option label="网络与连接 (C_NET)" value="C_NET" />
                  <el-option label="软件与系统 (C_SW)" value="C_SW" />
                  <el-option label="硬件与外设 (C_HW)" value="C_HW" />
                  <el-option label="账号与权限 (C_ACC)" value="C_ACC" />
                  <el-option label="其他分类 (C_OTH)" value="C_OTH" />
                </el-select>
              </el-form-item>

              <el-form-item label="入库方式">
                <el-radio-group v-model="uploadForm.publishNow">
                  <el-radio :value="false">存为草稿（标准流程：提审 → 发布）</el-radio>
                  <el-radio :value="true">直接发布（快速通道，跳过审核）</el-radio>
                </el-radio-group>
                <div v-if="uploadForm.publishNow" class="quick-warn">
                  直接发布跳过审核并立即进入 RAG 检索，仅建议管理端测试使用（规范 SM-KNOWLEDGE-001 要求审核后发布）
                </div>
              </el-form-item>

              <el-collapse class="advanced-params">
                <el-collapse-item title="高级处理参数">
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

              <el-alert v-if="uploadError" :title="uploadError" type="error" show-icon :closable="false" class="page-error" />
              <div class="upload-action-bar">
                <el-button
                  type="primary"
                  size="large"
                  :loading="isProcessing"
                  :disabled="!selectedFile"
                  class="submit-btn"
                  @click="submitUploadAndProcess"
                >
                  <el-icon v-if="!isProcessing"><Cpu /></el-icon>
                  {{ isProcessing ? '文档处理中...' : '开始处理文档' }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <!-- 历史处理记录列表 -->
          <el-card shadow="hover" class="box-card history-card" style="margin-top: 16px;">
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
            <el-alert v-if="historyError" :title="historyError" type="error" :closable="false"><el-button link type="primary" @click="fetchRecentTraces">重试</el-button></el-alert>
            <div v-if="historyLoading" class="empty-hint" role="status">正在加载处理记录…</div>
            <div v-else-if="!historyError && historyTraces.length === 0" class="empty-hint">
              暂无历史链路记录，请上传文档执行
            </div>
            <div v-else-if="!historyError" class="history-list">
              <div
                v-for="item in historyTraces"
                :key="item.traceId"
                class="history-item"
                role="button"
                tabindex="0"
                @keydown.enter="loadTrace(item)"
                @keydown.space.prevent="loadTrace(item)"
                :class="{ active: currentTrace?.traceId === item.traceId }"
                @click="loadTrace(item)"
              >
                <div class="history-item-top">
                  <span class="history-name">{{ item.documentName }}</span>
                  <el-tag :type="item.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
                    {{ item.status }}
                  </el-tag>
                </div>
                <div class="history-item-meta">
                  <span>{{ item.chunks?.length || 0 }} 个切片</span>
                  <span>耗时 {{ item.totalDurationMs }}ms</span>
                  <span>{{ formatTime(item.startTime) }}</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：链路过程与切片明细 -->
        <el-col :xs="24" :lg="15">
          <!-- 链路总览卡片 -->
          <el-card shadow="hover" class="box-card trace-card">
            <template #header>
              <div class="card-header-flex">
                <div class="card-header-title">
                  <el-icon><Connection /></el-icon>
                  <span>文档处理结果</span>
                </div>
                <span v-if="currentTrace" class="trace-id-badge">
                  TraceID: <code>{{ currentTrace.traceId }}</code>
                </span>
              </div>
            </template>

            <div v-if="!currentTrace" class="empty-trace-container">
              <el-empty description="请在左侧上传文档，或选择历史记录查看全链路处理过程" />
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
                  <span class="label">全链路总耗时</span>
                  <span class="value">{{ currentTrace.totalDurationMs }} ms</span>
                </div>
                <div class="summary-metric">
                  <span class="label">知识库状态</span>
                  <el-tag :type="getStageTagType(currentTrace.status)" effect="plain">{{ currentTrace.status === 'SUCCESS' ? '处理完成' : currentTrace.status === 'FAILED' ? '处理失败' : '请查看处理步骤' }}</el-tag>
                </div>
              </div>

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
                          {{ stage.status }}
                        </el-tag>
                      </div>
                      <p class="stage-desc">{{ stage.description }}</p>
                      <div class="stage-msg">
                        <el-icon><Check /></el-icon>
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
                  <h3 class="section-heading">内容切片预览</h3>
                  <el-input
                    v-model="chunkSearchKeyword"
                    placeholder="搜索切片文本或标题..."
                    :prefix-icon="Search"
                    aria-label="搜索切片文本或标题"
                    size="small"
                    clearable
                    style="width: 240px"
                  />
                </div>

                <div class="chunk-list-container">
                  <el-collapse v-model="activeChunkNames" accordion>
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
                              {{ chunk.vectorDimensions ? `${chunk.vectorDimensions} 维向量` : '向量已生成' }}
                            </el-tag>
                            <el-tag size="small" type="success">ES: {{ chunk.esDocId || '未返回索引编号' }}</el-tag>
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
            </div>
          </el-card>
        </el-col>
      </el-row>
      </el-tab-pane>

      <el-tab-pane label="知识管理" name="lifecycle">
        <el-card shadow="hover" class="box-card">
          <template #header>
            <div class="card-header-flex">
              <div class="card-header-title">
                <el-icon><Notebook /></el-icon>
                <span>知识文章列表</span>
              </div>
              <div class="list-toolbar">
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

          <p class="scope-note">符合筛选的知识共 {{ articleTotal }} 篇，当前页已加载 {{ articles.length }} 篇。</p>
          <el-alert v-if="listError" :title="listError" type="error" :closable="false" show-icon class="page-error"><el-button link type="primary" @click="fetchArticles()">重新加载</el-button></el-alert>
          <el-table
            :data="articles"
            v-loading="listLoading"
            border
            stripe
            :empty-text="listError ? '知识列表加载失败，请重试' : '暂无知识文章，可先在文档导入页存为草稿'"
          >
            <el-table-column prop="title" label="文章标题" min-width="320">
              <template #default="{ row }">
                <div class="knowledge-title">{{ row.title || '（未命名知识）' }}</div>
                <div class="knowledge-article-id" :title="row.articleId">ID：{{ row.articleId }}</div>
              </template>
            </el-table-column>
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
                <el-button link type="primary" size="small" @click="openDetail(row.articleId)">
                  详情 / 操作
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager-row">
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
      </el-tabs>
    </main>

    <!-- 知识详情与生命周期操作抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`知识详情 · ${detail?.article?.articleId || ''}`"
      size="min(600px, 100vw)"
      :destroy-on-close="true"
    >
      <div v-loading="detailLoading" class="drawer-body">
        <el-alert v-if="detailError" :title="detailError" type="error" :closable="false" show-icon />
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
            <el-descriptions-item label="乐观锁版本">{{ detail.article.version }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(detail.article.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatTime(detail.article.updatedAt) }}</el-descriptions-item>
          </el-descriptions>

          <template v-if="detail.currentVersion">
            <el-descriptions title="当前版本" :column="2" border size="small" class="mt-16">
              <el-descriptions-item label="版本ID" :span="2">{{ detail.currentVersion.versionId }}</el-descriptions-item>
              <el-descriptions-item label="版本号">v{{ detail.currentVersion.versionNo }}</el-descriptions-item>
              <el-descriptions-item label="标题" :span="2">{{ versionContent.title || '—' }}</el-descriptions-item>
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

          <template v-if="detail.currentVersion">
            <h3 class="section-heading">知识内容（审核对象）</h3>
            <div class="knowledge-content">
              <template v-if="versionContent.summary">
                <span class="content-label">摘要</span>
                <p class="content-summary">{{ versionContent.summary }}</p>
              </template>
              <template v-if="versionContent.keywords">
                <span class="content-label">关键词</span>
                <div class="content-keywords">
                  <el-tag
                    v-for="kw in versionContent.keywords.split(/\s+/)"
                    :key="kw"
                    size="small"
                    effect="plain"
                    class="keyword-tag"
                  >{{ kw }}</el-tag>
                </div>
              </template>
              <span class="content-label">正文</span>
              <pre class="content-body">{{ versionContent.body || '（无正文内容）' }}</pre>
            </div>
          </template>

          <h3 class="section-heading">流转审计时间线</h3>
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
              <div class="transition-meta">操作人：{{ t.operatorId }}（{{ t.operatorRole }}）</div>
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
            title="已下线知识不可恢复，只能发布新版本（规范 PRD §16.4）"
            class="mb-12"
          />
          <el-button
            v-if="detail.article.status === 'DRAFT'"
            type="primary"
            :loading="actionLoading"
            @click="doSubmit"
          ><el-icon><UploadFilled /></el-icon> 提交审核</el-button>
          <el-button
            v-if="detail.article.status === 'PENDING_REVIEW'"
            type="success"
            :loading="actionLoading"
            @click="doPublish"
          ><el-icon><Check /></el-icon> 审核通过并发布</el-button>
          <el-button
            v-if="detail.article.status === 'PENDING_REVIEW'"
            type="danger"
            plain
            :loading="actionLoading"
            @click="doReject"
          >驳回</el-button>
          <el-button
            v-if="detail.article.status === 'PUBLISHED'"
            type="danger"
            :loading="actionLoading"
            @click="doOffline"
          >下线（搜索与 RAG 不再返回）</el-button>
          <el-button
            v-if="detail.article.status === 'PUBLISHED'"
            type="warning"
            plain
            :loading="actionLoading"
            @click="doReindex"
          >重建检索索引</el-button>
          <div v-if="detail.article.status === 'PENDING_REVIEW'" class="self-review-hint">
            作者不得审核自己提交的内容（AC-25）；高风险知识须平台管理员复核
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
/**
 * ============================================================================
 * 知识库管理工作台组件 (KnowledgeAdminView.vue)
 * ============================================================================
 *
 * 【业务定位与界面设计】：
 * 1. 提供 RAG 知识库管理员专用的文档摄入（Ingestion）操作台。
 * 2. 具备 Markdown/TXT 拖拽上传、切片滑动窗口参数实时微调能力。
 * 3. 实时可观测性（Observability）：以时间线（Timeline）展示文档解析、切片、ES 写入各环节耗时与指标。
 * 4. 切片预览与检索：展示每一个 Chunk 的字符数、Token 估算、所属章节与 ES Document ID。
 *
 * @author IT工单系统前端研发组 - RAG专项
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
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
import { useUserStore } from '../stores/user.js'
import { ragApi } from '../api/index.js'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ---- 响应式状态定义 ----
/** 当前选中的待上传文件对象 */
const selectedFile = ref(null)
/** 文档上传与切片处理中 Loading 状态 */
const isProcessing = ref(false)
const uploadError = ref('')
/** ES 索引初始化中 Loading 状态 */
const isInitEs = ref(false)
/** 当前展示的全链路追踪报告实体 */
const currentTrace = ref(null)
/** 历史追踪记录列表 */
const historyTraces = ref([])
const historyLoading = ref(false)
const historyError = ref('')
const listError = ref('')
const detailError = ref('')
/** 切片手风琴展开的切片 ID 集合 */
const activeChunkNames = ref([])
/** 切片内容搜索过滤关键词 */
const chunkSearchKeyword = ref('')

// ---- 生命周期管理状态 ----
/** 当前页签：ingest 上传工作台 / lifecycle 生命周期管理 */
const activeTab = computed({
  get: () => route.query.tab === 'lifecycle' ? 'lifecycle' : 'ingest',
  set: tab => router.push({ path: route.path, query: { ...route.query, tab } })
})
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

/** 上传表单及切片策略配置 */
const uploadForm = ref({
  title: '',           // 自定义文档标题（留空自动解析）
  categoryId: 'C_NET', // 默认分类：网络与连接
  publishNow: false,   // 默认存为草稿（标准流程：提审 → 发布）；直接发布跳过审核，仅供快速验证
  chunkSize: 500,      // 目标切片大小（字符）
  chunkOverlap: 50     // 切片重叠大小（字符）
})

/**
 * 手动触发初始化/重建 ES 知识库索引
 */
async function handleInitEsIndex() {
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

/**
 * 提交文档上传并触发切片与 ES 入库全流程
 */
async function submitUploadAndProcess() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要上传的文档')
    return
  }

  isProcessing.value = true
  uploadError.value = ''
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (uploadForm.value.title) formData.append('title', uploadForm.value.title)
  if (uploadForm.value.categoryId) formData.append('categoryId', uploadForm.value.categoryId)
  formData.append('publishNow', uploadForm.value.publishNow)
  formData.append('chunkSize', uploadForm.value.chunkSize)
  formData.append('chunkOverlap', uploadForm.value.chunkOverlap)

  try {
    const res = await ragApi.uploadDocument(formData)
    if (res && res.data) {
      currentTrace.value = res.data.trace
      if (res.data.article?.status === 'DRAFT') {
        ElMessage.success('已存为草稿，请到「知识生命周期管理」页提交审核')
      } else {
        ElMessage.success('文档切片并写入 ES 成功！')
      }
      fetchRecentTraces()
      fetchArticles(1)
      if (res.data.trace?.chunks?.length > 0) {
        activeChunkNames.value = [res.data.trace.chunks[0].chunkId]
      }
    }
  } catch (err) {
    uploadError.value = err.message || '文档处理失败，请重试'
  } finally {
    isProcessing.value = false
  }
}

async function fetchRecentTraces() {
  historyLoading.value = true
  historyError.value = ''
  try {
    const res = await ragApi.listTraces()
    if (res && res.data) {
      historyTraces.value = res.data
      if (!currentTrace.value && res.data.length > 0) {
        currentTrace.value = res.data[0]
      }
    }
  } catch (e) {
    historyError.value = e.message || '处理记录加载失败，请重试'
  } finally {
    historyLoading.value = false
  }
}

function loadTrace(trace) {
  currentTrace.value = trace
  if (trace.chunks?.length > 0) {
    activeChunkNames.value = [trace.chunks[0].chunkId]
  }
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

async function fetchArticles(page) {
  if (page) listQuery.value.page = page
  listLoading.value = true
  listError.value = ''
  try {
    const res = await ragApi.listArticles({
      status: listQuery.value.status || undefined,
      page: listQuery.value.page,
      pageSize: listQuery.value.pageSize
    })
    if (res?.data) {
      articles.value = res.data.records || []
      articleTotal.value = res.data.total || 0
    }
  } catch (e) {
    listError.value = '知识列表加载失败：' + (e.message || '网络错误')
  } finally {
    listLoading.value = false
  }
}

async function openDetail(articleId) {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  detailError.value = ''
  try {
    const res = await ragApi.getArticle(articleId)
    if (res?.data) detail.value = res.data
  } catch (e) {
    detailError.value = '知识详情加载失败：' + (e.message || '网络错误')
  } finally {
    detailLoading.value = false
  }
}

async function refreshAfterAction() {
  await fetchArticles()
  if (detail.value?.article?.articleId) {
    await openDetail(detail.value.article.articleId)
  }
}

/** 提交审核：DRAFT ➔ PENDING_REVIEW */
async function doSubmit() {
  const id = detail.value.article.articleId
  actionLoading.value = true
  try {
    const res = await ragApi.submitArticle(id, { remark: '工作台提交审核' })
    if (res?.data) ElMessage.success(res.data.message || '已提交审核')
    await refreshAfterAction()
  } catch (e) {
    ElMessage.error(e.message || '提审失败')
  } finally {
    actionLoading.value = false
  }
}

/** 审核通过并发布：PENDING_REVIEW ➔ PUBLISHED，联动 ES 入库 */
async function doPublish() {
  const id = detail.value.article.articleId
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
    return
  }
  actionLoading.value = true
  try {
    const res = await ragApi.publishArticle(id, { changeNote: note })
    if (res?.data) {
      if (res.data.indexStatus === 'PENDING_COMPENSATION') {
        ElMessage.warning(res.data.message || '已发布，但 RAG 索引未完成，可稍后「重建索引」补偿')
      } else {
        ElMessage.success(res.data.message || '发布成功，已写入 RAG 索引')
      }
    }
    await refreshAfterAction()
  } catch (e) {
    // 作者自审 / 高风险非平台管理员复核会由服务端 403 拦截，这里原样提示
    ElMessage.error(e.message || '发布失败')
  } finally {
    actionLoading.value = false
  }
}

/** 驳回：PENDING_REVIEW ➔ DRAFT（原因必填，写入版本驳回记录） */
async function doReject() {
  const id = detail.value.article.articleId
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
    return
  }
  actionLoading.value = true
  try {
    const res = await ragApi.rejectArticle(id, { reason })
    if (res?.data) ElMessage.success(res.data.message || '已驳回并退回草稿')
    await refreshAfterAction()
  } catch (e) {
    ElMessage.error(e.message || '驳回失败')
  } finally {
    actionLoading.value = false
  }
}

/** 下线：PUBLISHED ➔ OFFLINE，同步 ES 状态（AC-27：搜索与 RAG 不再返回） */
async function doOffline() {
  const id = detail.value.article.articleId
  let reason = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入下线原因（必填）。下线后搜索与 RAG 索引均不再返回该版本（AC-27）。', '下线知识', {
      confirmButtonText: '确认下线',
      cancelButtonText: '取消',
      inputPlaceholder: '必填',
      inputValidator: (v) => (v && v.trim().length > 0) || '下线原因必填',
      closeOnClickModal: false
    })
    reason = value
  } catch {
    return
  }
  actionLoading.value = true
  try {
    const res = await ragApi.offlineArticle(id, { reason })
    if (res?.data) ElMessage.success(res.data.message || '已下线')
    await refreshAfterAction()
  } catch (e) {
    ElMessage.error(e.message || '下线失败')
  } finally {
    actionLoading.value = false
  }
}

/** 重建 RAG 索引（发布后索引失败等场景的补偿入口，RD-008） */
async function doReindex() {
  const id = detail.value.article.articleId
  actionLoading.value = true
  try {
    const res = await ragApi.reindexArticle(id)
    if (res?.data) {
      if (res.data.indexStatus === 'INDEXED') {
        ElMessage.success(res.data.message || '索引重建完成')
      } else {
        ElMessage.warning(res.data.message || '索引重建返回异常状态')
      }
    }
    await refreshAfterAction()
  } catch (e) {
    ElMessage.error(e.message || '重建索引失败')
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

/**
 * 当前版本正文内容：后端 content 为 JSON 字符串（title/summary/keywords/body 四键，
 * 见 rag-service support/KnowledgeContent），此处解析供详情抽屉展示与人工审核使用。
 * 非 JSON 的历史脏数据整体按正文兜底展示，不白屏。
 */
const versionContent = computed(() => {
  const empty = { title: '', summary: '', keywords: '', body: '' }
  const raw = detail.value?.currentVersion?.content
  if (!raw) return empty
  try {
    const node = JSON.parse(raw)
    if (node && typeof node === 'object') {
      return {
        title: node.title || '',
        summary: node.summary || '',
        keywords: node.keywords || '',
        body: node.body || ''
      }
    }
  } catch (e) {
    return { ...empty, body: String(raw) }
  }
  return empty
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

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.kb-admin-container {
  min-width: 0;
  background-color: var(--el-bg-color-page);
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0;
  margin-bottom: 24px;
  background: var(--el-bg-color);
  border-bottom: 0;
  box-shadow: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
}

.main-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.sub-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-name {
  font-weight: 600;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.kb-main-body {
  padding: 0;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: var(--el-text-color-primary);
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trace-id-badge code {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.kb-uploader {
  width: 100%;
}

.advanced-params {
  margin: 12px 0;
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  padding: 0 12px;
}

.upload-action-bar {
  margin-top: 18px;
}

.submit-btn {
  width: 100%;
  font-weight: 600;
}

.history-list {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
  cursor: pointer;
  background: var(--el-fill-color-light);
  transition: all 0.2s;
}

.history-item:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.history-item.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.history-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.history-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.empty-hint {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 24px 0;
  font-size: 13px;
}

.empty-trace-container {
  padding: 60px 0;
}

.trace-summary-banner {
  display: flex;
  justify-content: space-between;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px 20px;
  margin-bottom: 20px;
}

.summary-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-metric .label {
  font-size: 12px;
  color: var(--el-color-success);
  font-weight: 500;
}

.summary-metric .value {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.summary-metric .value.doc-title {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-metric .value.highlight {
  color: var(--el-color-primary);
}

.section-heading {
  margin: 16px 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* ---- 详情抽屉：知识内容（审核对象） ---- */
.knowledge-content {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 12px;
  background: var(--el-fill-color-light);
}

.content-label {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.content-summary {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.content-keywords {
  margin-bottom: 10px;
}

.keyword-tag {
  margin-right: 6px;
}

.content-body {
  margin: 0;
  padding: 10px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 340px;
  overflow-y: auto;
  font-family: inherit;
}

.stage-inner-card {
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.stage-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.stage-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.stage-desc {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin: 4px 0 8px 0;
}

.stage-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-color-success);
  background: var(--el-bg-color);
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid var(--el-color-success);
  margin-bottom: 8px;
}

.stage-metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-chip {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 12px;
}

.m-key {
  color: var(--el-text-color-secondary);
  margin-right: 4px;
}

.m-val {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.chunks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chunk-collapse-title {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.chunk-index {
  background: var(--el-color-primary);
  color: var(--el-bg-color);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}

.chunk-section-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunk-tags {
  display: flex;
  gap: 6px;
  margin-right: 12px;
}

.chunk-body {
  padding: 10px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-lighter);
}

.chunk-meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.chunk-content-view {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--el-bg-color-page);
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  font-family: Consolas, Monaco, "Courier New", monospace;
  border: 1px solid var(--el-border-color);
}

/* ===== 生命周期管理 ===== */
.kb-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 600;
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.quick-warn {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-color-warning);
  line-height: 1.5;
}

.mt-16 {
  margin-top: 16px;
}

.mb-12 {
  margin-bottom: 12px;
}

.drawer-body {
  padding: 0 4px;
}

.drawer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.self-review-hint {
  width: 100%;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
}

.transition-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.transition-flow {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.transition-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.transition-reason {
  font-size: 12px;
  color: var(--el-text-color-regular);
  background: var(--el-bg-color-page);
  border-radius: 4px;
  padding: 4px 8px;
  margin-top: 4px;
}

.page-eyebrow { display:block; color:var(--el-color-primary); font-size:12px; font-weight:700; letter-spacing:1.4px; margin-bottom:8px; }
.main-title { font-size:28px; line-height:1.3; }
.sub-title { display:block; margin:8px 0 0; font-size:14px; line-height:1.6; }
.kb-header { gap:16px; flex-wrap:wrap; background:transparent; }
.logo-icon { width:48px; height:48px; border-radius:14px; background:var(--el-color-primary-light-9); color:var(--el-color-primary); display:grid; place-items:center; flex-shrink:0; }
:deep(.el-card) { border-radius:16px; box-shadow:none; }
.card-header-title { font-size:18px; }
.card-header-flex { gap:12px; flex-wrap:wrap; }
.scope-note { margin:0 0 16px; color:var(--el-text-color-secondary); font-size:13px; line-height:1.6; }
.knowledge-title { color:var(--el-text-color-primary); font-size:14px; font-weight:600; line-height:1.6; white-space:normal; overflow-wrap:anywhere; }
.knowledge-article-id { margin-top:4px; color:var(--el-text-color-secondary); font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.page-error { margin-bottom:16px; }
.trace-id-badge { color:var(--el-text-color-secondary); font-size:12px; overflow-wrap:anywhere; }
.trace-summary-banner { gap:16px; flex-wrap:wrap; }
.summary-metric .label { color:var(--el-text-color-secondary); }
.timeline-section { margin-top:24px; }
.stage-inner-card { border-radius:10px; }
.history-item:focus-visible { outline:2px solid var(--el-color-primary); outline-offset:2px; }
.chunk-collapse-title { min-width:0; flex-wrap:wrap; padding:10px 0; }
.chunk-tags { flex-wrap:wrap; }
:deep(.el-collapse-item__header) { height:auto; min-height:48px; line-height:1.5; }
.drawer-body { min-height:100px; }
:deep(.el-radio) { white-space:normal; height:auto; min-height:36px; }
:deep(.el-radio__label) { white-space:normal; line-height:1.6; }
:deep(.el-radio-group) { gap:8px; }
@media(max-width:767px) {
  .main-title { font-size:24px; }
  .header-left { align-items:flex-start; }
  .logo-icon { display:none; }
  .kb-main-body :deep(.el-col) { margin-bottom:16px; }
  :deep(.el-card__body), :deep(.el-card__header) { padding:16px; }
  .list-toolbar { width:100%; }
  .list-toolbar :deep(.el-radio-group) { display:flex; flex-wrap:wrap; gap:6px; }
  .list-toolbar :deep(.el-radio-button__inner) { border:1px solid var(--el-border-color); border-radius:8px; min-height:40px; display:flex; align-items:center; }
  .pager-row { justify-content:center; }
  .pager-row :deep(.el-pagination) { flex-wrap:wrap; justify-content:center; gap:8px; }
  .chunks-header, .chunk-meta-bar { flex-wrap:wrap; gap:8px; }
  .chunks-header :deep(.el-input) { width:100% !important; }
  .chunk-tags { width:100%; margin:0; }
  .history-item-meta { flex-wrap:wrap; gap:6px 12px; }
  .trace-summary-banner { padding:16px; }
  .summary-metric { width:calc(50% - 8px); min-width:0; }
  .stage-title-row { gap:8px; align-items:flex-start; }
  :deep(.el-drawer__body) { padding:16px; }
  :deep(.el-descriptions__table) { overflow-wrap:anywhere; }
}
</style>
