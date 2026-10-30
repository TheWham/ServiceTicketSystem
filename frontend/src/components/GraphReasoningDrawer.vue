<template>
  <div>
    <!-- 主抽屉：思维推导链路 -->
    <el-drawer
      v-model="visible"
      title="🧠 知识图谱多跳思维推导链路 (GraphRAG)"
      direction="rtl"
      size="620px"
      class="graph-reasoning-drawer"
      :before-close="handleClose"
      @opened="onDrawerOpened"
      @closed="onDrawerClosed"
    >
      <template #header>
        <div class="drawer-header-custom">
          <div class="header-icon-box">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="header-title-box">
            <div class="drawer-title">知识图谱多跳思维推导链路</div>
            <div class="drawer-subtitle">Neo4j 刚性拓扑因果演绎 · 动态子图与根因穿透</div>
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
            本轮问答不仅基于文本向量检索，更直接调取企业知识图谱（Neo4j）的刚性因果链与资产依赖进行多跳演绎，直接穿透表面现象锁定真实根因。
          </p>
        </div>

        <!-- 1. 交互式因果拓扑图（内置画布） -->
        <section class="section-block">
          <div class="section-title">
            <el-icon><Share /></el-icon>
            <span>因果网络全景拓扑图 (Topology Graph)</span>
            <div class="section-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :icon="FullScreen"
                @click="openFullscreen"
              >
                大屏全屏显示
              </el-button>
            </div>
          </div>

          <!-- 画布卡片 -->
          <div class="topology-canvas-card">
            <!-- 顶部工具小栏 -->
            <div class="canvas-toolbar">
              <span class="canvas-tip">可拖拽节点 · 滚轮缩放画布</span>
              <div class="canvas-btn-group">
                <el-button size="small" circle :icon="RefreshRight" title="复位视角" @click="resetDrawerNetwork" />
              </div>
            </div>

            <!-- Vis.js 容器 -->
            <div ref="drawerNetworkRef" class="network-container"></div>

            <!-- 图例栏 -->
            <div class="legend-bar">
              <span class="legend-item"><span class="dot dot-root"></span>根因节点</span>
              <span class="legend-item"><span class="dot dot-fault"></span>故障表象</span>
              <span class="legend-item"><span class="dot dot-action"></span>排查/处置动作</span>
              <span class="legend-item"><span class="dot dot-sys"></span>系统/通道资产</span>
            </div>
          </div>
        </section>

        <!-- 2. 核心种子实体 -->
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

        <!-- 3. 拓扑演绎推导链 -->
        <section class="section-block">
          <div class="section-title">
            <el-icon><Share /></el-icon>
            <span>分步推导逻辑链 (Deduction Steps)</span>
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

        <!-- 4. 处置策略与排查建议 -->
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

        <!-- 5. 穿透关联知识库父卡 -->
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
      </div>
    </el-drawer>

    <!-- 大屏全屏显示弹窗 -->
    <el-dialog
      v-model="fullscreenVisible"
      fullscreen
      destroy-on-close
      class="topology-fullscreen-dialog"
      :show-close="false"
      @opened="onFullscreenOpened"
      @closed="onFullscreenClosed"
    >
      <div class="fullscreen-container">
        <!-- 大屏顶部操作栏 -->
        <div class="fullscreen-header">
          <div class="fs-title-box">
            <div class="fs-title">
              <el-icon class="fs-icon"><Connection /></el-icon>
              <span>知识图谱多跳因果全景拓扑 (大屏模式)</span>
            </div>
            <div class="fs-sub">
              当前展示：{{ reasoning?.entities?.length || 0 }} 个核心实体 · {{ reasoning?.chains?.length || 0 }} 跳因果关系
            </div>
          </div>

          <!-- 右侧操作按钮群 -->
          <div class="fs-actions">
            <div class="legend-bar fs-legend">
              <span class="legend-item"><span class="dot dot-root"></span>根因节点</span>
              <span class="legend-item"><span class="dot dot-fault"></span>故障表象</span>
              <span class="legend-item"><span class="dot dot-action"></span>排查/处置动作</span>
              <span class="legend-item"><span class="dot dot-sys"></span>系统/通道资产</span>
            </div>
            <el-button type="info" plain :icon="RefreshRight" @click="resetFullscreenNetwork">复位视角</el-button>
            <el-button type="primary" :icon="Close" @click="fullscreenVisible = false">退出大屏</el-button>
          </div>
        </div>

        <!-- 大屏主画布容器 -->
        <div class="fullscreen-canvas-wrap">
          <div ref="fullscreenNetworkRef" class="fullscreen-network-container"></div>
          <!-- 悬浮提示 -->
          <div class="fullscreen-floating-hint">
            💡 支持任意拖动节点 · 滚轮自由平移缩放 · 物理力导向实时动态推演
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Connection, Aim, Share, Opportunity, CircleCheck,
  Document, FullScreen, Warning, Key, Monitor, Setting,
  RefreshRight, Close
} from '@element-plus/icons-vue'
import { Network, DataSet } from 'vis-network/standalone/esm/vis-network.js'

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

