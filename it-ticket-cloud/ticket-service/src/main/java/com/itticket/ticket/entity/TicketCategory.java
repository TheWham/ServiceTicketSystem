package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 工单末级分类(it_ticket.ticket_category,PRD 10.1) */
@Data
@TableName("ticket_category")
public class TicketCategory {
    @TableId(value = "category_id", type = IdType.INPUT)
    private String categoryId;
    private String name;
    /** 0=平台管理员已停用,停用后不可再用于新工单 */
    private Integer enabled;
    private Integer sortNo;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
