package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 团队成员(SQL-010 team_member)。[LOCAL] 只读,复合主键不使用 ORM 注解。 */
@Data
@TableName("team_member")
public class TeamMember {

    private String teamId;
    private String engineerId;
    private LocalDateTime joinedAt;
    private LocalDateTime leftAt;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
