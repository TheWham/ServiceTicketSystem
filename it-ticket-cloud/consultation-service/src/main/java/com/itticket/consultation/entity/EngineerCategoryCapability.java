package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 工程师可接分类(SQL-010 engineer_category_capability)。[LOCAL] 只读。
 * 对应 PRD 12.1 第 2 步"筛选可接收该类任务的工程师"。
 * 注意:这不是 PRD 3.3 排除的"技术能力标签",只是路由可达性配置。
 */
@Data
@TableName("engineer_category_capability")
public class EngineerCategoryCapability {

    private String engineerId;
    private String categoryId;
    private String teamId;
    private Boolean enabled;
    private LocalDateTime effectiveAt;
    private LocalDateTime expiredAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
