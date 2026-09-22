# IT 服务工单系统 · 未完成项 Roadmap

> 本文档以 **PRD(7)** 为主参照、**SPEC(2)** 为技术补充,列出当前微服务版尚未实现的功能点。
> 现状基线:`it-ticket-cloud/`(Spring Cloud 微服务,Java 17 + Spring Boot 3.2.5,MySQL 8)。
>
> 最近更新:2026-09-22

---

## 总览

| 优先级 | 数量 | 主题 |
|:---|:---|:---|
| **P0**(阻断业务闭环) | 6 项 | F-01 推荐、F-02 通知调度、F-03 智能客服、字段级校验完整化、通知短信兜底、SPEC 基础设施三件套 |
| **P1**(工程增强) | 5 项 | SPEC 超时降级矩阵、状态机完整性、报表五项、附件 OSS、自动派单 |
| **P2**(智能化扩展) | 4 项 | FAQ 沉淀、相似度合并、对话式查进度、移动端 |

图例:📄=PRD(7) 章节,⚙️=SPEC(2) 章节

---

## P0 · 阻断业务闭环(必须完成)

### P0-1 F-01 知识库相似推荐(智能客服前置)

- **来源**:📄 四.2「AI Agent / API 接口汇总表」第 1 条 + 图 3-2
- **接口契约**:`POST /api/kb/recommend`
- **触发**:F-01 提单输入停顿 300ms 后触发
- **入参**:`creator_id` / `asset_id` / `category` / `description` / `system_stage`
- **出参**:`has_recommendation` + `recommend_list[]`(article_id / title / similarity_score / solution_summary)
- **降级契约**:响应 >2s 或异常 → 前端静默隐藏推荐卡,不弹框不阻塞提单;MQ 异步落库搜索词与资产号
- **现状**:❌ 完全未实现。微服务里无 `KnowledgeBaseController`,无检索引擎,无 FAQ 库表
- **建议路径**:
  1. `ticket-service` 新增 `KbController.recommend()`
  2. 检索层:**先 BM25**(MySQL FULLTEXT)→ **再向量**(可选,Embedding + Milvus/Qdrant)→ **Rerank**(BGE-Reranker Top3)
  3. 降级:Hystrix/Resilience4j 超时 2s 熔断

### P0-2 F-02 全节点自动通知(独立调度接口)

- **来源**:📄 四.2「AI Agent / API 接口汇总表」第 2 条
- **接口契约**:`POST /api/notify/dispatch`
- **入参**:`ticket_id` / `event_type` / `receiver_id` / `priority` / `template_params`
- **出参**:`channel_used` / `is_fallback` / `delivery_status`
- **降级契约**:
  - 企微推送 >3s 超时 → HIGH 优先级触发**短信兜底**
  - 低/中级仅重试,不发短信
  - Redis 锁(TTL 60s)防重复推送
- **现状**:⚠️ 半实现。`ticket-service` 内有 `NotificationService.sendNotification()`,已实现「1 分钟幂等 dedupKey = ticket_id:event_type」,但:
  - 仅作内部 Service 调用,未暴露独立 `POST /api/notify/dispatch` 接口
  - 无短信兜底通道
  - 无 Redis 锁(纯数据库幂等)
- **建议路径**:
  1. `ticket-service` 新增 `NotifyController.dispatch()`
  2. 通道抽象:`NotificationChannel` 接口 + `WeworkChannel` / `SmsChannel` / `EmailChannel` 实现
  3. 短信通道:阿里云 SMS / 腾讯云 SMS(需 access key,放配置中心)
  4. 引入 Redis 替代 SPEC §1.6 的「替代 Redis 三件套」

### P0-3 F-03 智能客服对话(对话式 AI 排查)

- **来源**:📄 图 3-6「智能客服(员工先让 AI 试着解决问题,AI 无法解决,再提交成工单)」
- **业务流程**:员工发起 → AI 客服对话排查 → 解决关单 / 未解决降级 → 人工客服兜底 → 创建工单 → 工程师处理
- **现状**:❌ 完全未实现。无对话界面、无 NLU、无对话状态机、无降级路径
- **建议路径**:
  1. 前端新增对话面板(独立于提单页)
  2. 后端新增 `ChatController`:
     - `POST /api/chat/message` 发送用户消息
     - `POST /api/chat/resolve` 标记解决
     - `POST /api/chat/escalate` 降级转人工(生成 ticket 草稿并预填上下文)
  3. NLU 层:调用大模型(OpenAI/通义/文心)做意图识别 + FAQ 检索回答
  4. 强约束拒答:模型不决定开不开单,仅"把已有答案说得更顺";开单动作由用户点按钮触发

### P0-4 字段级校验完整化(前端 + 后端契约)

