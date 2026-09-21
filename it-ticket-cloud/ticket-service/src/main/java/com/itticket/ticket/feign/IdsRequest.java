package com.itticket.ticket.feign;

import lombok.Data;

import java.util.List;

/** 批量查询用户请求体(与 user-service 的 IdsRequest 结构一致) */
@Data
public class IdsRequest {
    private List<String> ids;

    public IdsRequest() {
    }

    public IdsRequest(List<String> ids) {
        this.ids = ids;
    }
}
