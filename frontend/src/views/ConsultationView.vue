<template>
  <div class="consultation-page">
    <header class="page-heading">
      <div><div class="page-eyebrow">INTELLIGENT SERVICE / 智能服务</div><h1>工作遇到问题？我们来帮你。</h1><p>描述你遇到的 IT 问题，获取处理建议，或直接联系工程师。</p></div>
      <el-button :icon="Plus" @click="$router.push({ path: '/employee', query: { tab: 'create' } })">直接提交工单</el-button>
    </header>
    <div class="support-layout">
      <section class="conversation" aria-label="智能客服会话"><ConsultationChat /></section>
      <aside class="support-sidebar" aria-label="服务说明">
        <section class="assistant-profile">
          <div class="profile-top"><span class="assistant-mark"><el-icon aria-hidden="true"><Service /></el-icon></span><span class="profile-label">你的办公好帮手</span></div>
          <h2>从一个问题开始，<br>一起找到解决办法。</h2>
          <p>电脑、网络、邮箱和办公软件，<br>有问题，随时来聊聊。</p>
          <RouterLink :to="{ path: '/employee', query: { tab: 'list' } }" class="ticket-shortcut"><el-icon aria-hidden="true"><Tickets /></el-icon>查看我的工单<el-icon aria-hidden="true"><ArrowRight /></el-icon></RouterLink>
        </section>
        <section class="support-guide">
          <h3>接下来会怎样</h3>
          <ol>
            <li><span>1</span><div><strong>描述问题，获取建议</strong><p>现象、报错和发生时间都很有帮助</p></div></li>
            <li><span>2</span><div><strong>需要时，由工程师接力</strong><p>携带对话记录，继续处理问题</p></div></li>
            <li><span>3</span><div><strong>提交工单，跟进进度</strong><p>确认信息后，随时查看处理状态</p></div></li>
          </ol>
        </section>
        <section class="help-note"><el-icon aria-hidden="true"><InfoFilled /></el-icon><div><strong>让沟通更高效</strong><p>可以告诉我们已经尝试过哪些方法。请勿在对话中发送密码或验证码。</p></div></section>
      </aside>
    </div>
  </div>
</template>
<script setup>
import { Service, Plus, Tickets, InfoFilled, ArrowRight } from '@element-plus/icons-vue'
import ConsultationChat from '../components/ConsultationChat.vue'
</script>
<style scoped>
.page-heading { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin: 0 0 26px; }
h1 { font-size: clamp(22px, 2vw, 28px); font-weight: 700; letter-spacing: -.5px; line-height: 1.4; color: var(--el-text-color-primary); }
.page-heading p { font-size: 13px; margin-top: 10px; color: var(--el-text-color-secondary); }
.page-heading > .el-button { flex-shrink: 0; }
.support-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 24px; align-items: start; }
.support-sidebar { display: grid; gap: 18px; }
.assistant-profile, .support-guide { border: 1px solid var(--el-border-color-lighter); border-radius: 16px; background: var(--el-bg-color); padding: 24px; box-shadow: var(--desk-shadow); }
.assistant-profile { background: linear-gradient(140deg, var(--el-color-primary-light-9), var(--el-bg-color) 75%); }
.profile-top { display: flex; align-items: center; gap: 12px; }
.assistant-mark { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; background: #2563eb; color: white; font-size: 22px; }
.profile-label { font-size: 12px; color: var(--el-text-color-secondary); }
h2 { font-size: 20px; line-height: 1.6; letter-spacing: -.4px; margin: 20px 0 12px; }
.assistant-profile p { font-size: 12px; line-height: 1.9; color: var(--el-text-color-secondary); }
.ticket-shortcut { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--el-color-primary); text-decoration: none; margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--el-border-color-lighter); }
.ticket-shortcut .el-icon:last-child { margin-left: auto; }
h3 { font-size: 15px; margin: 0 0 25px; }
ol { list-style: none; padding: 0; margin: 0; }
li { display: flex; position: relative; gap: 12px; padding-bottom: 25px; }
li:not(:last-child)::before { content: ''; position: absolute; width: 1px; top: 24px; left: 11px; bottom: 0; background: var(--el-border-color-lighter); }
li:last-child { padding-bottom: 0; }
li > span { display: grid; place-items: center; width: 24px; height: 24px; flex-shrink: 0; border-radius: 50%; background: var(--el-fill-color); color: var(--el-text-color-secondary); font-size: 11px; }
li:first-child > span { background: #2563eb; color: white; }
li strong { font-size: 12px; font-weight: 600; }
li p { margin-top: 5px; font-size: 11px; line-height: 1.7; color: var(--el-text-color-secondary); }
.help-note { display: flex; gap: 10px; padding: 20px; background: var(--el-color-primary-light-9); border: 1px solid var(--el-color-primary-light-8); border-radius: 14px; }
.help-note > .el-icon { flex-shrink: 0; color: var(--el-color-primary); margin-top: 3px; }
.help-note strong { font-size: 12px; }
.help-note p { margin-top: 8px; font-size: 12px; line-height: 1.8; color: var(--el-text-color-regular); }
.conversation { min-width: 0; }
@media (max-width: 1199px) { .support-layout { grid-template-columns: minmax(0, 1fr); } .support-sidebar { display: none; } }
@media (max-width: 767px) { .page-heading { flex-wrap: wrap; gap: 14px; margin-bottom: 20px; } h1 { font-size: 22px; } .page-heading p { font-size: 12px; line-height: 1.7; } }
</style>
