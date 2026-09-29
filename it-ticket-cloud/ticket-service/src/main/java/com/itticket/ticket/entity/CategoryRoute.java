package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 分类路由（PRD §12.1 分配算法第 1 步：分类→有序候选团队） */
@Data
@TableName("category_route")
public class CategoryRoute {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String categoryId;
    private String teamId;
    private Integer routeOrder;
    private LocalDateTime effectiveAt;
    private LocalDateTime createdAt;
}
