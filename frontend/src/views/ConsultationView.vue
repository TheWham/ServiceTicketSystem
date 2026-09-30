<template>
  <div class="consultation-page">
    <div class="page-head">
      <div><p class="page-eyebrow">服务支持</p><h2>智能客服</h2></div>
      <p>说说你遇到的问题，我们一起找到下一步。</p>
    </div>
    <!-- 聊天实现已抽为组件,与 App.vue 全局抽屉共用同一份(PRD 8.1 咨询入口) -->
    <ConsultationChat />
  </div>
</template>

<script setup>
import ConsultationChat from '../components/ConsultationChat.vue'
</script>

<style scoped>
.consultation-page { max-width: 1040px; margin: 0 auto; min-width: 0; }
.page-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 12px; padding-bottom: 20px; }
.page-head h2 { margin: 0; font-size: 24px; font-weight: 600; color: var(--el-text-color-primary); }
.page-head p { margin: 0; font-size: 13px; line-height: 1.7; color: var(--el-text-color-secondary); }
.page-head .page-eyebrow { margin-bottom: 6px; font-size: 12px; color: var(--el-color-primary); }
</style>
