# IT 服务台前端改造 Implementation Plan

> **For agentic workers:** Use subagent-driven-development for independent page work and requesting-code-review for integration review. Track steps below.

**Goal:** 将已确认的深蓝侧栏、蓝白工作台方案落实到现有 Vue 前端，保留真实业务流程。

**Architecture:** App 管理统一导航和移动端抽屉；全局语义变量覆盖 Element Plus；现有页面继续负责业务接口及状态。页内视图通过 URL query 同步，不新增后端能力。

**Tech Stack:** Vue 3、Vite、Element Plus、Pinia、Vue Router；不新增运行依赖。

## Global Constraints

- 用户已确认 `2026-10-08-service-desk-ui-design.md`，允许在此基础上完善设计并实施。
- 在当前 feature 工作区增量修改，保留现有未提交成果；不提交或覆盖其他任务文件。
- 主题色 #2563EB，导航 #12223D；浅色卡片 16px 圆角；中文系统字体；SVG 图标。
- 375/768/1024/1440px、明暗主题、键盘可达、加载失败与空态区分。
- 角色沿用 EMPLOYEE、ENGINEER、PLATFORM_ADMIN、KNOWLEDGE_ADMIN/KB_ADMIN；不新增客服角色。
- 原型示例数字不进入业务页面；无统计 API 时标明当前列表统计范围。
- 可逆纯样式改动通过浏览器与构建验证；导航和筛选行为用真实行为测试；记录已有失败基线。

## Task 1: 共享设计与导航（主代理）

Files: `frontend/src/styles/service-desk.css`, `frontend/src/App.vue`, `frontend/src/main.js`, `frontend/src/utils/navigation.js`, `frontend/src/router/index.js`, `frontend/tests/navigation.test.mjs`。

- [x] 记录测试基线。为角色主页、导航选中及 query 区分建立 node:test 测试，验证失败后实现纯函数。
- [x] 新建语义主题变量，映射 Element Plus 色阶、卡片、表单、弹窗、焦点和 reduced-motion。
- [x] 统一 App 深蓝侧栏、品牌、顶栏、通知/主题/账号、移动端抽屉。导航链接采用真实 router-link。
- [x] 员工路由 `/employee?tab=create|list`；工程师 `/engineer?view=pool|tasks|completed|consultations`；知识 `/knowledge-admin?tab=ingest|lifecycle`。
- [x] 已授权角色标签和主页一致；账号权限仍以当前路由为准，不扩大后端权限。

## Task 2: 员工体验（主代理）

Files: `LoginView.vue`, `ConsultationView.vue`, `EmployeeView.vue`, `ConsultationChat.vue`。

- [x] 登录页品牌和表单分栏，真实 label 与账号/密码自动补全，沿用登录/忘记密码。
- [x] 咨询页主会话+右侧服务说明，欢迎态保留快捷问题、转人工、直接提单；不引入额外统计请求。
- [x] 员工页标题随 tab 变化；表单分区、手机单列、列表范围说明、状态筛选回第一页、加载与错误重试。
- [x] 保留咨询预填、自动保存、详情深链接与工单操作；列表卡片支持键盘。
- [x] 使用既有咨询测试与浏览器验证发送、失败恢复、转人工、表单跳转。

## Task 3: 工程师工作台（独立实现任务）

Files: `frontend/src/views/EngineerView.vue`, `frontend/src/components/EngineerConsultation.vue`; 可新增 `frontend/src/utils/engineerViews.js` 和对应行为测试。

- [x] 阅读设计 spec 与现有接口。对视图筛选编写失败的真实行为测试。
- [x] 对应 view query 提供工单池、我的任务、已完成、人工咨询；保留详情与接单状态机。`pool` 仅 ASSIGNED；`tasks` 为 IN_PROGRESS/PENDING_SUPPLEMENT/PENDING_EXTERNAL/PENDING_ACCEPTANCE；`completed` 为 COMPLETED/CANCELLED/CLOSED；默认 all 可展示看板。
- [x] 接通已有 EngineerConsultation，不启用旧 AgentWorkbenchView；使 view=consultations 刷新可进入咨询面板，关闭返回工程师页。
- [x] 统一标题、SVG 图标、表格/看板层级、局部空态/错误重试、移动端和暗色。统计只声明已加载工单。
- [x] 检查构建、行为测试，报告文件和风险；不改 App、全局样式、其他页面；不提交。

## Task 4: 管理与知识工作台（独立实现任务）

Files: `SupervisorView.vue`, `KnowledgeAdminView.vue`, `AccountManageView.vue`。

- [x] 统一页面 eyebrow、标题、说明、操作分组；卡片/表格/表单采用共享主题变量。
- [x] 管理工单统计注明当前页范围，筛选重置分页；加载与失败反馈明确；保留派单和管理权限。
- [x] 知识页 tab=ingest|lifecycle 与 URL 双向同步；SVG 替换结构性 emoji；技术追踪作为次级内容；保留真实审核流程。
- [x] 账号页可见标签、弹窗手机适配、空态/加载反馈；不扩展账号权限。
- [x] 运行构建或 Vue 编译检查，报告；不修改 App、全局样式或其他页面，不提交。

## Task 5: 集成验收与审查（主代理 + reviewer）

- [x] `npm run build`，`node --test tests/*.test.mjs` 对照 baseline；新增测试必须通过。
- [x] Playwright 接口桩检查所有角色页面与深链接、筛选、键盘、窄屏、明暗；桩数据只存在测试中。
- [x] 真实网关可用时只作必要只读/登录验证，不写业务工单。
- [x] 保存截图到 `logs/ui-redesign/`，记录验证结果与现有限制；独立代码审查并修复本次引入的问题。
- [x] 将设计 doc 更新为实施完成与真实边界，交付本地预览地址和截图，不发布或提交现有工作区其他改动。

## 执行记录

- 基线输出：`logs/ui-baseline-tests.txt`；当前分支 feature，有已有未提交改动。

