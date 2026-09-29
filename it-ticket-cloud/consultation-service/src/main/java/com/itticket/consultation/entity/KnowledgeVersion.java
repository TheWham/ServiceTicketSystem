package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 知识版本(DM-004)。[LOCAL] 本服务只读。
 * searchText 是 content_json 的数据库生成列,只作检索投影,不参与写入。
 */
@Data
@TableName("knowledge_version")
public class KnowledgeVersion {

    @TableId(value = "version_id", type = IdType.INPUT)
    private String versionId;
    private String articleId;
    private Integer versionNo;
    /** {"title","summary","body","keywords"} */
    private String contentJson;
    /** 数据库生成列,只供全文检索使用;select=false 避免每次读实体都把全文拉回堆内存。 */
    @TableField(select = false,
            insertStrategy = com.baomidou.mybatisplus.annotation.FieldStrategy.NEVER,
            updateStrategy = com.baomidou.mybatisplus.annotation.FieldStrategy.NEVER)
    private String searchText;
    private String authorId;
    private String reviewerId;
    private LocalDateTime publishedAt;
    private String changeNote;
    /** 高风险知识的平台管理员复核事实(DM-004 / SM-KNOWLEDGE-001)。本服务只读。 */
    private String platformReviewerId;
    private LocalDateTime platformReviewedAt;
    private String platformReviewDecision;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