- **来源**:📄 三.2「字段级校验与交互反馈表」(适用 F-01 提单页)
- **现状**:⚠️ 前端 Element Plus 化时已做基础必填校验,但**完整契约未落地**:

| 校验项 | PRD 要求 | 当前状态 |
|:---|:---|:---|
| `title` | 必填,1–50 字符,失焦为空红字 + 实时字数 12/50 | ⚠️ 已有必填,无字数实时反馈 |
| `category` | 必填,5 枚举,选中后 300ms 防抖调推荐 | ⚠️ 已有必填,无防抖推荐联动 |
| `priority` | 必填,选中 HIGH 时提示「将同步短信通知」 | ❌ 无提示 |
| `description` | 必填,10–500 字符,不足置灰,超限截断飘红 | ⚠️ 已有长度校验,无置灰/截断 |
| `attachment_urls` | 选填,jpg/png ≤5MB ×3,拖拽/粘贴/按钮 | ❌ 完全未实现上传(只是 URL 数组字段) |
| `expected_finish_time` | 选填,格式 YYYY-MM-DD HH:mm:ss,须 ≥ 当前 | ⚠️ 有 el-date-picker,无未来时间约束 |
| `asset_id` | 选填,硬件必填,正则 `^IT-[A-Z]{2,4}-\d{8}$`,失焦调 CMDB 校验 | ⚠️ 仅有正则,无 CMDB 校验接口调用 |
| `submit` | 必填未齐置灰,Debounce 3s 防重复 | ⚠️ 有 loading,无 3s 防抖 |
| `save_draft` | 30s 自动存,显示「草稿已自动保存 14:22」 | ⚠️ 有定时存,无时间戳提示 |

- **建议路径**:
  1. 前端补齐交互反馈(工作量约 2-3 天)
  2. 后端补 `POST /api/assets/validate`(CMDB 资产校验,Mock 即可)
  3. 补 `POST /api/files/upload`(附件上传,先本地存储 / 后 OSS)

### P0-5 通知 HIGH 优先级短信兜底

- **来源**:📄 四.2「全节点自动通知」降级契约 + ⚙️ SPEC §2.4
- **要求**:HIGH 优先级工单状态变更,企微推送 >3s 超时 → 自动切换短信通道
- **现状**:❌ 未实现。`NotificationService` 无通道切换逻辑
- **建议路径**:
  1. 抽象 `NotificationChannel` 接口,定义 `send()` / `isAvailable()` / `getCost()`
  2. `NotificationDispatcher` 按优先级路由:HIGH → [Wework, Sms],MEDIUM/LOW → [Wework]
  3. 失败检测:超时 3s 或返回非 0 → 标记 `is_fallback=true` 并切换下一通道

### P0-6 SPEC 基础设施三件套(替代 Redis)

- **来源**:⚙️ SPEC §1.6「基础设施表(替代 Redis 的三件套)」
- **要求**:不引入 Redis,用数据库表实现:
  1. **分布式锁表** `distributed_lock`(key, owner, expire_at)
  2. **ID 生成器表** `id_generator`(biz_type, current_value, step)
  3. **状态缓存表** `state_cache`(key, value, ttl)
- **现状**:⚠️ 部分实现。`TicketNoGenerator` 存在但实现细节未知;分布式锁未见;状态缓存未见
- **建议路径**:
  1. 确认 `ticket_id` 生成是否走 `id_generator` 表(雪花算法 or 数据库号段)
  2. 补 `distributed_lock` 表 + `LockService`,用于「防止同 ticket 并发操作」
  3. 补 `state_cache` 表(可选,优先级低)

---

## P1 · 工程增强

### P1-1 SPEC 超时与降级矩阵完整落地

- **来源**:⚙️ SPEC §2「超时与降级(Fallback)响应逻辑」
- **现状**:❌ 未见 Resilience4j / Hystrix 配置
- **建议**:
  1. `common-web` 引入 Resilience4j
  2. 按 SPEC §2.1「超时阈值矩阵」配置:提单 3s、查询 5s、通知 3s、KB 推荐 2s
  3. 实现 SPEC §2.2-2.7 所有降级路径

### P1-2 工单状态机完整性(8 态 12 转移)

- **来源**:📄 四.1「工单流转状态」枚举 + ⚙️ SPEC §3「工单状态转换表」
- **8 态**:CREATED → ASSIGNED → PENDING_SUPPLEMENT ⇄ PENDING_EXTERNAL → PENDING_ACCEPTANCE → ACCEPTED / REJECTED → CLOSED
- **现状**:⚠️ 部分实现。README 写「7 状态 12 转移」,PRD 已扩为 8 态(含 REJECTED)
- **建议**:
  1. 对比 PRD 和 SPEC 状态机差异,补齐 REJECTED 路径
  2. `ticket_flow_log` 表补 `action_type` 字段标记驳回/撤回等特殊事件

