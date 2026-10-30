<template>
  <el-drawer
    v-model="visible"
    title="🧠 知识图谱多跳思维推导链路 (GraphRAG)"
    direction="rtl"
    size="560px"
    class="graph-reasoning-drawer"
    :before-close="handleClose"
  >
    <template #header>
      <div class="drawer-header-custom">
        <div class="header-icon-box">
          <el-icon><Connection /></el-icon>
        </div>
        <div>
          <div class="drawer-title">知识图谱多跳思维推导链路</div>
          <div class="drawer-subtitle">Neo4j 刚性拓扑因果演绎 · 跨卡穿透溯源</div>
        </div>
      </div>
    </template>

    <div v-if="reasoning" class="drawer-body-wrap">
      <!-- 场景提示横幅 -->
      <div class="summary-banner">
        <div class="summary-title">
          <span class="pulse-dot"></span>
          <span>已激活 GraphRAG 双轨拓扑演绎</span>
        </div>
        <p class="summary-desc">
          本轮问答不仅检索了文本相似度切片，更通过企业知识图谱（Neo4j）穿透了深层因果关系与资产依赖，成功排除了表面现象干扰。
        </p>
      </div>

      <!-- 1. 核心种子实体 -->
      <section class="section-block">
        <div class="section-title">
          <el-icon><Aim /></el-icon>
          <span>识别核心关联实体 (Seed Entities)</span>
          <span class="count-tag">{{ reasoning.entities.length }} 个节点</span>
        </div>
        <div class="entities-wrap">
          <el-tag
            v-for="(entity, idx) in reasoning.entities"
            :key="idx"
            :type="entityTagType(entity)"
            effect="light"
            class="entity-pill"
          >
            <el-icon class="entity-icon"><component :is="entityIcon(entity)" /></el-icon>
            {{ entity }}
          </el-tag>
        </div>
      </section>

      <!-- 2. 拓扑演绎推导链 -->
      <section class="section-block">
        <div class="section-title">
          <el-icon><Share /></el-icon>
          <span>拓扑因果演绎链路 (Causal Chain)</span>
          <span class="count-tag">{{ reasoning.chains.length }} 跳推导</span>
        </div>
        <div class="chains-flow">
          <div
            v-for="(ch, idx) in reasoning.chains"
            :key="idx"
            class="chain-card"
            :class="{ 'causal-highlight': ch.isCausal }"
          >
            <div class="chain-header">
              <span class="step-badge">第 {{ ch.step }} 跳</span>
              <el-tag size="small" :type="ch.isCausal ? 'danger' : 'warning'" effect="plain">
                {{ ch.tag }}
              </el-tag>
            </div>

            <!-- 结构化节点关系流转图 -->
            <div v-if="ch.src && ch.tgt" class="chain-relation-visual">
              <div class="chain-node node-src">{{ ch.src }}</div>
              <div class="chain-arrow">
                <span class="arrow-label">{{ ch.rel }}</span>
                <span class="arrow-line">──────▶</span>
              </div>
              <div class="chain-node node-tgt" :class="{ 'node-root-cause': ch.isCausal }">
                {{ ch.tgt }}
                <span v-if="ch.isCausal && ch.tgt.includes('根因')" class="root-badge">根因</span>
              </div>
            </div>
            <!-- 兜底纯文本事实 -->
            <div v-else class="chain-raw-text">
              {{ ch.raw }}
            </div>
          </div>
        </div>
      </section>

      <!-- 3. 处置策略与排查建议 -->
      <section class="section-block">
        <div class="section-title">
          <el-icon><Opportunity /></el-icon>
          <span>图谱指导处置建议 (Action Strategy)</span>
        </div>
        <div class="suggestion-card">
          <el-icon class="sug-icon"><CircleCheck /></el-icon>
          <div class="sug-content">
            <div class="sug-title">根因处置优先级</div>
            <div class="sug-desc">{{ reasoning.suggestion }}</div>
          </div>
        </div>
      </section>

      <!-- 4. 穿透关联知识库父卡 -->
      <section class="section-block">
        <div class="section-title">
          <el-icon><Document /></el-icon>
          <span>穿透关联知识库卡片 (Associated Cards)</span>
          <span class="count-tag">{{ reasoning.cards.length }} 篇</span>
        </div>
        <div class="cards-list">
          <div
            v-for="card in reasoning.cards"
            :key="card.versionId"
            class="card-item"
            :class="{ 'card-graph-source': card.hasGraph }"
          >
            <div class="card-item-main">
              <div class="card-item-title">
                <span v-if="card.hasGraph" class="graph-source-badge">图谱推导源</span>
                {{ card.title }}
              </div>
              <div class="card-item-meta">
                <span>版本: {{ card.versionId }}</span>
                <span v-if="card.articleId">卡号: {{ card.articleId }}</span>
              </div>
            </div>
            <div class="card-item-score">
              <el-tag size="small" type="info">匹配度 {{ card.score }}</el-tag>
            </div>
          </div>
        </div>
      </section>

      <!-- 5. 全景拓扑工作台联动入口 -->
      <div class="workbench-action-box">
        <div class="workbench-info">
          <div class="wb-title">想在交互式画布中自由探索该因果网络？</div>
          <div class="wb-desc">可直接调出 GraphRAG 全景评测工作台，支持物理力导向图、关系拖拽与新旧制度剪枝演示。</div>
        </div>
        <el-button
          type="primary"
          :icon="FullScreen"
          class="wb-launch-btn"
          @click="openWorkbench"
        >
          在 Neo4j 全景拓扑工作台打开 (8350) ↗
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import {
  Connection, Aim, Share, Opportunity, CircleCheck,
  Document, FullScreen, Warning, Key, Monitor, Setting
} from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  reasoning: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