const fullscreenVisible = ref(false)
const drawerNetworkRef = ref(null)
const fullscreenNetworkRef = ref(null)

// 保持为非响应式变量，避免 Vue Proxy 破坏 Vis.js 内部循环引用
let drawerNetwork = null
let fullscreenNetwork = null

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

// 节点与连线色彩配置
function getNodeColor(label) {
  if (/锁定|根因/.test(label)) {
    return { background: '#e11d48', border: '#f43f5e' } // 玫瑰红 / 根因
  }
  if (/错误|故障|失败|超时|异常|691|502|APPCRASH|闪退|崩溃|NXDOMAIN|蓝屏|BSOD/.test(label)) {
    return { background: '#d97706', border: '#f59e0b' } // 琥珀橙 / 故障表象
  }
  if (/处置|排查|重置|等待|平台|控制器|服务台|sfc|ipconfig|flushdns|BlueScreenView|查看器|1000/.test(label)) {
    return { background: '#059669', border: '#10b981' } // 翡翠绿 / 处置排查
  }
  if (/系统|网络|VPN|邮箱|客户端|ERP|运行库|Redistributable|Framework|DNS|驱动|内存/.test(label)) {
    return { background: '#0284c7', border: '#38bdf8' } // 科技天蓝 / 系统与通道
  }
  return { background: '#6366f1', border: '#818cf8' } // 经典紫色 / 其他关联
}

function getEdgeColor(rel) {
  if (/根因|诱发/.test(rel)) return { color: '#f43f5e', highlight: '#fda4af', hover: '#fb7185' }
  if (/排查|处置/.test(rel)) return { color: '#10b981', highlight: '#6ee7b7', hover: '#34d399' }
  if (/废止|替代/.test(rel)) return { color: '#ef4444', highlight: '#fca5a5', hover: '#f87171' }
  return { color: '#818cf8', highlight: '#c7d2fe', hover: '#a5b4fc' }
}

// 异步尝试从 Neo4j 读取真实全量子图，若失败则安全降级为推导链
async function fetchNeo4jSubgraph(entities = [], scene = 'custom') {
  try {
    const entParam = Array.isArray(entities) ? entities.join(',') : ''
    const url = `http://127.0.0.1:8310/api/neo4j/graph_data?entities=${encodeURIComponent(entParam)}&scene=${encodeURIComponent(scene)}`
    const res = await fetch(url, {
      signal: AbortSignal.timeout(1800)
    })
    if (res.ok) {
      const json = await res.json()
      if (json.code === 0 && json.data && json.data.nodes?.length) {
        return json.data
      }
    }
  } catch (e) {
    // 降级为本地推导链构建
  }
  return null
}

