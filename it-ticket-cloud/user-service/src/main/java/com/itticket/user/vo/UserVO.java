package com.itticket.user.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;

/** 对外输出的用户信息(snake_case,与旧版 SQLite 行字段一致) */
@Data
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UserVO {
    private String userId;
    private String name;
    private String role;
    private String department;
}
