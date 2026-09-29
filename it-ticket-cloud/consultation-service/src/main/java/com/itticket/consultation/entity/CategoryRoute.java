package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 分类到团队的有序路由(SQL-010 category_route)。[LOCAL] 只读。
 * 复合主键按 DM-004 约定不使用 ORM 复合主键注解,只做条件查询。
 */
@Data
@TableName("category_route")
public class CategoryRoute {

    private String categoryId;
    private String teamId;
    private Integer routeOrder;
    private LocalDateTime effectiveAt;
    private LocalDateTime expiredAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