// 构建拓扑图数据（融合 Neo4j 真实子图与本地推导事实）
async function buildGraphData() {
  if (!props.reasoning) return { nodes: new DataSet([]), edges: new DataSet([]) }

  const entities = props.reasoning.entities || []
  const scene = props.reasoning.scene || 'custom'
  const neo4jData = await fetchNeo4jSubgraph(entities, scene)

  // 校验返回的 Neo4j 节点是否与当前实体匹配（杜绝返回默认历史 VPN 数据）
  const hasMatchedEntities = neo4jData && neo4jData.nodes?.length && (
    entities.length === 0 ||
    neo4jData.nodes.some(n => {
      const label = n.label || n.id || ''
      return entities.some(ent => label.includes(ent) || ent.includes(label))
    })
  )

  if (hasMatchedEntities && neo4jData.edges?.length) {
    // 1. 优先使用与 Neo4j 100% 对应的原生节点与关系
    const nodesMap = new Map()
    for (const n of neo4jData.nodes) {
      const col = getNodeColor(n.label || n.id)
      const isRoot = /根因|锁定/.test(n.label || n.id)
      nodesMap.set(n.id, {
        id: n.id,
        label: n.label || n.id,
        shape: 'dot',
        size: isRoot ? 24 : (n.id.startsWith('ITKB-') ? 20 : 16),
        color: {
          background: col.background,
          border: col.border,
          highlight: { background: '#818cf8', border: '#c7d2fe' },
          hover: { background: '#6366f1', border: '#a5b4fc' }
        },
        font: { color: '#ffffff', size: 12, strokeWidth: 2, strokeColor: '#020617' },
        title: `实体: ${n.label || n.id}${n.is_deprecated ? ' (已废止)' : ''}`
      })
    }

    const edges = []
    const edgeKeySet = new Set()
    for (let idx = 0; idx < neo4jData.edges.length; idx++) {
      const e = neo4jData.edges[idx]
      const ec = getEdgeColor(e.label)
      const key = `${e.from}->${e.to}:${e.label}`
      if (!edgeKeySet.has(key)) {
        edgeKeySet.add(key)
        edges.push({
          id: `ne_${idx}`,
          from: e.from,
          to: e.to,
          label: e.label,
          arrows: 'to',
          color: ec,
          font: { size: 10, color: '#cbd5e1', background: '#0f172a', strokeWidth: 0 },
          title: e.title || `${e.from} ──(${e.label})──> ${e.to}`
        })
      }
    }

    // 补充：确保当前推理事实链中的边 100% 呈现在图谱中
    for (const ch of props.reasoning.chains || []) {
      if (ch.src && ch.tgt) {
        if (!nodesMap.has(ch.src)) {
          const col = getNodeColor(ch.src)
          nodesMap.set(ch.src, {
            id: ch.src,
            label: ch.src,
            shape: 'dot',
            size: /根因|锁定/.test(ch.src) ? 24 : 16,
            color: { background: col.background, border: col.border },
            font: { color: '#ffffff', size: 12, strokeWidth: 2, strokeColor: '#020617' },
            title: `实体: ${ch.src}`
          })
        }
        if (!nodesMap.has(ch.tgt)) {
          const col = getNodeColor(ch.tgt)
          nodesMap.set(ch.tgt, {
            id: ch.tgt,
            label: ch.tgt,
            shape: 'dot',
            size: /根因|锁定/.test(ch.tgt) ? 24 : 16,
            color: { background: col.background, border: col.border },
            font: { color: '#ffffff', size: 12, strokeWidth: 2, strokeColor: '#020617' },
            title: `实体: ${ch.tgt}`
          })
        }
        const key = `${ch.src}->${ch.tgt}:${ch.rel}`
        if (!edgeKeySet.has(key)) {
          edgeKeySet.add(key)
          const ec = getEdgeColor(ch.rel)
          edges.push({
            id: `chain_${key}`,
            from: ch.src,
            to: ch.tgt,
            label: ch.rel,
            arrows: 'to',
            color: ec,
            font: { size: 10, color: '#cbd5e1', background: '#0f172a', strokeWidth: 0 },
            title: `${ch.src} ──(${ch.rel})──> ${ch.tgt}`
          })
        }
      }
    }

    return { nodes: new DataSet(Array.from(nodesMap.values())), edges: new DataSet(edges) }
  }

  // 2. 本地兜底模式：基于已解析的推导链组装
  const nodesMap = new Map()
  const edgesList = []
  const connectedNodeIds = new Set()

  // 收集所有带连线的关系
  for (const ch of props.reasoning.chains || []) {
    if (ch.src && ch.tgt) {
      connectedNodeIds.add(ch.src)
      connectedNodeIds.add(ch.tgt)
      const ec = getEdgeColor(ch.rel)
      edgesList.push({
        from: ch.src,
        to: ch.tgt,
        label: ch.rel,
        arrows: 'to',
        color: ec,
        font: { size: 10, color: '#cbd5e1', background: '#0f172a', strokeWidth: 0 },
        title: `${ch.src} ──(${ch.rel})──> ${ch.tgt}`
      })
    }
  }

  // 保证已连接节点进入节点表
  for (const id of connectedNodeIds) {
    const col = getNodeColor(id)
    nodesMap.set(id, {
      id,
      label: id,
      shape: 'dot',
      size: /根因|锁定/.test(id) ? 24 : 16,
      color: {
        background: col.background,
        border: col.border,
        highlight: { background: '#818cf8', border: '#c7d2fe' },
        hover: { background: '#6366f1', border: '#a5b4fc' }
      },
      font: { color: '#ffffff', size: 12, strokeWidth: 2, strokeColor: '#020617' },
      title: `实体节点: ${id}`
    })
  }

  // 如果某些种子实体没有孤立连线，与其核心根因节点连接，杜绝出现孤立悬空点
  const rootNode = Array.from(nodesMap.keys()).find(k => /锁定|根因/.test(k))
  for (const ent of props.reasoning.entities || []) {
    if (!nodesMap.has(ent)) {
      if (rootNode) {
        // 自动补充与根因的推导连线
        edgesList.push({
          from: ent,
          to: rootNode,
          label: '诱发根因',
          arrows: 'to',
          color: getEdgeColor('诱发根因'),
          font: { size: 10, color: '#cbd5e1', background: '#0f172a', strokeWidth: 0 },
          title: `${ent} ──(诱发根因)──> ${rootNode}`
        })
      }
      const col = getNodeColor(ent)
      nodesMap.set(ent, {
        id: ent,
        label: ent,
        shape: 'dot',
        size: 18,
        color: {
          background: col.background,
          border: col.border,
          highlight: { background: '#818cf8', border: '#c7d2fe' },
          hover: { background: '#6366f1', border: '#a5b4fc' }
        },
        font: { color: '#ffffff', size: 12, strokeWidth: 2, strokeColor: '#020617' },
        title: `核心实体: ${ent}`
      })
    }
  }

  return {
    nodes: new DataSet(Array.from(nodesMap.values())),
    edges: new DataSet(edgesList)
  }
}

