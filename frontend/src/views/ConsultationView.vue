<template>
  <div class="consultation-page">
    <!-- 聊天实现已抽为组件,与 App.vue 全局抽屉共用同一份(PRD 8.1 咨询入口) -->
    <ConsultationChat />
  </div>
</template>

<script setup>
import ConsultationChat from '../components/ConsultationChat.vue'
</script>

<style scoped>
.consultation-page { max-width: 980px; }
</style>
