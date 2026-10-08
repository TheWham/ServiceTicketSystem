# AI 已解决反馈进入知识审核队列

**目标：** 通用 AI 回答被员工标记 HELPFUL 后，知识管理员能在现有 PENDING_REVIEW 列表看到对应问答并审核发布。

**设计：** 当前反馈仅持久化 ai_interaction.feedback，知识服务缺少消费者。沿用共享 MySQL，由 rag-service 每 5 秒消费反馈，按消息 metadata.interactionId 和 ai-q:/ai-a: 请求键准确配对问答。创建 knowledge_article、knowledge_version，复用 KnowledgeStore.submitForReview 写审核流转和事件，整个操作在同一事务内完成。无需新增表或调用模型；不自动发布或索引。

**约束：** 保留当前工作区已有改动。只处理 HELPFUL + ANSWER + generalAnswer + 无引用的完整、未撤回问答。确定性文章 ID 防止重复消费，历史反馈自动补处理；脱敏后入队，提示注入内容跳过并记录来源 ID。每批使用游标，失败记录不会堵住后续记录，下轮重试。正文保留完整问答，来源会话及回答 ID 写入 change_note，供管理员查看。

**实现与验证：**

- [ ] 在 rag-service 增加消费、脱敏、幂等、失败回滚的回归测试，先验证失败。
- [ ] 新增 AiFeedbackCandidate、AiFeedbackSourceMapper、AiFeedbackKnowledgeService 和调度器；启用调度及可配置开关。
- [ ] 使用既有知识生命周期创建待审记录，更新客服说明和文档。
- [ ] 执行 rag-service、consultation-service 测试及前端相关检查；检查 SQL 配对及管理员审核兼容性。

**验收：** 服务启动后新反馈默认约 5 秒可见；积压逐批补入；同一回答不重复生成知识；管理员拒绝/发布后不会重新提交；未审核内容不进入检索；依赖故障不会影响员工确认解决。
