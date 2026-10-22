<template>
  <div class="consultation-page">
    <header class="page-heading">
      <div class="heading-row">
        <div class="heading-title-group">
          <span class="page-eyebrow">INTELLIGENT SERVICE / 智能服务</span>
          <h1>工作遇到问题？我们来帮你。</h1>
        </div>
        <p>描述你遇到的 IT 问题，获取处理建议，或直接联系工程师。</p>
      </div>
    </header>
    <section class="conversation" aria-label="智能客服会话"><ConsultationChat /></section>
  </div>
</template>
<script setup>
import ConsultationChat from '../components/ConsultationChat.vue'
</script>
<style scoped>
.consultation-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  width: 100%;
  max-width: 100%;
}
.page-heading {
  margin: 0 0 8px;
  flex-shrink: 0;
}
.heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.heading-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-eyebrow {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  letter-spacing: 1.2px;
  color: var(--el-color-primary);
  font-weight: 700;
  background: var(--el-color-primary-light-9);
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}
h1 {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -.2px;
  line-height: 1.3;
  color: var(--el-text-color-primary);
  margin: 0;
  white-space: nowrap;
}
.page-heading p {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0;
  line-height: 1.4;
}
.conversation {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
@media (max-width: 767px) {
  .page-heading { margin: 0 0 6px; }
  .heading-row { flex-direction: column; align-items: flex-start; gap: 3px; }
  .heading-title-group { gap: 6px; }
  h1 { font-size: 14px; }
  .page-heading p { font-size: 11px; }
}
</style>
