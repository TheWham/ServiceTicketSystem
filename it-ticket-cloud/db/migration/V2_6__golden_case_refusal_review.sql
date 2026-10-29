-- ============================================================================
-- V2_6__golden_case_refusal_review.sql
-- ----------------------------------------------------------------------------
-- 黄金数据集（golden_case）与 AI 拒答处置（bad_case_review）承载表。
--
-- 需求依据：
--   Day20 Demo Day「沉淀 Bad Case → 黄金问题集回归」在线闭环：
--   知识库管理员在页面上查询 AI 拒答记录（consultation_message.citation_json
--   的 replyType='REFUSE' + refusalReason），三选一处置——
--   补知识后进黄金集(GOLDEN_QA) / 直接进黄金对抗区(GOLDEN_REFUSAL) / 丢弃(DISCARD)。
--
-- 设计说明：
--   1. bad_case_review 只存「处置决策」，待处置列表由
--      consultation_message(AI REFUSE 消息) 实时联查 ai_interaction 与本表
--      LEFT JOIN 得出（无同步队列、零延迟）；uk_bad_case_ai_message 唯一键
--      保证一条拒答只能被处置一次，重复处置由服务层返回冲突。
--   2. golden_case 为黄金问题集唯一真源：种子由 db/tools/golden_seed_import.py
--      从 evals/golden_dataset_v1.1.json 幂等导入（natural_key=原 JSON id），
--      处置入集 natural_key=BC-{ai_message_id}，手工新增 natural_key=manual-{uuid}。
--      Python 评测管道（rag_pipeline golden_evaluation）继续读 JSON 文件，
--      由 db/tools/golden_export.py 从本表导出，评测代码零改动。
--   3. 主键/关联键用 VARCHAR 与 consultation_message(ai_interaction) 现有
--      字符串业务键对齐（message_id/session_id/interaction_id 均为 VARCHAR）。
--   4. 黄金条目不物理删除（enabled=0 软删），保证评测回放可追溯，
--      与「已发布知识不物理删除」（PRD §16.4）同一原则。
--
-- 幂等：本迁移为纯增量（CREATE TABLE ... IF NOT EXISTS），不含 DROP / TRUNCATE / DELETE。
--   重复执行会因表已存在被 IF NOT EXISTS 跳过（与 V2_5 同等执行契约）。
-- ============================================================================

CREATE TABLE IF NOT EXISTS bad_case_review (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ai_message_id VARCHAR(64) NOT NULL COMMENT 'AI 拒答消息 message_id (consultation_message)',
  session_id     VARCHAR(32) NOT NULL COMMENT '所属咨询会话',
  interaction_id VARCHAR(64) NULL COMMENT '关联 ai_interaction.interaction_id',
  question_text  TEXT NOT NULL COMMENT '触发拒答的员工提问原文',
  refusal_reason VARCHAR(64) NULL COMMENT '结构化拒答原因 (AiRefusalReason)',
  confidence     DECIMAL(8,4) NULL COMMENT '处置时的置信度快照',
  decision ENUM('GOLDEN_QA','GOLDEN_REFUSAL','DISCARD') NOT NULL COMMENT '处置决策',
  golden_case_id BIGINT NULL COMMENT '入黄金集时回填 golden_case.id',
  review_note VARCHAR(500) NULL COMMENT '处置备注',
  reviewed_by VARCHAR(64) NOT NULL COMMENT '处置人 userId',
  reviewed_at DATETIME(6) NOT NULL,
  UNIQUE KEY uk_bad_case_ai_message (ai_message_id),
  KEY idx_bad_case_decision (decision)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 拒答案例处置记录';

CREATE TABLE IF NOT EXISTS golden_case (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  natural_key VARCHAR(128) NOT NULL COMMENT '幂等键: 种子=原JSON id / 处置=BC-{ai_message_id} / 手工=manual-{uuid}',
  category VARCHAR(64) NOT NULL COMMENT '业务分类',
  difficulty VARCHAR(16) NOT NULL DEFAULT 'MEDIUM' COMMENT '难度 EASY/MEDIUM/HARD',
  query TEXT NOT NULL COMMENT '问题正文',
  ground_truth_answer MEDIUMTEXT NOT NULL COMMENT '标准答案(对抗样本为期望拒答话术)',
  reference_chunk_ids JSON NULL COMMENT '期望命中的知识切片',
  expected_keywords JSON NULL COMMENT '期望关键词',
  is_conflict_check TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否版本冲突消歧题',
  is_adversarial TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否对抗样本(回归验证仍拒答)',
  source_type ENUM('SEED','BAD_CASE','MANUAL') NOT NULL DEFAULT 'SEED' COMMENT '来源: 种子导入/bad case 处置/手工',
  source_ai_message_id VARCHAR(64) NULL COMMENT '来源拒答消息 id (BAD_CASE 时)',
  enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '软删标记: 0=移出评测',
  created_by VARCHAR(64) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  UNIQUE KEY uk_golden_natural_key (natural_key),
  KEY idx_golden_adversarial (is_adversarial),
  KEY idx_golden_source (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='黄金问题集(评测基准唯一真源)';
