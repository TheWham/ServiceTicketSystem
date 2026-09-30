package com.itticket.user.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 团队自动分配（ticket 域表，共享库直写）。
 * PRD F-06 路由链路为 分类→支持团队→团队成员，新建工程师账号时自动补齐团队成员关系，
 * 使其无需人工维护排班即可被自动派单（负载均衡按未结单量取最少者）。
 */
public interface TeamAutoJoinMapper {

    /** 全部 ACTIVE 支持团队 */
    @Select("SELECT team_id FROM support_team WHERE status = 'ACTIVE'")
    List<String> listActiveTeams();

    /** 已存在成员关系则复位为 ACTIVE（重复创建/曾离队的工程师可直接复用） */
    @Update("UPDATE team_member SET status = 'ACTIVE', left_at = NULL, updated_at = UTC_TIMESTAMP(6) "
            + "WHERE team_id = #{teamId} AND engineer_id = #{engineerId}")
    int reactivate(@Param("teamId") String teamId, @Param("engineerId") String engineerId);

    /** 新增成员关系 */
    @Insert("INSERT INTO team_member (team_id, engineer_id, status, joined_at, created_at, updated_at) "
            + "VALUES (#{teamId}, #{engineerId}, 'ACTIVE', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))")
    int join(@Param("teamId") String teamId, @Param("engineerId") String engineerId);
}