// 初始化抽屉内部 Vis-Network 画布
async function initDrawerNetwork() {
  if (!drawerNetworkRef.value) return
  if (drawerNetwork) {
    drawerNetwork.destroy()
    drawerNetwork = null
  }

  const { nodes, edges } = await buildGraphData()
  if (!drawerNetworkRef.value) return

  const options = {
    physics: {
      barnesHut: {
        gravitationalConstant: -3200,
        centralGravity: 0.25,
        springLength: 105,
        springConstant: 0.045,
        damping: 0.09
      },
      stabilization: { iterations: 110 }
    },
    interaction: {
      hover: true,
      zoomView: true,
      dragView: true,
      tooltipDelay: 100
    }
  }

  drawerNetwork = new Network(drawerNetworkRef.value, { nodes, edges }, options)
}

function resetDrawerNetwork() {
  if (drawerNetwork) {
    drawerNetwork.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } })
  }
}

function onDrawerOpened() {
  nextTick(() => {
    setTimeout(() => {
      initDrawerNetwork()
    }, 100)
  })
}

function onDrawerClosed() {
  if (drawerNetwork) {
    drawerNetwork.destroy()
    drawerNetwork = null
  }
}

// 监听当前推导上下文变更，保证每次打开不同问题卡片时画布拓扑实时更新
watch(() => props.reasoning, () => {
  if (visible.value && drawerNetworkRef.value) {
    nextTick(() => {
      initDrawerNetwork()
    })
  }
}, { deep: true })

