package com.itticket.user.dto;

import lombok.Data;

@Data
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class LoginRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("userId")
    private String userId;
    private String password;
}
