<template>
  <div class="consultation-page">
    <header class="page-heading">
      <div><div class="page-eyebrow">INTELLIGENT SERVICE / 智能服务</div><h1>工作遇到问题？我们来帮你。</h1><p>描述你遇到的 IT 问题，获取处理建议，或直接联系工程师。</p></div>
    </header>
    <section class="conversation" aria-label="智能客服会话"><ConsultationChat /></section>
  </div>
</template>
<script setup>
import ConsultationChat from '../components/ConsultationChat.vue'
</script>
<style scoped>
.page-heading { margin: 0 0 20px; }
h1 { font-size: clamp(22px, 2vw, 28px); font-weight: 700; letter-spacing: -.5px; line-height: 1.4; color: var(--el-text-color-primary); }
.page-heading p { font-size: 13px; margin-top: 10px; color: var(--el-text-color-secondary); }
.conversation { min-width: 0; }
@media (max-width: 767px) { h1 { font-size: 22px; } .page-heading p { font-size: 12px; line-height: 1.7; } }
</style>
