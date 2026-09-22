package com.itticket.common.user;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户信息(内部服务间传递, camelCase)
 * user-service 的 /api/internal/users 接口返回此结构,gateway 与 ticket-service 消费
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserInfo {
    private String userId;
    private String name;
    private String role;
    private String department;
    private String status;
}
