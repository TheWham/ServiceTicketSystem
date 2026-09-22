package com.itticket.ticket.dto;

import lombok.Data;

/** 通用状态操作请求 */
@Data
public class ActionRequest {
    private String action;
    private String remark;
}
