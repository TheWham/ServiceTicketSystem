package com.itticket.consultation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.consultation.entity.TeamMember;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface TeamMemberMapper extends BaseMapper<TeamMember> {
    /** Runtime presence cannot substitute for the authoritative account and role state. */
    @Select("""
            SELECT COUNT(*) FROM `user` u
             WHERE u.user_id = #{engineerId} AND u.status = 'ACTIVE'
               AND EXISTS (SELECT 1 FROM user_role r
                            WHERE r.user_id = u.user_id AND r.role_code = 'ENGINEER'
                              AND r.revoked_at IS NULL)
            """)
    int countActiveEngineer(@Param("engineerId") String engineerId);
}
