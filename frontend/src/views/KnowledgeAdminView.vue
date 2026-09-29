<template>
  <div class="kb-admin-container">
    <!-- 顶部导航栏 -->
    <header class="kb-header">
      <div class="header-left">
        <div class="logo-icon">📚</div>
        <div class="header-titles">
          <h1 class="main-title">知识库管理工作台</h1>
          <span class="sub-title">RAG 文档解析、智能切片与 Elasticsearch 链路追踪</span>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="danger" effect="dark" round class="role-badge">
          知识库管理员
        </el-tag>
        <el-button type="warning" plain size="small" :loading="isInitEs" @click="handleInitEsIndex">
          ⚡ 初始化 ES 索引
        </el-button>
        <span class="user-name">{{ userStore.currentUser?.name || '知识库管理员' }}</span>
        <el-button type="info" plain size="small" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </header>

    <main class="kb-main-body">
      <el-row :gutter="20">
        <!-- 左侧：文档上传与参数配置 -->
        <el-col :xs="24" :lg="9">
          <el-card shadow="hover" class="box-card upload-card">
            <template #header>
              <div class="card-header-title">
                <el-icon><UploadFilled /></el-icon>
                <span>上传知识文档 (RAG Ingestion)</span>
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

              <el-collapse class="advanced-params">
                <el-collapse-item title="⚙️ 切片策略高级参数设置">
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
                  {{ isProcessing ? '切片与入库处理中...' : '开始切片并写入 ES 知识库' }}
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
                  <span>最近执行链路记录</span>
                </div>
                <el-button link type="primary" size="small" @click="fetchRecentTraces">
                  刷新
                </el-button>
              </div>
            </template>
            <div v-if="historyTraces.length === 0" class="empty-hint">
              暂无历史链路记录，请上传文档执行
            </div>
            <div v-else class="history-list">
              <div
                v-for="item in historyTraces"
                :key="item.traceId"
                class="history-item"
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
                  <span>RAG 切片入库全链路追踪 (Pipeline Trace)</span>
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
                  <el-tag type="success" effect="plain">已入库索引</el-tag>
                </div>
              </div>

              <!-- 链路步骤时间线 -->
              <div class="timeline-section">
                <h3 class="section-heading">📌 链路执行步骤详情</h3>
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
                  <h3 class="section-heading">📑 生成语义切片明细 (Chunks Preview)</h3>
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
                              {{ chunk.vectorDimensions || 1024 }} 维向量
                            </el-tag>
                            <el-tag size="small" type="success">ES: {{ chunk.esDocId || '已索引' }}</el-tag>
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
    </main>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  UploadFilled,
  Cpu,
  Clock,
  Connection,
  Check,
  Search
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { ragApi } from '../api/index.js'

const router = useRouter()
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

/** 上传表单及切片策略配置 */
const uploadForm = ref({
  title: '',           // 自定义文档标题（留空自动解析）
  categoryId: 'C_NET', // 默认分类：网络与连接
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

// 页面加载时自动拉取最近执行的历史链路
onMounted(() => {
  fetchRecentTraces()
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
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (uploadForm.value.title) formData.append('title', uploadForm.value.title)
  if (uploadForm.value.categoryId) formData.append('categoryId', uploadForm.value.categoryId)
  formData.append('chunkSize', uploadForm.value.chunkSize)
  formData.append('chunkOverlap', uploadForm.value.chunkOverlap)

  try {
    const res = await ragApi.uploadDocument(formData)
    if (res && res.data) {
      currentTrace.value = res.data.trace
      ElMessage.success('文档切片并写入 ES 成功！')
      fetchRecentTraces()
      if (res.data.trace?.chunks?.length > 0) {
        activeChunkNames.value = [res.data.trace.chunks[0].chunkId]
      }
    }
  } catch (err) {
    ElMessage.error(err.message || '文档处理失败')
  } finally {
    isProcessing.value = false
  }
}

async function fetchRecentTraces() {
  try {
    const res = await ragApi.listTraces()
    if (res && res.data) {
      historyTraces.value = res.data
      if (!currentTrace.value && res.data.length > 0) {
        currentTrace.value = res.data[0]
      }
    }
  } catch (e) {
    console.warn('获取历史追踪记录失败', e)
  }
}

function loadTrace(trace) {
  currentTrace.value = trace
  if (trace.chunks?.length > 0) {
    activeChunkNames.value = [trace.chunks[0].chunkId]
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

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.kb-admin-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 28px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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
  color: #303133;
}

.sub-title {
  font-size: 12px;
  color: #909399;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-name {
  font-weight: 600;
  color: #606266;
  font-size: 14px;
}

.kb-main-body {
  padding: 20px 24px;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trace-id-badge code {
  background: #ecf5ff;
  color: #409eff;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.kb-uploader {
  width: 100%;
}

.advanced-params {
  margin: 12px 0;
  border: 1px dashed #dcdfe6;
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
  border: 1px solid #e4e7ed;
  cursor: pointer;
  background: #fafafa;
  transition: all 0.2s;
}

.history-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.history-item.active {
  background: #ecf5ff;
  border-color: #409eff;
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
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #909399;
}

.empty-hint {
  text-align: center;
  color: #909399;
  padding: 24px 0;
  font-size: 13px;
}

.empty-trace-container {
  padding: 60px 0;
}

.trace-summary-banner {
  display: flex;
  justify-content: space-between;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
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
  color: #67c23a;
  font-weight: 500;
}

.summary-metric .value {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.summary-metric .value.doc-title {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-metric .value.highlight {
  color: #409eff;
}

.section-heading {
  margin: 16px 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.stage-inner-card {
  border-radius: 6px;
  background: #fafbfc;
}

.stage-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.stage-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.stage-desc {
  font-size: 12px;
  color: #606266;
  margin: 4px 0 8px 0;
}

.stage-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #67c23a;
  background: #fff;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
  margin-bottom: 8px;
}

.stage-metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-chip {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 11px;
}

.m-key {
  color: #909399;
  margin-right: 4px;
}

.m-val {
  font-weight: 600;
  color: #303133;
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
  background: #409eff;
  color: #fff;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}

.chunk-section-title {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
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
  background: #fdfdfd;
  border-radius: 4px;
  border: 1px solid #f2f6fc;
}

.chunk-meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.chunk-content-view {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #2c3e50;
  font-family: Consolas, Monaco, "Courier New", monospace;
  border: 1px solid #e4e7ed;
}
</style>
