# a99ab6a 字段修订落实

基线：远程 main 的 a99ab6a；保留该提交之前合入的其他代码。用户后续要求整套PRD/spec强对齐：以PRD业务字段为准统一文档，再修正已有运行模块；未开发模块只对齐文档，不补齐运行模块。

## 对照范围

| 对象 | 旧实现 | 本次规范 |
|---|---|---|
| 用户 | user_account / display_name / enabled | user / name / status，保留 employee_no、department_id、identity_source 和技术元数据 |
| 团队及成员 | enabled | status |
| 分类 | nature / enabled | ticket_nature / status |
| 工单与快照 | ticket_nature / field_snapshot_json | nature / field_definition_snapshot |
| 草稿性质 | nature | ticket_nature |
| 咨询/流转/SLA | resolution_type / event_code / breached_at | resolved_type / event / breach_at；SLA补ticket_id与通用关联一致性 |
| 知识/AI/审计 | content_json / retrieved_versions_json / latency_ms / before_json / after_json | content / retrieved_versions / latency / before_value / after_value；保留JSON类型与单位 |

EngineerCategoryCapability 等仍明确使用 enabled 的其他对象不作全局替换；角色与UTC语义不回退。前端旧登录缓存可一次性归一，但新API和持久化不再输出旧用户字段。

## 实施与验证

- [x] 后端实体、Mapper、查询条件、投影与所有调用方按新字段修正；覆盖 ACTIVE/禁用行为。
- [x] 前端以新字段为准，旧缓存兼容及冲突值优先级有行为测试。
- [x] 更新空库基线、seed、生成器与范围检查；8张未开发模块表保持不变。
- [x] V2_0/V2_1保持已发布内容，增加从470ce57字段到PRD2.2统一字段的显式升级；保留数据且不执行真实业务数据库迁移。
- [x] 后端全测试、前端测试/构建、SQL静态与独立MySQL验证；验证后提交推送main。

## 仍需区分的文档差异

PRD第20节仍列 resolved_type、工单nature、流转event，未修改的spec列 resolution_type、ticket_nature、event_code。用户已明确要求这些差异也统一处理：保留PRD的 resolved_type/nature/event/breach_at/content/retrieved_versions/latency/before_value/after_value，spec和已实现代码同步；历史迁移及未开发运行表保持不变。文档门禁验证PRD→DM→SQL→HTTP关键字段。

原工作目录、运行服务、现有业务数据库不自动切换；所有编辑在隔离工作树，数据库验证使用独立临时实例。

验证记录：后端221项、前端41项、文档5项、SQL静态10项测试通过；后端打包与前端构建通过。真实MySQL覆盖两条升级链、状态/JSON/UTC保留及失败门禁；独立临时服务通过8组业务接口、2组实际网关身份校验、禁用工程师普通/恢复分配和SLA关联验证。独立审查发现的ACTIVE状态路由缺口已修复并通过回归。现有业务数据库未迁移，未接入的独立ai-service代码保留原样。
