-- ============================================================================
-- V2_8__golden_aggregate_check.sql
-- ----------------------------------------------------------------------------
-- 黄金问题集支持「跨工单宏观归纳」题型。
--
-- 需求依据：
--   Day21 跨工单聚合归纳能力需要有对应的验收口径。既有评测是**单卡命中**口径
--   （rag_pipeline/evaluation/golden.py 取第一个匹配 expected_chunks 的卡、记 rank、
--   break），对"跨数十条工单做宏观归纳"这类问题物理上无法评分——它压根没有
--   "该命中哪一张卡"这回事。
--
-- 设计说明：
--   1. 加两列而不是另建一张表：聚合题与既有题共用 id/query/ground_truth_answer 等
--      字段，另建表会让题库出现两个真源，导出/导入/处置闭环都要写两遍。
--   2. is_aggregate_check 是**题型标记**，供评测入口分流：为 1 的题走
--      rag_pipeline.pipelines.aggregate_evaluation，为 0 的仍走 golden_evaluation。
--      两者指标正交，刻意不混在同一个大盘里（检索质量 ≠ 聚合正确性，混在一起日后无法单独调参）。
--   3. aggregate_expect 存该题的**期望口径**（维度/期望标签/占比容差/覆盖率下限/
--      是否要求下钻/是否期望拒答等）。用 JSON 而不是拆列：期望项会随题型演化，
--      拆列意味着每加一种校验就要改表结构，而评测脚本本来就要读 JSON。
--      例：
--        {"dimension":"SYMPTOM","expected_top1":"蓝屏","ratio_tolerance":0.5,
--         "min_coverage":0.6,"require_drilldown":true}
--        {"expect_refusal":true,"expect_gates":["SMALL_UNIVERSE"]}
--   4. 两列都有默认值，既有 38 条题零改动即可继续跑（is_aggregate_check=0、
--      aggregate_expect=NULL 表示"按原单卡命中口径评分"）。
--
-- 幂等：MySQL 8 无 ADD COLUMN IF NOT EXISTS，故用 information_schema 存在性判断
--   加 PREPARE 动态执行。本迁移为纯增量（仅 ADD COLUMN），不含 DROP / TRUNCATE /
--   DELETE / MODIFY；重复执行时列已存在，动态语句退化为 SELECT 1（与 V2_7 同等契约）。
-- ============================================================================

SET @col_exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'golden_case'
    AND column_name = 'is_aggregate_check'
);

SET @ddl := IF(
  @col_exists = 0,
  'ALTER TABLE golden_case
     ADD COLUMN is_aggregate_check TINYINT(1) NOT NULL DEFAULT 0
       COMMENT ''是否跨工单宏观归纳题(1=走 aggregate_evaluation, 0=走 golden_evaluation)''
       AFTER is_adversarial,
     ADD COLUMN aggregate_expect JSON NULL
       COMMENT ''聚合题的期望口径: dimension/expected_labels/ratio_tolerance/min_coverage/require_drilldown/expect_gates/expect_refusal 等''
       AFTER is_aggregate_check,
     ADD KEY idx_golden_aggregate (is_aggregate_check)',
  'SELECT 1'
);

PREPARE golden_agg_stmt FROM @ddl;
EXECUTE golden_agg_stmt;
DEALLOCATE PREPARE golden_agg_stmt;