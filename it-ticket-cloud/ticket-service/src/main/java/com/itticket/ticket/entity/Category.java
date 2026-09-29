package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import lombok.Data;

import java.time.LocalDateTime;

/** 分类 category —— PRD §20，最多三级，仅末级可提单，停用保留快照 §10.1 */
@Data
@TableName("category")
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class Category {
    @TableId(value = "category_id", type = IdType.INPUT)
    private String categoryId;
    private String parentId;
    /** 工单性质 INCIDENT/SERVICE_REQUEST */
    @TableField("ticket_nature")
    private String ticketNature;
    private String name;
    /** 1~3，仅末级（level=3 或最深层）可提单 */
    private Integer level;
    /** ACTIVE/DISABLED */
    private String status;
    private String definitionVersion;
    private Integer version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
