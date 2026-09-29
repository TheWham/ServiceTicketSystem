package com.itticket.user.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.itticket.user.entity.User;
import lombok.Data;

/** PRD identity projection plus the role used by the current login client. */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UserVO {
    private String userId;
    private String employeeNo;
    private String name;
    private String departmentId;
    private String status;
    private String identitySource;
    private String role;

    public static UserVO from(User user, String role) {
        UserVO value = new UserVO();
        value.setUserId(user.getUserId());
        value.setEmployeeNo(user.getEmployeeNo());
        value.setName(user.getName());
        value.setDepartmentId(user.getDepartmentId());
        value.setStatus(user.getStatus());
        value.setIdentitySource(user.getIdentitySource());
        value.setRole(role);
        return value;
    }
}
