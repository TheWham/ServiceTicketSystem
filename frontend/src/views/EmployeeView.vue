<template>
  <div class="employee-view">
    <div class="page-head"><div><span class="page-eyebrow">EMPLOYEE SERVICE DESK</span><h1 class="page-title">{{ tab === 'list' ? '我的工单' : editingTicket ? '重新编辑工单' : '提交工单' }}</h1><p class="page-sub">{{ tab === 'list' ? '查看处理进度，补充问题信息，确认解决结果' : editingTicket ? '修改已提交的内容，保存后沿用原工单计时' : '告诉我们您遇到的问题，我们会安排合适的工程师处理' }}</p></div><el-button v-if="tab === 'list'" :icon="Refresh" :loading="listLoading" @click="loadTickets">刷新工单</el-button></div>
    <div class="support-entry">
      <div><strong>遇到 IT 问题？先问问智能客服</strong><span>描述问题，获取排查建议，也可以转接人工。</span></div>
      <el-button type="primary" plain @click="$router.push('/consultation')">开始咨询 →</el-button>
    </div>
    <!-- ===== 顶部 Tabs ===== -->
    <el-tabs v-model="tab" class="view-tabs">
      <el-tab-pane name="create">
        <template #label>
          <el-icon style="vertical-align:-2px;margin-right:4px"><EditPen /></el-icon>{{ editingTicket ? '重新编辑' : '提交工单' }}
        </template>
      </el-tab-pane>
      <el-tab-pane name="list">
        <template #label>
          <el-icon style="vertical-align:-2px;margin-right:4px"><List /></el-icon>我的工单
          <el-badge :value="total" :max="99" class="tab-badge" />
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- ===== 提单表单 ===== -->
    <div v-if="tab === 'create'" class="create-layout">
    <el-card shadow="never" class="panel form-panel">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">{{ editingTicket ? `重新编辑 · ${editingTicket.ticket_id}` : '提交新工单' }}</span>
        </div>
      </template>

      <el-alert v-if="editingTicket" title="问题类型不可修改；保存后保留原提交时间和处理进度，工单不会重新计时。" type="info" show-icon :closable="false" class="draft-alert" />
      <div v-if="!editingTicket && (consultationSession || appliedSession)" class="consultation-origin">
        <div class="origin-heading"><el-icon aria-hidden="true"><ChatDotRound /></el-icon><strong>{{ appliedSession ? '已关联咨询内容' : '来自咨询的工单' }}</strong></div>
        <p v-if="appliedSession">已关联咨询 {{ appliedSession }}。您可以继续修改表单，确认后再提交。</p>
        <p v-if="prefillLoading" role="status">正在读取咨询内容，您也可以直接填写表单。</p>
        <p v-else-if="prefillError" class="origin-error">{{ prefillError }}。您仍可直接填写并提交工单。</p>
        <p v-else-if="prefillDraft && !prefillDraft.convert_allowed">{{ prefillDraft.status === 'CONVERTED_TO_TICKET' ? '该咨询已转为工单' : '当前咨询状态不支持转为工单' }}，您仍可直接提交新工单。</p>
        <p v-else-if="prefillDraft && appliedSession !== consultationSession">咨询内容已就绪。点击填入空白内容并关联咨询，现有内容会保留。</p>
        <div class="origin-actions"><el-button v-if="prefillDraft?.convert_allowed && appliedSession !== consultationSession" type="primary" plain :disabled="categoryLoading || prefillLoading || submitting" @click="applyConsultationPrefill">填入并关联咨询</el-button><el-button v-if="prefillError" :loading="prefillLoading" @click="loadConsultationPrefill">重试读取</el-button></div>
      </div>
      <!-- 草稿提示 -->
      <el-alert
        v-if="draftBanner && !editingTicket"
        type="warning"
        :closable="false"
        class="draft-alert"
      >
        <template #title>
          检测到未提交的草稿，
          <el-link type="primary" @click="restoreDraft">点击恢复</el-link>
          <el-link type="info" style="margin-left:12px" @click="clearDraft">忽略</el-link>
        </template>
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        :disabled="submitting || editPhotoLoading"
        label-position="top"
        class="ticket-form"
      >
        <section class="form-section"><div class="section-heading"><span class="section-number">01</span><div><h2>问题信息</h2><p>清楚描述现象与影响，便于工程师判断和处理。</p></div></div>
        <el-alert v-if="categoryError && !editingTicket" :title="categoryError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="loadCategories">重新加载分类</el-button></el-alert>
        <!-- 工单标题 -->
        <el-form-item prop="title">
          <template #label>
            工单标题
          </template>
          <el-input
            v-model="form.title"
            maxlength="100"
            show-word-limit
            placeholder="一句话概括问题，如：市场部打印机无法连接"
            clearable
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 工单性质 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="nature" label="工单性质">
              <el-radio-group v-model="form.nature" :disabled="!!editingTicket">
                <el-radio-button v-for="n in natures" :key="n.value" :value="n.value">{{ n.label }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <!-- 末级分类 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="category_id" label="问题类型（分类）">
              <el-input v-if="editingTicket" :model-value="ticketTypeLabel(editingTicket)" readonly aria-label="问题类型（不可修改）" />
              <el-select v-else :loading="categoryLoading" v-model="form.category_id" placeholder="选择末级分类" style="width:100%" filterable>
                <el-option v-for="c in filteredCategories" :key="c.categoryId" :value="c.categoryId" :label="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 问题描述 -->
        <el-form-item prop="description">
          <template #label>
            问题描述
          </template>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="5000"
            show-word-limit
            placeholder="请详细描述问题：何时开始、报错原文、已尝试的操作..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 影响情况 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="impact_description">
              <template #label>
                影响情况
              </template>
              <el-input v-model="form.impact_description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="影响了哪些人/业务？如：本人无法打印 / 全部门网络中断" />
            </el-form-item>
          </el-col>

          <!-- 紧急说明 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="urgency_description">
              <template #label>
                紧急说明
              </template>
              <el-input v-model="form.urgency_description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="为什么紧急？如：下午有重要会议需投屏" />
            </el-form-item>
          </el-col>
        </el-row>

        </section>
        <section class="form-section"><div class="section-heading"><span class="section-number">02</span><div><h2>位置与联系信息</h2><p>选填，帮助工程师联系您并找到相关设备。</p></div></div>
        <el-row :gutter="16">
          <!-- 位置（选填） -->
          <el-col :xs="24" :sm="12">
            <el-form-item label="位置">
              <el-input v-model="form.location" maxlength="200" placeholder="如：3号楼 502 室（选填）" />
            </el-form-item>
          </el-col>
          <!-- 本次联系方式（选填） -->
          <el-col :xs="24" :sm="12">
            <el-form-item label="本次联系方式">
              <el-input v-model="form.contact" maxlength="64" placeholder="手机或座机（选填）" />
            </el-form-item>
          </el-col>
          <!-- 资产编号（选填） -->
          <el-col :xs="24" :sm="12">
            <el-form-item label="资产编号">
              <el-input v-model="form.asset_id" maxlength="64" placeholder="如 PC-2024-001（选填）" />
            </el-form-item>
          </el-col>
        </el-row>

        </section>
        <section class="form-section"><div class="section-heading"><span class="section-number">03</span><div><h2>照片附件</h2><p>选填，可上传报错截图或设备照片，帮助我们了解现场。</p></div></div>
        <!-- 照片附件（选填，最多 3 张；提交后与工单绑定，工程师/主管可见） -->
        <el-form-item label="照片附件">
          <div class="photo-upload">
            <el-upload
              v-model:file-list="photoList"
              list-type="picture-card"
              accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
              :limit="3"
              :disabled="submitting || editPhotoLoading"
              :http-request="uploadPhoto"
              :before-upload="checkPhoto"
              :on-remove="removePhoto"
              :on-exceed="() => ElMessage.warning('最多上传 3 张照片')"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
            <div class="upload-tip">支持 jpg/png/gif/webp/bmp，单张不超过 20MB，最多 3 张（选填）</div>
          </div>
        </el-form-item>

        </section>
        <el-alert v-if="submitError" :title="submitError" type="error" show-icon :closable="false" class="page-error" />
        <!-- 提交区 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="!!submitHint"
            @click="submitTicket"
          >
            {{ editingTicket ? (submitting ? '保存中...' : '保存修改') : (submitting ? '提交中...' : '提交工单') }}
          </el-button>
          <el-button v-if="editingTicket" size="large" :disabled="submitting || photoUploading || editPhotoLoading" @click="cancelEdit">取消编辑</el-button>
          <el-text v-if="submitHint" type="warning" size="small" style="margin-left:16px">
            {{ submitHint }}
          </el-text>
          <el-text v-if="draftSaved && !editingTicket" type="success" size="small" style="margin-left:16px">
            <el-icon style="vertical-align:-2px"><SuccessFilled /></el-icon>
            草稿已自动保存 {{ draftTime }}
          </el-text>
        </el-form-item>
      </el-form>
    </el-card>
    <aside class="service-guide"><el-card shadow="never"><div class="guide-heading"><el-icon aria-hidden="true"><Service /></el-icon><h2>让处理更顺畅</h2></div><p>完整的信息能帮助工程师更快理解问题。</p><ol class="guide-steps"><li><strong>描述发生了什么</strong><span>写明出现时间、报错原文，以及您尝试过的操作。</span></li><li><strong>说明业务影响</strong><span>告知受影响的人员和工作，以及需要完成的时间。</span></li><li><strong>关注工单进展</strong><span>提交后在「我的工单」查看进度，并在处理完成后验收。</span></li></ol><div class="guide-note"><el-icon aria-hidden="true"><InfoFilled /></el-icon><span>请勿在描述或截图中提供密码、验证码等敏感信息。</span></div></el-card></aside>
    </div>

    <!-- ===== 我的工单列表 ===== -->
    <el-card v-if="tab === 'list'" shadow="never" class="panel">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">我的工单</span>
          <div class="list-filters"><label class="filter-label" for="employee-page-search">本页搜索</label><el-input id="employee-page-search" v-model="pageSearch" :prefix-icon="Search" placeholder="工单号或标题" clearable class="page-search" /><label class="filter-label" for="employee-status-filter">状态</label>
          <el-select
            id="employee-status-filter"
            v-model="filter.status"
            placeholder="全部状态"
            clearable
            style="width: 160px"
            @change="applyFilters"
          >
            <el-option v-for="s in statuses" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select></div>
        </div>
      </template>

      <el-alert v-if="createdTicketId" type="success" show-icon :closable="false" class="page-error"><template #title>工单 {{ createdTicketId }} 已提交</template><el-button link type="primary" @click="openDetail({ ticket_id: createdTicketId })">查看工单</el-button></el-alert>
      <p class="scope-note">统计范围：当前页已加载 {{ tickets.length }} 张工单；符合状态筛选的工单共 {{ total }} 张。本页搜索仅检索当前页。</p>
      <el-alert v-if="listError" :title="listError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="loadTickets">重新加载</el-button></el-alert>
      <!-- 当前页统计 -->
      <div class="stat-row">
        <div v-for="s in listStats" :key="s.label" class="stat-card">
          <div class="stat-icon" :class="s.tone">
            <el-icon :size="18"><component :is="s.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <div v-if="listLoading" class="list-loading" role="status"><el-skeleton :rows="4" animated /><span>正在加载工单…</span></div>
      <el-empty v-else-if="!listError && displayedTickets.length === 0" :description="pageSearch.trim() ? '当前页没有匹配的工单' : '当前筛选下暂无工单'" />

      <div v-else-if="!listError" class="ticket-list">
        <el-card
          v-for="t in displayedTickets"
          :key="t.ticket_id"
          shadow="hover"
          class="ticket-card"
          role="button"
          tabindex="0"
          :aria-label="`查看工单：${t.title}，${statusLabel(t.status)}`"
          @keydown.enter="openDetail(t)"
          @keydown.space.prevent="openDetail(t)"
          @click="openDetail(t)"
        >
          <div class="ticket-header">
            <span class="ticket-id">{{ t.ticket_id }}</span>
            <el-tag :type="statusTagType(t.status)" size="small">{{ statusLabel(t.status) }}</el-tag>
            <el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ priorityLabel(t.priority) }}</el-tag>
          </div>
          <div class="ticket-title">{{ t.title }}</div>
          <div class="ticket-meta">
            <el-tag size="small" type="info" effect="plain">{{ ticketTypeLabel(t) }}</el-tag>
            <span v-if="t.assignee_name">处理人：{{ t.assignee_name }}</span>
            <span>{{ formatTime(t.created_at) }}</span>
            <SlaBadge :ticket-id="t.ticket_id" mode="card" />
          </div>
        </el-card>
      </div>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="loadTickets"
      />
    </el-card>

    <!-- ===== 工单详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="`工单详情 · ${detailTicket?.ticket_id || ''}`"
      width="min(760px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="detailLoading" class="detail-loading" role="status"><el-skeleton :rows="5" animated /><p>正在加载工单详情…</p></div>
      <el-alert v-if="detailError" :title="detailError" type="error" :closable="false" show-icon><el-button link type="primary" @click="openDetail({ ticket_id: detailId })">重新加载</el-button></el-alert>
      <div v-if="detailTicket && !detailLoading && !detailError" class="ticket-detail-content">
        <div class="detail-summary"><h2>{{ detailTicket.title }}</h2><div><el-tag :type="statusTagType(detailTicket.status)">{{ statusLabel(detailTicket.status) }}</el-tag><el-tag :type="priorityTagType(detailTicket.priority)" effect="plain">{{ priorityLabel(detailTicket.priority) }}优先级</el-tag><span>处理人：{{ detailTicket.assignee_name || '等待分配' }}</span></div></div>
        <el-descriptions :column="detailColumns" border class="detail-desc">
          <el-descriptions-item label="标题" :span="detailColumns">{{ detailTicket.title }}</el-descriptions-item>
          <el-descriptions-item label="工单性质">{{ ticketNatureLabel(detailTicket.nature) }}</el-descriptions-item>
          <el-descriptions-item label="问题类型">{{ ticketTypeLabel(detailTicket) }}</el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTagType(detailTicket.priority)" size="small">{{ priorityLabel(detailTicket.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detailTicket.status)" size="small">{{ statusLabel(detailTicket.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提单人">{{ detailTicket.creator_name }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ detailTicket.assignee_name || '未分配' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detailTicket.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="detailTicket.location" label="位置">{{ detailTicket.location }}</el-descriptions-item>
          <el-descriptions-item v-if="detailTicket.contact" label="本次联系方式">{{ detailTicket.contact }}</el-descriptions-item>
          <el-descriptions-item v-if="detailTicket.asset_id" label="资产编号">{{ detailTicket.asset_id }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="detailColumns">{{ detailTicket.description }}</el-descriptions-item>
          <el-descriptions-item label="影响情况" :span="detailColumns">{{ detailTicket.impact_description }}</el-descriptions-item>
          <el-descriptions-item label="紧急说明" :span="detailColumns">{{ detailTicket.urgency_description }}</el-descriptions-item>
          <el-descriptions-item v-if="detailPhotos.length" label="照片附件" :span="detailColumns">
            <el-image
              v-for="(u, i) in detailPhotos"
              :key="i"
              :src="u"
              :preview-src-list="detailPhotos"
              :initial-index="i"
              fit="cover"
              preview-teleported
              style="width:96px;height:96px;margin-right:8px;border-radius:4px"
            />
          </el-descriptions-item>
        </el-descriptions>

        <!-- SLA 计时 -->
        <SlaTimer :ticket-id="detailTicket.ticket_id" />

        <el-alert v-if="detailTicket.status === 'CANCELLED'" title="工单已撤回" description="本工单已作废并停止计时，内容和流转记录保留存档，平台管理员仍可查看。" type="info" show-icon :closable="false" />
        <section v-else-if="detailTicket.creator_id === userStore.userId" class="ticket-detail-actions" aria-label="工单操作">
          <div class="detail-action-copy"><h3>工单操作</h3><p>修改内容不重置计时；不再需要处理时，可撤回工单。</p></div>
          <div class="detail-action-buttons">
            <el-button type="primary" :icon="EditPen" :disabled="!!editingTicket || submitting || photoUploading || withdrawing" @click="canEdit(detailTicket) ? openEdit(detailTicket) : startEdit(detailTicket)">
              {{ canEdit(detailTicket) ? (detailTicket.status === 'PENDING_SUPPLEMENT' ? '补充信息并重新提交' : '编辑并重新提交') : '重新编辑' }}
            </el-button>
            <el-button v-if="canWithdrawTicket(detailTicket, userStore.userId)" type="danger" plain :loading="withdrawing" :disabled="!!editingTicket || submitting || photoUploading" @click="withdrawTicket(detailTicket)">撤回工单</el-button>
          </div>
          <el-alert v-if="withdrawError" :title="withdrawError" type="error" show-icon :closable="false" />
        </section>

        <!-- 验收操作 -->
        <el-card v-if="detailTicket.status === 'PENDING_ACCEPTANCE'" shadow="never" class="action-card">
          <template #header><span class="action-title">验收工单</span></template>
          <el-space>
            <el-button type="success" :icon="CircleCheck" @click="acceptTicket(detailTicket)">
              确认解决
            </el-button>
          </el-space>
          <el-divider />
          <div class="reject-area">
            <el-input
              v-model="rejectReason"
              placeholder="请输入驳回原因"
              maxlength="200"
              show-word-limit
            />
            <el-button type="danger" :icon="CircleClose" @click="rejectTicket(detailTicket)">
              驳回
            </el-button>
          </div>
          <el-text v-if="rejectError" type="danger" size="small">{{ rejectError }}</el-text>
        </el-card>

        <!-- 满意度评价 -->
        <el-card
          v-if="detailTicket.status === 'COMPLETED' && !detailTicket.rating_score"
          shadow="never"
          class="action-card"
        >
          <template #header><span class="action-title">满意度评价</span></template>
          <el-rate v-model="ratingScore" :max="5" size="large" />
          <el-input
            v-model="ratingComment"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="补充评价（选填，≤200 字）"
            style="margin-top:12px"
          />
          <el-button
            type="primary"
            :disabled="!ratingScore"
            style="margin-top:12px"
            @click="submitRating(detailTicket)"
          >
            提交评价
          </el-button>
        </el-card>

        <el-alert
          v-if="detailTicket.rating_score"
          type="success"
          :closable="false"
          style="margin-bottom:16px"
        >
          <template #title>
            <el-rate :model-value="detailTicket.rating_score" :max="5" disabled size="small" />
            <span style="margin-left:8px">{{ detailTicket.rating_comment || '未留言' }}</span>
          </template>
        </el-alert>

        <!-- 流转日志 -->
        <el-card shadow="never" class="flow-card">
          <template #header><span class="action-title">流转记录</span></template>
          <el-empty v-if="detailFlows.length === 0" description="暂无记录" :image-size="60" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="f in detailFlows"
              :key="f.transition_id"
              :timestamp="formatTime(f.occurred_at)"
              :type="flowTimelineType(f.to_status)"
            >
              <div class="flow-content">
                <el-tag size="small" effect="plain">{{ statusLabel(f.to_status || f.from_status) }}</el-tag>
                <span class="flow-operator">{{ f.operator_name || operatorLabel(f.operator_id) }}</span>
                <span v-if="f.reason" class="flow-remark">{{ f.reason }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </div>
    </el-dialog>

    <!-- ===== 编辑工单弹窗 ===== -->
    <el-dialog
      v-model="editVisible"
      :title="`编辑工单 · ${editId}`"
      width="min(720px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="editForm" label-position="top" class="ticket-form">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="工单性质" required>
              <el-radio-group v-model="editForm.nature">
                <el-radio-button v-for="n in natures" :key="n.value" :value="n.value">{{ n.label }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="问题分类" required>
              <el-select :loading="categoryLoading" v-model="editForm.category_id" placeholder="选择末级分类" style="width:100%" filterable>
                <el-option v-for="c in editCategories" :key="c.categoryId" :value="c.categoryId" :label="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="工单标题" required>
          <el-input v-model="editForm.title" maxlength="100" show-word-limit placeholder="一句话概括问题" clearable />
        </el-form-item>

        <el-form-item label="问题描述" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" maxlength="5000" show-word-limit placeholder="请详细描述问题" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="影响情况" required>
              <el-input v-model="editForm.impact_description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="影响了哪些人/业务？" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="紧急说明" required>
              <el-input v-model="editForm.urgency_description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="为什么紧急？" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :xs="24" :sm="8">
            <el-form-item label="位置">
              <el-input v-model="editForm.location" maxlength="200" placeholder="如：3号楼 502 室（选填）" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="本次联系方式">
              <el-input v-model="editForm.contact" maxlength="64" placeholder="手机或座机（选填）" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="资产编号">
              <el-input v-model="editForm.asset_id" maxlength="64" placeholder="如 PC-2024-001（选填）" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 照片附件：已有附件保留/删除 + 新上传；提交时全量对齐，最多 3 张 -->
        <el-form-item label="照片附件">
          <div class="photo-upload">
            <el-upload
              v-model:file-list="editPhotoList"
              list-type="picture-card"
              accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
              :limit="3"
              :http-request="uploadEditPhoto"
              :before-upload="checkPhoto"
              :on-remove="removeEditPhoto"
              :on-exceed="() => ElMessage.warning('最多上传 3 张照片')"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
            <div class="upload-tip">删除的照片提交后不再保留；支持 jpg/png/gif/webp/bmp，单张不超过 20MB，最多 3 张</div>
          </div>
        </el-form-item>
      </el-form>
      <el-alert v-if="editError" :title="editError" type="error" show-icon :closable="false" class="page-error" />
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="submitEdit">
          {{ editSaving ? '提交中...' : '保存并提交' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  EditPen, List, WarningFilled, SuccessFilled, CircleCheck, CircleClose, Plus, Clock, Loading, Finished, Refresh, Search, Service, InfoFilled, ChatDotRound
} from '@element-plus/icons-vue'
import { ticketApi, draftApi, categoryApi, attachmentApi } from '../api/index.js'
import { consultationApi } from '../api/consultation.js'
import { loadPhotoUrls, revokePhotoUrls } from '../utils/attachmentPhotos.js'
import { ticketToForm, ticketTypeLabel, ticketNatureLabel, editableTicketPayload, canWithdrawTicket } from '../utils/ticketEditing.js'
import { useUserStore } from '../stores/user.js'
import SlaBadge from '../components/SlaBadge.vue'
import SlaTimer from '../components/SlaTimer.vue'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const tab = computed({
  get: () => ['create', 'list'].includes(route.query.tab) ? route.query.tab : route.query.ticket ? 'list' : 'create',
  set: value => router.push({ path: route.path, query: { ...route.query, tab: value } })
})
// 末级分类从后端动态加载（PRD §10.1 分类目录）
const categories = ref([])
const categoryLoading = ref(false)
const categoryError = ref('')
// 按当前工单性质过滤末级分类（PRD §10.1：分类目录按 nature 分组，SPEC 字段为 nature）
const filteredCategories = computed(() => categories.value.filter(c => (c.nature || c.ticketNature) === form.value.nature))
const natures = [
  { value: 'INCIDENT', label: '故障报修' },
  { value: 'SERVICE_REQUEST', label: '服务申请' }
]

const form = ref({
  nature: 'INCIDENT', category_id: '', title: '', description: '',
  impact_description: '', urgency_description: '', location: '', contact: '', asset_id: ''
})
const editingTicket = ref(null)
const editPhotoLoading = ref(false)
let createFormBackup = null
let editPhotoRequest = 0
let editPhotoUrls = []
// Consultation content is fetched separately and only applied on explicit user action.
const consultationSession = computed(() => route.query.from === 'consultation' && typeof route.query.session === 'string' ? route.query.session : '')
const prefillLoading = ref(false)
const prefillError = ref('')
const prefillDraft = ref(null)
const appliedSession = ref('')
let prefillRequest = 0

function mapConsultationDraft(draft, leaves) {
  if (draft?.convert_allowed !== true) return null
  const category = leaves.find(item => item.categoryId === draft.category_id && ['INCIDENT', 'SERVICE_REQUEST'].includes(item.nature || item.ticketNature))
  return {
    title: String(draft.title || '').slice(0, 100),
    description: String(draft.description || draft.summary || '').slice(0, 5000),
    category_id: category?.categoryId || '',
    nature: category ? category.nature || category.ticketNature : ''
  }
}

function fillEmptyDraftFields(current, prefill) {
  const result = { ...current }
  let changed = false
  for (const field of ['title', 'description', 'category_id']) {
    if (!String(current[field] || '').trim() && prefill[field]) {
      result[field] = prefill[field]
      changed = true
      if (field === 'category_id' && prefill.nature) result.nature = prefill.nature
    }
  }
  return { form: result, changed }
}

async function loadConsultationPrefill() {
  const session = consultationSession.value
  const request = ++prefillRequest
  prefillDraft.value = null
  prefillError.value = ''
  prefillLoading.value = !!session
  if (!session) return
  try {
    const draft = await consultationApi.ticketDraft(session)
    if (request !== prefillRequest || consultationSession.value !== session) return
    if (!draft || draft.session_id !== session) throw new Error('咨询内容与当前咨询不匹配，请重新读取')
    prefillDraft.value = draft
  } catch (error) {
    if (request === prefillRequest) prefillError.value = error.message || '咨询内容读取失败'
  } finally {
    if (request === prefillRequest) prefillLoading.value = false
  }
}

function applyConsultationPrefill() {
  if (prefillLoading.value || categoryLoading.value || submitting.value) return
  const draft = prefillDraft.value
  const session = consultationSession.value
  if (!session || draft?.session_id !== session) return
  const mapped = mapConsultationDraft(draft, categories.value)
  if (!mapped) return
  const result = fillEmptyDraftFields(form.value, mapped)
  if (result.changed) form.value = result.form
  else ElMessage.info('已关联咨询，保留现有内容')
  appliedSession.value = session
  formToken.value = genClientToken()
}

const formRef = ref(null)
const submitting = ref(false)
const submitError = ref('')
const createdTicketId = ref('')
const draftBanner = ref(false)
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// Element Plus 表单校验规则（保留原有校验语义）
const formRules = {
  nature: [{ required: true, message: '请选择工单性质', trigger: 'change' }],
  category_id: [{ required: true, message: '请选择问题分类', trigger: 'change' }],
  title: [
    { required: true, message: '请填写工单标题', trigger: 'blur' },
    { min: 1, max: 100, message: '工单标题 1~100 个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请填写问题描述', trigger: 'blur' },
    { max: 5000, message: '问题描述不能超过 5000 个字符', trigger: 'blur' }
  ],
  impact_description: [
    { required: true, message: '请填写影响情况（接单时供工程师确认优先级）', trigger: 'blur' },
    { max: 500, message: '影响情况不能超过 500 个字符', trigger: 'blur' }
  ],
  urgency_description: [
    { required: true, message: '请填写紧急说明', trigger: 'blur' },
    { max: 500, message: '紧急说明不能超过 500 个字符', trigger: 'blur' }
  ]
}

// 工单列表
const tickets = ref([])
const listLoading = ref(false)
const listError = ref('')
const pageSearch = ref('')
const displayedTickets = computed(() => {
  const keyword = pageSearch.value.trim().toLocaleLowerCase()
  if (!keyword) return tickets.value
  return tickets.value.filter(ticket => `${ticket.ticket_id || ''} ${ticket.title || ''}`.toLocaleLowerCase().includes(keyword))
})
const total = ref(0)
const page = ref(1)
const pageSize = 10

// 状态筛选项（英文枚举，显示用 statusLabel 转中文）
const statuses = ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE', 'COMPLETED', 'CANCELLED', 'CLOSED']

// 我的工单统计条（简洁商务）
const listStats = computed(() => {
  const t = tickets.value
  const count = (s) => t.filter(x => x.status === s).length
  return [
    { label: '当前页待处理', value: count('NEW') + count('ASSIGNED'), icon: Clock, tone: 'warning' },
    { label: '当前页处理中', value: count('IN_PROGRESS') + count('PENDING_EXTERNAL') + count('PENDING_SUPPLEMENT'), icon: Loading, tone: 'primary' },
    { label: '当前页待验收', value: count('PENDING_ACCEPTANCE'), icon: CircleCheck, tone: 'primary' },
    { label: '当前页已完成', value: count('COMPLETED'), icon: Finished, tone: 'success' }
  ]
})
const filter = ref({ status: '' })

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detailId = ref('')
const rejectReason = ref('')
const rejectError = ref('')
const ratingScore = ref(0)
const ratingComment = ref('')
const detailPhotos = ref([])
const detailColumns = ref(2)
function resizeDetail() { detailColumns.value = window.innerWidth <= 540 ? 1 : 2 }
const withdrawing = ref(false)
const withdrawError = ref('')

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

// 操作人兜底：流转记录里 SYSTEM（系统自动路由）无用户档案，显示为「系统」
function operatorLabel(operatorId) { return operatorId === 'SYSTEM' ? '系统' : (operatorId || '—') }

function disablePastDate(time) { return time.getTime() < Date.now() - 86400000 }

// 状态英文枚举 → 中文标签 + 颜色（PRD §9.2 九态）
const STATUS_LABEL = {
  NEW: '新建', ASSIGNED: '已分配', IN_PROGRESS: '处理中',
  PENDING_SUPPLEMENT: '待补充', PENDING_EXTERNAL: '外部等待',
  PENDING_ACCEPTANCE: '待验收', COMPLETED: '已完成',
  CANCELLED: '已撤回', CLOSED: '已关闭'
}
const STATUS_TYPE = {
  NEW: 'warning', ASSIGNED: 'primary', IN_PROGRESS: 'primary',
  PENDING_SUPPLEMENT: 'info', PENDING_EXTERNAL: 'info',
  PENDING_ACCEPTANCE: 'primary', COMPLETED: 'success',
  CANCELLED: 'info', CLOSED: 'info'
}
function statusLabel(s) { return STATUS_LABEL[s] || s }
function statusTagType(s) { return STATUS_TYPE[s] || 'info' }

// 优先级英文 → 中文 + 颜色
const PRIORITY_LABEL = { HIGH: '高', MEDIUM: '中', LOW: '低' }
const PRIORITY_TYPE = { HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' }
function priorityLabel(p) { return PRIORITY_LABEL[p] || p }
function priorityTagType(p) { return PRIORITY_TYPE[p] || 'info' }

function flowTimelineType(status) {
  const map = {
    COMPLETED: 'success', PENDING_ACCEPTANCE: 'primary', IN_PROGRESS: 'primary',
    NEW: 'warning', ASSIGNED: 'primary', CANCELLED: 'info', CLOSED: 'info'
  }
  return map[status] || 'primary'
}

// 未满足条件时的实时提示
const submitHint = computed(() => {
  if (submitting.value) return ''
  if (editPhotoLoading.value) return '正在加载原工单照片'
  if (photoUploading.value) return '请等待照片上传完成'
  const missing = []
  if (!form.value.category_id) missing.push('问题分类')
  const tLen = form.value.title.trim().length
  if (tLen === 0) missing.push('工单标题')
  else if (tLen > 100) missing.push('标题需在 100 字以内')
  const dLen = form.value.description.trim().length
  if (dLen === 0) missing.push('问题描述')
  if (!form.value.impact_description.trim()) missing.push('影响情况')
  if (!form.value.urgency_description.trim()) missing.push('紧急说明')
  if (!missing.length) return ''
  return '还差：' + missing.join('、')
})

// 兼容非安全上下文（crypto.randomUUID 在 http 非 localhost 下不可用）
function genClientToken() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'tk-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10)
}

// 幂等令牌：同一表单会话内保持不变，双击/重试只会命中后端幂等而不会重复建单
const formToken = ref('')
const lastSubmitAt = ref(0)

// ---- 照片附件上传（先传图拿 attachment_id，提交工单时随 attachments 字段绑定）----
const photoList = ref([])
const photoIds = ref([])
const photoRequests = ref(0)
const photoUploading = computed(() => photoRequests.value > 0 || photoList.value.some(file => file.status === 'ready' || file.status === 'uploading'))

async function startEdit(ticket) {
  if (editingTicket.value || submitting.value || photoUploading.value || withdrawing.value || ticket.status === 'CANCELLED' || ticket.creator_id !== userStore.userId) return
  clearTimeout(draftTimer)
  createFormBackup = {
    form: { ...form.value }, photoList: [...photoList.value], photoIds: [...photoIds.value],
    submitError: submitError.value
  }
  editingTicket.value = { ...ticket }
  form.value = ticketToForm(ticket)
  photoIds.value = [...(ticket.attachments || [])]
  photoList.value = photoIds.value.map((id, index) => ({
    uid: id, name: `原照片 ${index + 1}`, status: 'success', response: { attachment_id: id }
  }))
  submitError.value = ''
  detailVisible.value = false
  editPhotoLoading.value = true
  const request = ++editPhotoRequest
  const query = { ...route.query, tab: 'create' }
  delete query.ticket
  await router.push({ path: route.path, query })
  await nextTick()
  formRef.value?.clearValidate()
  try {
    for (const file of photoList.value) {
      const urls = await loadPhotoUrls([file.response.attachment_id])
      if (request !== editPhotoRequest) { revokePhotoUrls(urls); return }
      editPhotoUrls.push(...urls)
      file.url = urls[0] || ''
    }
  } finally {
    if (request === editPhotoRequest) editPhotoLoading.value = false
  }
}

function restoreCreateForm() {
  editPhotoRequest++
  revokePhotoUrls(editPhotoUrls)
  editPhotoUrls = []
  editPhotoLoading.value = false
  clearTimeout(draftTimer)
  if (createFormBackup) {
    form.value = createFormBackup.form
    photoList.value = createFormBackup.photoList
    photoIds.value = createFormBackup.photoIds
    submitError.value = createFormBackup.submitError
  }
  editingTicket.value = null
  createFormBackup = null
  nextTick(() => formRef.value?.clearValidate())
}

function cancelEdit() {
  if (submitting.value || photoUploading.value || editPhotoLoading.value) return
  restoreCreateForm()
  tab.value = 'list'
}

async function saveEditedTicket() {
  const id = editingTicket.value.ticket_id
  submitting.value = true
  try {
    await ticketApi.edit(id, editableTicketPayload(form.value, photoIds.value))
    restoreCreateForm()
    ElMessage.success('修改已保存，工单计时保持不变')
    await router.push({ path: route.path, query: { ...route.query, tab: 'list' } })
    await loadTickets()
    await openDetail({ ticket_id: id })
  } catch (error) {
    submitError.value = '保存失败：' + (error.message || '请稍后重试')
  } finally {
    submitting.value = false
  }
}

function checkPhoto(file) {
  const okTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
  if (!okTypes.includes(file.type)) {
    ElMessage.error('仅支持图片格式（jpg/png/gif/webp/bmp）')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('单张照片不能超过 20MB')
    return false
  }
  return true
}

async function uploadPhoto({ file }) {
  const request = editPhotoRequest
  photoRequests.value++
  try {
    const res = await attachmentApi.upload(file)
    // 移除上传项或离开本次编辑后，迟到结果不能写入另一张表单。
    if (request !== editPhotoRequest || !photoList.value.some(item => item.uid === file.uid)) return
    if (editingTicket.value && createFormBackup?.photoIds.includes(res.data.attachment_id)) {
      throw new Error('该照片已用于未提交的新工单草稿，请选择其他照片')
    }
    if (!photoIds.value.includes(res.data.attachment_id)) photoIds.value.push(res.data.attachment_id)
    // Promise 结果交给 el-upload 写入 file.response，避免重复成功回调覆盖附件 ID。
    return res.data
  } catch (e) {
    ElMessage.error('照片上传失败：' + e.message)
    throw e
  } finally {
    photoRequests.value--
  }
}

function removePhoto(file) {
  const attId = file.response?.attachment_id
  if (!attId) return
  photoIds.value = photoIds.value.filter(id => id !== attId)
  // 编辑原照片只更新待保存集合，取消编辑时不会撤回原附件。
  if (editingTicket.value?.attachments?.includes(attId)) return
  attachmentApi.remove(attId).catch(() => {})
}

// 提交工单
async function submitTicket() {
  if (submitting.value || photoUploading.value || editPhotoLoading.value) return
  submitError.value = ''
  // PRD §3.2：防重复点击 Debounce 3 秒
  if (!editingTicket.value && Date.now() - lastSubmitAt.value < 3000) return

  // Element Plus 表单校验
  try {
    await formRef.value.validate()
  } catch (e) {
    nextTick(() => {
      const el = document.querySelector('.el-form-item.is-error')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
    return
  }

  if (editingTicket.value) return saveEditedTicket()
  if (!formToken.value) formToken.value = genClientToken()
  submitting.value = true
  lastSubmitAt.value = Date.now()
  try {
    const created = await ticketApi.create({
      nature: form.value.nature,
      category_id: form.value.category_id,
      title: form.value.title.trim(),
      description: form.value.description.trim(),
      impact_description: form.value.impact_description.trim(),
      urgency_description: form.value.urgency_description.trim(),
      location: form.value.location.trim() || null,
      contact: form.value.contact.trim() || null,
      asset_id: form.value.asset_id.trim() || null,
      attachments: photoIds.value.length ? photoIds.value : undefined,
      source_session_id: appliedSession.value || undefined,
      idempotency_key: formToken.value
    })
    form.value = {
      nature: 'INCIDENT', category_id: '', title: '', description: '',
      impact_description: '', urgency_description: '', location: '', contact: '', asset_id: ''
    }
    createdTicketId.value = created.data?.ticket_id || ''
    clearTimeout(draftTimer)
    photoList.value = []
    photoIds.value = []
    formToken.value = genClientToken()
    await draftApi.delete().catch(() => {})
    draftBanner.value = false
    draftSaved.value = false
    ElMessage.success('工单提交成功！')
    appliedSession.value = ''
    prefillDraft.value = null
    const nextQuery = { ...route.query, tab: 'list' }
    delete nextQuery.session
    delete nextQuery.from
    await router.push({ path: route.path, query: nextQuery })
    loadTickets()
  } catch (e) {
    submitError.value = '提交失败：' + (e.message || '请稍后重试')
  } finally {
    submitting.value = false
  }
}

// 草稿
async function saveDraft() {
  if (editingTicket.value) return
  await draftApi.save({
    nature: form.value.nature,
    category_id: form.value.category_id,
    title: form.value.title,
    description: form.value.description,
    impact_description: form.value.impact_description,
    urgency_description: form.value.urgency_description,
    location: form.value.location,
    contact: form.value.contact,
    asset_id: form.value.asset_id
  })
  draftSaved.value = true
  draftTime.value = new Date().toLocaleTimeString('zh-CN')
}

function restoreDraft() {
  draftApi.get().then(res => {
    if (res.data) {
      appliedSession.value = ''
      form.value = {
        nature: res.data.nature || 'INCIDENT',
        category_id: res.data.category_id || '',
        title: res.data.title || '',
        description: res.data.description || '',
        impact_description: res.data.impact_description || '',
        urgency_description: res.data.urgency_description || '',
        location: res.data.location || '',
        contact: res.data.contact || '',
        asset_id: res.data.asset_id || ''
      }
      draftBanner.value = false
    }
  }).catch(error => ElMessage.error(error.message || '草稿读取失败，请重试'))
}
function clearDraft() { draftApi.delete().catch(() => {}); draftBanner.value = false }

// 筛选变更返回第一页；刷新保留当前页。
function applyFilters() {
  page.value = 1
  pageSearch.value = ''
  loadTickets()
}

let listRequest = 0
// 加载工单列表
async function loadTickets() {
  const request = ++listRequest
  listLoading.value = true
  listError.value = ''
  try {
    const params = { creator_id: userStore.userId, page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    const res = await ticketApi.list(params)
    if (request !== listRequest) return
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) {
    if (request === listRequest) listError.value = e.message || '工单加载失败，请稍后重试'
  } finally {
    if (request === listRequest) listLoading.value = false
  }
}

// 查看详情
let detailRequest = 0
function invalidateDetailRequest() {
  detailRequest++
  detailLoading.value = false
  detailTicket.value = null
  detailError.value = ''
  revokePhotoUrls(detailPhotos.value)
  detailPhotos.value = []
}
watch(detailVisible, visible => { if (!visible) invalidateDetailRequest() }, { flush: 'sync' })

async function openDetail(ticket) {
  const request = ++detailRequest
  detailId.value = ticket.ticket_id
  detailTicket.value = null
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = ''
  withdrawError.value = ''
  try {
    const res = await ticketApi.detail(ticket.ticket_id)
    if (request !== detailRequest) return
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
    revokePhotoUrls(detailPhotos.value)
    const photos = await loadPhotoUrls(res.data.ticket.attachments)
    if (request !== detailRequest) { revokePhotoUrls(photos); return }
    detailPhotos.value = photos
    rejectReason.value = ''
    rejectError.value = ''
    ratingScore.value = 0
    ratingComment.value = ''
  } catch (e) {
    if (request === detailRequest) detailError.value = '详情加载失败：' + (e.message || '请稍后重试')
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}

async function withdrawTicket(ticket) {
  if (withdrawing.value || editingTicket.value || submitting.value || photoUploading.value || !canWithdrawTicket(ticket, userStore.userId)) return
  withdrawing.value = true
  withdrawError.value = ''
  try {
    try {
      await ElMessageBox.confirm('撤回后工单将作废并停止计时，工程师不再处理；内容和记录保留存档，您和平台管理员仍可查看。此操作不可恢复。', '确认撤回工单', {
        confirmButtonText: '确认撤回', cancelButtonText: '继续保留', type: 'warning',
        confirmButtonClass: 'el-button--danger'
      })
    } catch { return }
    await ticketApi.withdraw(ticket.ticket_id)
    ElMessage.success('工单已撤回，记录已保留')
    detailVisible.value = false
    await loadTickets()
    await openDetail({ ticket_id: ticket.ticket_id })
  } catch (error) {
    withdrawError.value = '撤回失败：' + (error.message || '请稍后重试')
  } finally {
    withdrawing.value = false
  }
}

// 验收通过
async function acceptTicket(t) {
  try {
    await ElMessageBox.confirm('确认此工单已解决？', '验收确认', {
      confirmButtonText: '确认解决',
      cancelButtonText: '再想想',
      type: 'success'
    })
  } catch { return }

  try {
    await ticketApi.action(t.ticket_id, { action: 'accept' })
    ElMessage.success('验收通过！')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// 驳回
async function rejectTicket(t) {
  rejectError.value = ''
  if (!rejectReason.value || !rejectReason.value.trim()) {
    rejectError.value = '请填写驳回原因'
    return
  }
  try {
    await ticketApi.action(t.ticket_id, { action: 'reject', remark: rejectReason.value })
    ElMessage.success('已驳回，工单退回处理中')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// 评价
async function submitRating(t) {
  try {
    await ticketApi.rating(t.ticket_id, { score: ratingScore.value, comment: ratingComment.value })
    ElMessage.success('评价成功！')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// ---- 编辑工单并重新提交（提单人；NEW/ASSIGNED/待补充 可编辑）----
const EDITABLE_STATUSES = ['NEW', 'ASSIGNED', 'PENDING_SUPPLEMENT']
function canEdit(t) { return !!t && EDITABLE_STATUSES.includes(t.status) }

const editVisible = ref(false)
const editSaving = ref(false)
const editError = ref('')
const editId = ref('')
const editForm = ref({
  nature: 'INCIDENT', category_id: '', title: '', description: '',
  impact_description: '', urgency_description: '', location: '', contact: '', asset_id: ''
})
const editCategories = computed(() => categories.value.filter(c => (c.nature || c.ticketNature) === editForm.value.nature))
const editPhotoList = ref([])

// 打开编辑弹窗：预填工单内容，拉取已绑定照片生成预览（保留 attachment_id 供全量对齐）
async function openEdit(t) {
  editId.value = t.ticket_id
  editForm.value = {
    nature: t.nature || 'INCIDENT',
    category_id: t.category_id || '',
    title: t.title || '',
    description: t.description || '',
    impact_description: t.impact_description || '',
    urgency_description: t.urgency_description || '',
    location: t.location || '',
    contact: t.contact || '',
    asset_id: t.asset_id || ''
  }
  editError.value = ''
  revokeEditPhotoUrls()
  editPhotoList.value = []
  editVisible.value = true
  const photos = []
  for (const id of t.attachments || []) {
    try {
      const blob = await attachmentApi.fetchBlob(id)
      photos.push({ name: id, url: URL.createObjectURL(blob), attachment_id: id })
    } catch (e) {
      console.error('[附件加载失败]', id, e?.message || e)
    }
  }
  if (editVisible.value) editPhotoList.value = photos
  else revokeEditPhotoUrls(photos)
}

function revokeEditPhotoUrls(list) {
  ;(list || editPhotoList.value).forEach(f => { if (f.url && f.url.startsWith('blob:')) URL.revokeObjectURL(f.url) })
}
watch(editVisible, visible => { if (!visible) revokeEditPhotoUrls() }, { flush: 'sync' })

async function uploadEditPhoto({ file, onSuccess, onError }) {
  try {
    const res = await attachmentApi.upload(file)
    onSuccess(res.data) // 挂到 file.response.attachment_id，提交时取回
  } catch (e) {
    onError(e)
    ElMessage.error('照片上传失败：' + e.message)
  }
}

function removeEditPhoto(file) {
  // 新上传未提交的草稿附件直接撤回；已绑定工单的附件在提交时由后端全量对齐撤回
  const attId = file.response?.attachment_id
  if (attId) attachmentApi.remove(attId).catch(() => {})
}

async function submitEdit() {
  if (editSaving.value) return
  editError.value = ''
  const f = editForm.value
  // 与后端同一口径的必填校验
  if (!f.category_id) { editError.value = '请选择问题分类'; return }
  if (!f.title.trim() || f.title.trim().length > 100) { editError.value = '工单标题需为 1~100 个字符'; return }
  if (!f.description.trim() || f.description.trim().length > 5000) { editError.value = '问题描述需为 1~5000 个字符'; return }
  if (!f.impact_description.trim() || f.impact_description.trim().length > 500) { editError.value = '请填写影响情况（≤500 字）'; return }
  if (!f.urgency_description.trim() || f.urgency_description.trim().length > 500) { editError.value = '请填写紧急说明（≤500 字）'; return }
  const attachments = editPhotoList.value
    .map(item => item.attachment_id || item.response?.attachment_id)
    .filter(Boolean)

  editSaving.value = true
  try {
    const res = await ticketApi.update(editId.value, {
      nature: f.nature,
      category_id: f.category_id,
      title: f.title.trim(),
      description: f.description.trim(),
      impact_description: f.impact_description.trim(),
      urgency_description: f.urgency_description.trim(),
      location: f.location.trim() || null,
      contact: f.contact.trim() || null,
      asset_id: f.asset_id.trim() || null,
      attachments
    })
    ElMessage.success(res.msg || '工单已更新')
    editVisible.value = false
    loadTickets()
    if (detailVisible.value) openDetail({ ticket_id: editId.value })
  } catch (e) {
    editError.value = e.message || '提交失败，请稍后重试'
  } finally {
    editSaving.value = false
  }
}

// 自动保存草稿：每 30s
watch(form, () => {
  clearTimeout(draftTimer)
  if (editingTicket.value || !form.value.description.trim()) return
  draftTimer = setTimeout(saveDraft, 30000)
}, { deep: true })

async function loadCategories() {
  categoryLoading.value = true
  categoryError.value = ''
  try {
    const res = await categoryApi.leaf()
    categories.value = res.data || []
  } catch (e) {
    categoryError.value = e.message || '分类加载失败，请重试'
  } finally { categoryLoading.value = false }
}

onMounted(async () => {
  resizeDetail()
  window.addEventListener('resize', resizeDetail)
  await loadCategories()
  try {
    const draft = await draftApi.get()
    if (draft.data) draftBanner.value = true
  } catch (e) {}
  await loadTickets()
  // 通知跳转：URL 带 ?ticket=xxx 时自动打开该工单详情
  if (route.query.ticket) {
    openDetail({ ticket_id: route.query.ticket })
  }
})

watch(consultationSession, loadConsultationPrefill, { immediate: true })

// 关键：同页内点击通知只改 query，组件不重挂载、onMounted 不触发——需 watch query 变化
watch(() => route.query.ticket, (tid) => {
  if (tid) openDetail({ ticket_id: tid })
})

onUnmounted(() => { window.removeEventListener('resize', resizeDetail); clearTimeout(draftTimer); editPhotoRequest++; revokePhotoUrls(editPhotoUrls); revokePhotoUrls(detailPhotos.value) })
</script>

<style scoped>
.support-entry { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 22px; margin-bottom: 20px; border: 1px solid var(--el-color-primary-light-7); border-radius: 12px; background: var(--el-color-primary-light-9); }
.support-entry strong { display: block; font-size: 15px; color: var(--el-text-color-primary); }
.support-entry span { display: block; margin-top: 6px; font-size: 13px; color: var(--el-text-color-regular); }
@media (max-width: 760px) { .support-entry { align-items: flex-start; flex-direction: column; } }
/* 照片附件上传提示 */
.upload-tip { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; line-height: 1.4; }

.view-tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
.tab-badge { margin-left: 6px; }

.panel { border-radius: 16px; }
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title { font-size: 16px; font-weight: 600; }

.draft-alert { margin-bottom: 16px; }

.ticket-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--el-text-color-primary);
}


.priority-hint {
  color: var(--el-color-warning);
  font-size: 12px;
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 列表 */
/* ===== 统计条（简洁商务） ===== */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 10px;
}
.stat-icon {
  width: 38px; height: 38px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-value { font-size: 20px; font-weight: 700; color: var(--el-text-color-primary); line-height: 1.1; }
.stat-label { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }

.ticket-list { display: flex; flex-direction: column; gap: 10px; }
.ticket-card {
  cursor: pointer;
  border-left: 3px solid var(--el-color-primary);
  transition: transform .15s ease;
}
.ticket-card:hover { transform: translateY(-1px); }

.ticket-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ticket-id {
  font-family: monospace;
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 13px;
}
.ticket-title { font-size: 15px; font-weight: 500; margin-bottom: 6px; color: var(--el-text-color-primary); }
.ticket-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  display: flex;
  gap: 14px;
  align-items: center;
}

.pagination { margin-top: 16px; justify-content: center; }

/* 弹窗 */
.ticket-detail-content { display: flex; flex-direction: column; gap: 24px; }
.ticket-detail-content > .detail-summary,
.ticket-detail-content > .detail-desc,
.ticket-detail-content > .el-card { margin: 0; }
.ticket-detail-content :deep(.el-descriptions__cell) { padding: 12px 14px; line-height: 1.7; }
.ticket-detail-content :deep(.el-descriptions__content) { overflow-wrap: anywhere; }
.ticket-detail-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; padding: 20px; border: 1px solid var(--el-border-color-lighter); border-radius: 12px; background: var(--el-fill-color-light); }
.detail-action-copy h3 { margin: 0 0 6px; font-size: 15px; }
.detail-action-copy p { margin: 0; font-size: 13px; line-height: 1.7; color: var(--el-text-color-secondary); }
.detail-action-buttons { display: flex; flex-wrap: wrap; gap: 12px; }
.detail-action-buttons :deep(.el-button) { min-height: 44px; margin: 0; }
.ticket-detail-actions > .el-alert { width: 100%; }
@media(max-width: 540px) {
  .ticket-detail-content { gap: 20px; }
  .ticket-detail-actions { padding: 16px; }
  .detail-action-buttons { width: 100%; }
  .detail-action-buttons :deep(.el-button) { flex: 1; }
}
.detail-desc { margin-bottom: 16px; }

.action-card { margin-bottom: 16px; background: var(--el-fill-color-light); }
.action-title { font-weight: 600; }

.reject-area {
  display: flex;
  gap: 8px;
}

.flow-card { background: var(--el-fill-color-light); }
.flow-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.flow-operator { font-size: 13px; color: var(--el-text-color-secondary); }
.flow-remark { font-size: 13px; color: var(--el-text-color-regular); }

.employee-view { min-width:0; }
.page-head { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:24px; }
.page-eyebrow { display:block; font-size:12px; font-weight:700; letter-spacing:1.4px; color:var(--el-color-primary); margin-bottom:8px; }
.page-title { margin:0; font-size:28px; line-height:1.3; color:var(--el-text-color-primary); }
.page-sub { margin:8px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); }
.create-layout { display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:24px; align-items:start; }
.form-panel { min-width:0; }
.panel-title { font-size:18px; }
.panel-header { gap:16px; flex-wrap:wrap; }
.form-section { padding-bottom:12px; margin-bottom:24px; border-bottom:1px solid var(--el-border-color-lighter); }
.section-heading { display:flex; gap:12px; align-items:flex-start; margin:0 0 24px; }
.section-number { display:grid; place-items:center; width:34px; height:34px; flex-shrink:0; font-size:13px; font-weight:700; background:var(--el-color-primary-light-9); color:var(--el-color-primary); border-radius:10px; }
.section-heading h2 { margin:0; font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.section-heading p { margin:5px 0 0; font-size:13px; line-height:1.6; color:var(--el-text-color-secondary); }
.service-guide { position:sticky; top:24px; }
.service-guide :deep(.el-card) { border-radius:16px; }
.guide-heading { display:flex; align-items:center; gap:8px; color:var(--el-color-primary); }
.guide-heading h2 { margin:0; font-size:17px; color:var(--el-text-color-primary); }
.service-guide p { font-size:13px; line-height:1.7; color:var(--el-text-color-secondary); }
.guide-steps { list-style:none; counter-reset:step; padding:0; margin:24px 0; }
.guide-steps li { position:relative; counter-increment:step; padding-left:34px; margin-bottom:24px; }
.guide-steps li::before { content:counter(step); position:absolute; left:0; top:0; display:grid; place-items:center; width:24px; height:24px; border:1px solid var(--el-border-color); border-radius:50%; font-size:12px; color:var(--el-text-color-secondary); }
.guide-steps strong { display:block; font-size:14px; color:var(--el-text-color-primary); }
.guide-steps span { display:block; margin-top:6px; font-size:13px; line-height:1.7; color:var(--el-text-color-secondary); }
.guide-note { display:flex; gap:8px; background:var(--el-fill-color-light); padding:12px; border-radius:10px; color:var(--el-text-color-secondary); font-size:12px; line-height:1.7; }
.guide-note .el-icon { flex-shrink:0; margin-top:3px; }
.list-filters { display:flex; align-items:center; flex-wrap:wrap; gap:10px; }
.filter-label { font-size:13px; color:var(--el-text-color-secondary); }
.page-search { width:200px; }
.scope-note { margin:0 0 16px; font-size:13px; color:var(--el-text-color-secondary); line-height:1.7; }
.page-error { margin-bottom:20px; }
.stat-icon.warning { color:var(--el-color-warning); background:var(--el-color-warning-light-9); }
.stat-icon.primary { color:var(--el-color-primary); background:var(--el-color-primary-light-9); }
.stat-icon.success { color:var(--el-color-success); background:var(--el-color-success-light-9); }
.list-loading { padding:24px 0; color:var(--el-text-color-secondary); font-size:13px; }
.list-loading > span { display:block; text-align:center; margin-top:16px; }
.ticket-card { border-radius:12px; }
.ticket-card:focus-visible { outline:2px solid var(--el-color-primary); outline-offset:3px; }
.ticket-title { font-size:16px; font-weight:600; line-height:1.6; overflow-wrap:anywhere; }
.ticket-header, .ticket-meta { flex-wrap:wrap; }
.detail-summary { margin-bottom:24px; }
.detail-summary h2 { margin:0 0 12px; font-size:22px; line-height:1.5; overflow-wrap:anywhere; color:var(--el-text-color-primary); }
.detail-summary > div { display:flex; align-items:center; flex-wrap:wrap; gap:10px; }
.detail-summary span { font-size:13px; color:var(--el-text-color-secondary); }
.detail-loading { min-height:200px; color:var(--el-text-color-secondary); }
@media(max-width:1199px) { .create-layout { grid-template-columns:minmax(0,1fr); } .service-guide { position:static; } .guide-steps { display:flex; gap:24px; } .guide-steps li { flex:1; margin:0; } }
@media(max-width:767px) {
  .page-head { flex-wrap:wrap; }
  .page-title { font-size:24px; }
  .support-entry { padding:16px; }
  :deep(.el-card__body), :deep(.el-card__header) { padding:16px; }
  .stat-row { grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
  .stat-card { padding:12px; gap:8px; }
  .stat-icon { width:32px; height:32px; }
  .stat-label { font-size:12px; }
  .list-filters { display:grid; grid-template-columns:auto minmax(0,1fr); width:100%; }
  .list-filters :deep(.el-select), .page-search { width:100% !important; }
  .ticket-meta { gap:8px 12px; }
  .guide-steps { display:block; }
  .guide-steps li { margin-bottom:20px; }
  .reject-area { flex-direction:column; }
  .pagination { flex-wrap:wrap; gap:8px; }
  .ticket-form :deep(.el-form-item__content) { gap:8px; }
  .ticket-form :deep(.el-text) { margin-left:0 !important; }
}

.consultation-origin { padding:16px; margin-bottom:20px; border:1px solid var(--el-color-primary-light-7); border-radius:12px; background:var(--el-color-primary-light-9); }
.origin-heading { display:flex; align-items:center; gap:8px; color:var(--el-text-color-primary); font-size:14px; }
.origin-heading .el-icon { color:var(--el-color-primary); }
.consultation-origin p { font-size:13px; line-height:1.7; color:var(--el-text-color-regular); margin:8px 0; overflow-wrap:anywhere; }
.consultation-origin .origin-error { color:var(--el-color-danger); }
.origin-actions { display:flex; flex-wrap:wrap; gap:8px; }
.origin-actions :deep(.el-button + .el-button) { margin-left:0; }
</style>