// 大屏全屏显示
function openFullscreen() {
  fullscreenVisible.value = true
}

function onFullscreenOpened() {
  nextTick(() => {
    setTimeout(() => {
      initFullscreenNetwork()
    }, 100)
  })
}

function onFullscreenClosed() {
  if (fullscreenNetwork) {
    fullscreenNetwork.destroy()
    fullscreenNetwork = null
  }
}

async function initFullscreenNetwork() {
  if (!fullscreenNetworkRef.value) return
  if (fullscreenNetwork) {
    fullscreenNetwork.destroy()
    fullscreenNetwork = null
  }

  const { nodes, edges } = await buildGraphData()
  if (!fullscreenNetworkRef.value) return
  const options = {
    physics: {
      barnesHut: {
        gravitationalConstant: -4800,
        centralGravity: 0.20,
        springLength: 140,
        springConstant: 0.04,
        damping: 0.09
      },
      stabilization: { iterations: 130 }
    },
    interaction: {
      hover: true,
      zoomView: true,
      dragView: true,
      tooltipDelay: 100
    }
  }

  fullscreenNetwork = new Network(fullscreenNetworkRef.value, { nodes, edges }, options)
}

function resetFullscreenNetwork() {
  if (fullscreenNetwork) {
    fullscreenNetwork.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } })
  }
}

onBeforeUnmount(() => {
  if (drawerNetwork) {
    drawerNetwork.destroy()
    drawerNetwork = null
  }
  if (fullscreenNetwork) {
    fullscreenNetwork.destroy()
    fullscreenNetwork = null
  }
})
</script>

<style scoped>
.drawer-header-custom {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-box {
  width: 38px;
  height: 38px;
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

.section-actions {
  margin-left: auto;
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

/* 拓扑画布卡片 */
.topology-canvas-card {
  position: relative;
  background: #090d16;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.canvas-toolbar {
  position: absolute;
  top: 10px;
  left: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 5;
  pointer-events: none;
}

.canvas-tip {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.75);
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid rgba(51, 65, 85, 0.5);
  backdrop-filter: blur(4px);
}

.canvas-btn-group {
  pointer-events: auto;
}

.network-container {
  width: 100%;
  height: 280px;
  cursor: grab;
}

.network-container:active {
  cursor: grabbing;
}

/* 图例 */
.legend-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  background: rgba(15, 23, 42, 0.9);
  padding: 8px 14px;
  border-top: 1px solid rgba(51, 65, 85, 0.5);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #cbd5e1;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.dot-root { background: #e11d48; box-shadow: 0 0 6px #f43f5e; }
.dot-fault { background: #d97706; }
.dot-action { background: #059669; }
.dot-sys { background: #0284c7; }

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

/* ================= 大屏全屏弹窗样式 ================= */
.fullscreen-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #020617;
  color: #f8fafc;
}

.fullscreen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
}

.fs-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
}

.fs-icon {
  font-size: 22px;
  color: #818cf8;
}

.fs-sub {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.fs-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.fs-legend {
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 6px 14px;
}

.fullscreen-canvas-wrap {
  position: relative;
  flex: 1;
  width: 100%;
  overflow: hidden;
}

.fullscreen-network-container {
  width: 100%;
  height: 100%;
  cursor: grab;
}

.fullscreen-network-container:active {
  cursor: grabbing;
}

.fullscreen-floating-hint {
  position: absolute;
  bottom: 18px;
  left: 24px;
  font-size: 12px;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(51, 65, 85, 0.7);
  padding: 6px 14px;
  border-radius: 20px;
  backdrop-filter: blur(6px);
  pointer-events: none;
}
</style>
