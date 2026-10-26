package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 黄金问题集条目(对应表 golden_case,V2_6)。唯一真源在 rag-service 的管理接口,
 * 本实体仅供处置事务内写入(BAD_CASE 来源),与 rag-service 同表不同模块。
 */
@Data
@TableName("golden_case")
public class GoldenCase {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 幂等键:处置来源固定 BC-{ai_message_id} */
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