### P1-3 报表五项

- **来源**:📄 一.功能规格说明清单(隐含)+ 历史会话确认的 P1 任务
- **5 项**:
  1. 员工提单量统计(按部门/时间)
  2. 工程师工作量(按人/状态)
  3. SLA 达标率(按优先级/分类)
  4. 平均响应时长(按优先级/分类)
  5. 满意度(按工程师/分类,基于 rating)
- **现状**:❌ 未实现。`SupervisorView.vue` 只有统计卡片占位
- **建议**:
  1. `ticket-service` 新增 `ReportController` + 5 个 endpoint
  2. 纯 SQL 聚合,无需引入 BI 工具
  3. 前端 Supervisor 工作台接入

### P1-4 附件上传 OSS/S3 集成

- **来源**:📄 三.2 字段表 `attachment_urls` + 四.1 Data Model
- **现状**:❌ 完全未实现。前端只有 URL 数组展示,无实际上传接口
- **建议**:
  1. `ticket-service` 新增 `FileController.upload()`
  2. 实现 `MultipartFile` 接收 + 本地存储(短期)或 OSS/S3 集成(长期)
  3. 校验:jpg/png,单张 ≤5MB,最多 3 张
  4. 返回 URL 列表供 `attachment_urls` 字段使用

### P1-5 自动派单 + HITL 人工兜底

- **来源**:历史会话确认的 P1 任务
- **要求**:按规则自动派单(技能匹配 + 负载均衡),失败时转主管人工派单
- **现状**:❌ 未实现。当前只有 supervisor 手动派单(`assign`)和 engineer 主动领取(`claim`)
- **建议**:
  1. `TicketService` 新增 `autoAssign()` 方法
  2. 规则引擎:按 `category` → 找技能匹配的工程师 → 按当前 `ASSIGNED` 数量升序取最少
  3. HITL 兜底:无匹配 / 全部满载 → 落 `pending_assignment_queue` 表,通知 supervisor

---

## P2 · 智能化扩展

### P2-1 FAQ 自动沉淀(ACCEPTED → 知识库)

- **来源**:历史会话确认的 P2 任务 + 📄 图 3-6 延伸
- **业务流**:工单 ACCEPTED → 脱敏归档 → 写入 FAQ 知识库(DRAFT)→ 主管审核 → 入正式库
- **现状**:❌ 未实现
- **建议**:
  1. `ticket-service` 监听 `ACCEPTED` 事件
  2. 触发 `FaqArchiveService.archive()`:LLM 生成 FAQ 问答对 → 写 `faq_article(status=DRAFT)`
  3. `user-service` 新增 supervisor 审核界面 + `POST /api/faq/{id}/approve`

### P2-2 相似度合并判定(≥0.85)

- **来源**:历史会话确认的 P2 任务
- **要求**:新 FAQ 入库前,与现有同分类 FAQ 做相似度计算,≥0.85 触发合并分支(不新增,合并到已有条目)
- **现状**:❌ 未实现
- **建议**:
  1. 引入 Embedding 模型(本地 Sentence-BERT 或 OpenAI Embedding)
  2. 余弦相似度计算 + 阈值判定
  3. 合并策略:保留高票答案,低票合并到「其他解决方案」

### P2-3 对话式查进度

- **来源**:📄 图 3-6 延伸 + 历史会话 P2 任务
- **要求**:员工通过对话查询「我的工单当前进度」
- **现状**:❌ 未实现
- **建议**:在智能客服对话面板中加意图识别:「查进度」→ 调 `GET /api/tickets?creator_id=xxx&status!=CLOSED` → 格式化返回

### P2-4 移动端

- **来源**:历史会话 P2 任务
- **要求**:H5 / 小程序 / 企业微信应用
- **现状**:❌ 未实现

---

## 优先级定义

- **P0**:不做就无法完成业务闭环,或 PRD/SPEC 明确写了"必须"
- **P1**:做了能显著提升工程质量或管理效率,但不做也能跑
- **P2**:面向未来的智能化扩展,依赖 P0/P1 落地

## 实施建议

**最近 2 周**:P0-1(KB 推荐)→ P0-4(字段校验)→ P0-2(通知调度)
**最近 1 个月**:P0-3(智能客服)→ P0-5(短信兜底)→ P0-6(基础设施)
**最近 3 个月**:P1 全部 + P2-1(FAQ 沉淀)

---

## 参照文档

- [PRD(7)](.) —— 业务需求与功能规格(主参照)
- [SPEC(2)](.) —— 技术规格书(技术补充)
- [it-ticket-cloud/README.md](it-ticket-cloud/README.md) —— 微服务版详细技术文档
- [acceptance/README.md](acceptance/README.md) —— 验收评测报告(27 项用例全绿)
