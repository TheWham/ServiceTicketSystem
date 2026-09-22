package com.itticket.user.dto;

import lombok.Data;

import java.util.List;

/** 内部批量查询用户请求体 */
@Data
public class IdsRequest {
    private List<String> ids;
}