function handleClose() {
  visible.value = false
}

function entityTagType(entity) {
  if (entity.includes('691') || entity.includes('错误') || entity.includes('失败') || entity.includes('502')) {
    return 'danger'
  }
  if (entity.includes('锁定') || entity.includes('根因') || entity.includes('轮询')) {
    return 'warning'
  }
  return 'primary'
}

function entityIcon(entity) {
  if (entity.includes('691') || entity.includes('错误') || entity.includes('失败')) {
    return Warning
  }
  if (entity.includes('密码') || entity.includes('账号') || entity.includes('锁定')) {
    return Key
  }
  if (entity.includes('VPN') || entity.includes('网络') || entity.includes('客户端')) {
    return Monitor
  }
  return Setting
}

function openWorkbench() {
  const scene = props.reasoning?.scene || 'vpn'
  const url = `http://127.0.0.1:8350/?scene=${encodeURIComponent(scene)}`
  window.open(url, '_blank')
}
</script>

<style scoped>
.drawer-header-custom {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.drawer-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.drawer-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.drawer-body-wrap {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 24px;
}

/* 顶部横幅 */
.summary-banner {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 12px;
  padding: 14px 16px;
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #6366f1;
  margin-bottom: 6px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  box-shadow: 0 0 8px #6366f1;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
}

.summary-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
  margin: 0;
}

/* 各区块通用 */
.section-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.count-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color);
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: auto;
}

/* 实体池 */
.entities-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 8px;
}

/* 推导流转链 */
.chains-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chain-card {
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
  transition: all 0.2s ease;
}

.chain-card.causal-highlight {
  border-color: rgba(239, 68, 68, 0.3);
  background: linear-gradient(to right, rgba(239, 68, 68, 0.03), transparent);
}

.chain-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step-badge {
  font-size: 11px;
  font-weight: 800;
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.chain-relation-visual {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 10px 12px;
}

.chain-node {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--el-fill-color);
  max-width: 40%;
  word-break: break-all;
  text-align: center;
}

.node-src {
  color: var(--el-text-color-primary);
}

.node-tgt {
  color: #4f46e5;
  position: relative;
}

.node-root-cause {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.root-badge {
  font-size: 9px;
  background: #ef4444;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 4px;
  font-weight: bold;
}

.chain-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-width: 60px;
}

.arrow-label {
  font-size: 11px;
  font-weight: 700;
  color: #8b5cf6;
  white-space: nowrap;
  margin-bottom: -2px;
}

.arrow-line {
  font-size: 10px;
  color: #a78bfa;
  letter-spacing: -1px;
}

.chain-raw-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}

/* 处置建议 */
.suggestion-card {
  display: flex;
  gap: 12px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 10px;
  padding: 12px 14px;
}

.sug-icon {
  font-size: 20px;
  color: #10b981;
  margin-top: 2px;
}

.sug-title {
  font-size: 13px;
  font-weight: 700;
  color: #059669;
  margin-bottom: 4px;
}

.sug-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}

/* 知识卡片 */
.cards-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
}

.card-item.card-graph-source {
  border-color: rgba(99, 102, 241, 0.35);
  background: rgba(99, 102, 241, 0.04);
}

.card-item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.graph-source-badge {
  font-size: 10px;
  font-weight: 700;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.12);
  padding: 1px 5px;
  border-radius: 4px;
}

.card-item-meta {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  display: flex;
  gap: 12px;
}

/* 底部全景画布入口 */
.workbench-action-box {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  border-radius: 12px;
  padding: 16px;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 4px 16px rgba(49, 46, 129, 0.25);
  margin-top: 10px;
}

.wb-title {
  font-size: 14px;
  font-weight: 700;
  color: #e0e7ff;
}

.wb-desc {
  font-size: 12px;
  color: #a5b4fc;
  line-height: 1.4;
  margin-top: 4px;
}

.wb-launch-btn {
  background: #6366f1;
  border-color: #818cf8;
  font-weight: 700;
  width: 100%;
}

.wb-launch-btn:hover {
  background: #4f46e5;
  border-color: #6366f1;
}
</style>
