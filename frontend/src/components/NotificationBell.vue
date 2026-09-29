<template>
  <el-popover
    placement="bottom-end"
    :width="380"
    trigger="click"
    @show="loadList"
  >
    <template #reference>
      <el-badge :value="pendingCount > 0 ? pendingCount : ''" :max="99" class="notify-badge">
        <el-button text circle class="bell-btn">
          <el-icon :size="18"><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>

    <div class="notify-panel">
      <div class="notify-header">
        <span class="notify-title">站内通知</span>
        <el-tag v-if="pendingCount > 0" type="danger" size="small" effect="dark">
          {{ pendingCount }} 条待办
        </el-tag>
      </div>

      <el-scrollbar v-if="list.length" max-height="380px">
        <div
          v-for="n in list"
          :key="n.notification_id"
          class="notify-item"
          :class="{ unread: n.status === 'SENT' }"
          @click="onOpen(n)"
        >
          <div class="notify-item-title">{{ n.title }}</div>
          <div class="notify-item-content">{{ n.content }}</div>
          <div class="notify-item-time">{{ formatTime(n.created_at) }}</div>
        </div>
      </el-scrollbar>
      <el-empty v-else description="暂无通知" :image-size="60" />

      <div class="notify-footer">
        <span class="notify-tip">查看通知不等于完成行动，请点击通知进入待办</span>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { notificationApi } from '../api/index.js'

const router = useRouter()
const list = ref([])
const pendingCount = ref(0)
let timer = null

async function loadCount() {
  try {
    const res = await notificationApi.pendingCount()
    pendingCount.value = res.data || 0
  } catch (e) { /* 静默，不打断页面 */ }
}

async function loadList() {
  try {
    const res = await notificationApi.list({ page: 1, page_size: 20 })
    list.value = res.data?.list || []
  } catch (e) {
    list.value = []
  }
}

// 点击通知 → 跳转待办行动入口（action_url），查看≠行动
function onOpen(n) {
  if (n.action_url) {
    router.push(n.action_url)
  }
  loadCount()
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  loadCount()
  // 30s 轮询未读数（PRD §14：通知中心轮询）
  timer = setInterval(loadCount, 30000)
})
onUnmounted(() => clearInterval(timer))

defineExpose({ loadCount })
</script>

<style scoped>
.notify-badge { margin: 0 4px; }
.bell-btn { font-size: 18px; }
.notify-panel { display: flex; flex-direction: column; }
.notify-header {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 8px; border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 4px;
}
.notify-title { font-weight: 600; font-size: 14px; }
.notify-item {
  padding: 10px 8px; cursor: pointer; border-radius: 6px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  transition: background .15s;
}
.notify-item:hover { background: var(--el-fill-color-light); }
.notify-item.unread .notify-item-title::before {
  content: ''; display: inline-block; width: 7px; height: 7px;
  background: var(--el-color-danger); border-radius: 50%;
  margin-right: 6px; vertical-align: middle;
}
.notify-item-title { font-size: 13px; font-weight: 600; color: var(--el-text-color-primary); }
.notify-item-content {
  font-size: 12px; color: var(--el-text-color-regular);
  margin: 3px 0; overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.notify-item-time { font-size: 11px; color: var(--el-text-color-secondary); }
.notify-footer {
  padding-top: 6px; border-top: 1px solid var(--el-border-color-lighter);
  text-align: center;
}
.notify-tip { font-size: 11px; color: var(--el-text-color-placeholder); }
</style>
