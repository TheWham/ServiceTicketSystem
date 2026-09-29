package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 团队成员（F-06 路由：分类→团队→工程师） */
@Data
@TableName("team_member")
public class TeamMember {
    private String teamId;
    private String engineerId;
    private LocalDateTime joinedAt;
    private Boolean enabled;
    private LocalDateTime leftAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
