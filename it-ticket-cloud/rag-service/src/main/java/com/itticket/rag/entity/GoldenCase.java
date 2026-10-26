package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 黄金问题集条目(对应表 golden_case,V2_6)。评测基准唯一真源:
 * SEED 由 db/tools/golden_seed_import.py 幂等导入,BAD_CASE 由 consultation-service
 * 拒答处置事务写入,MANUAL 由本模块管理接口新增。不物理删除(enabled=0 软删)。
 */
@Data
@TableName("golden_case")
public class GoldenCase {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 幂等键:SEED=原JSON id / BAD_CASE=BC-{ai_message_id} / MANUAL=manual-{uuid} */
    @TableField("natural_key")
    private String naturalKey;

    private String category;

    private String difficulty;

    private String query;

    @TableField("ground_truth_answer")
    private String groundTruthAnswer;

    @TableField("reference_chunk_ids")
    private String referenceChunkIdsJson;

    @TableField("expected_keywords")
    private String expectedKeywordsJson;

    @TableField("is_conflict_check")
    private Integer isConflictCheck;

    @TableField("is_adversarial")
    private Integer isAdversarial;

    @TableField("source_type")
    private String sourceType;

    @TableField("source_ai_message_id")
    private String sourceAiMessageId;

    private Integer enabled;

    @TableField("created_by")
    private String createdBy;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
