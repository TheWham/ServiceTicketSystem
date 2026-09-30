package com.itticket.consultation.service;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.*;
import com.itticket.consultation.enums.EngineerPresence;
import com.itticket.consultation.mapper.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.time.LocalDateTime;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.any;

/**
 * 咨询转人工派单（AssignmentService）的“身份活性”防线：
 *  团队成员 ACTIVE + 运行时 AVAILABLE（在岗）只说明排班与心跳正常，
 *  不代表账号本身有效 —— 账号若已被禁用/吊销角色，绝不允许派单。
 * 因此每次派单前必须额外执行 countActiveEngineer 身份核验
 * （user 表 ACTIVE 且 ENGINEER 角色未吊销），并附 SQL 文本契约防止条件被改丢。
 *
 * 覆盖三类场景：常规派单（assignNextCandidate）、指定人派单（assignPreferred，
 * 常见于会话重开时优先找回原工程师）、身份核验 SQL 契约。
 */
class AssignmentIdentityStatusTest {
    private final CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
    private final TeamMemberMapper members = mock(TeamMemberMapper.class);
    private final EngineerRuntimeStateMapper states = mock(EngineerRuntimeStateMapper.class);
    private final AssignmentMapper assignments = mock(AssignmentMapper.class);
    private final ConsultationMapper consultations = mock(ConsultationMapper.class);
    private final EngineerCategoryCapabilityMapper capabilities = mock(EngineerCategoryCapabilityMapper.class);
    private final ServiceCalendarProvider calendars = mock(ServiceCalendarProvider.class);
    private final LocalDateTime now = LocalDateTime.of(2026, 9, 29, 1, 0);
    private final AssignmentService service = new AssignmentService(routes, members, capabilities, states,
            assignments, consultations, mock(ExceptionQueueItemMapper.class), calendars,
            mock(TicketWorkloadProvider.class), new ConsultationProperties());

    /**
     * 公共桩：路由/成员/运行时全部“看起来可用”，
     * 但 countActiveEngineer 未配对任何值（默认返回 0 = 身份无效）。
     * 各用例按需再补充身份核验桩。日历 deadline 统一返回 +10 分钟。
     */
    @BeforeEach
    void availableRuntimeDoesNotProveAnActiveIdentity() {
        for (Class<?> entity : List.of(EngineerRuntimeState.class, TeamMember.class, CategoryRoute.class,
                Assignment.class, EngineerCategoryCapability.class, Consultation.class)) {
            com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                    new org.apache.ibatis.builder.MapperBuilderAssistant(
                            new com.baomidou.mybatisplus.core.MybatisConfiguration(), "test"), entity);
        }
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        route.setCategoryId("CATEGORY01");
        TeamMember member = new TeamMember();
        member.setTeamId("TEAM01");
        member.setEngineerId("ENG01");
        member.setStatus("ACTIVE");
        EngineerRuntimeState state = new EngineerRuntimeState();
        state.setEngineerId("ENG01");
        state.setPresence(EngineerPresence.AVAILABLE);
        Consultation consultation = new Consultation();
        consultation.setSessionId("SESSION01");
        consultation.setCategoryId("CATEGORY01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of(member));
        when(states.selectById("ENG01")).thenReturn(state);
        when(consultations.selectById("SESSION01")).thenReturn(consultation);
        WorkCalendar calendar = mock(WorkCalendar.class);
        when(calendar.deadlineUtc(any(), anyLong())).thenReturn(now.plusMinutes(10));
        when(calendars.current()).thenReturn(calendar);
    }

    /** 常规派单：成员与运行时在岗但身份核验不存在（账号被禁）-> 不派单、不写 assignment */
    @Test
    void disabledIdentityIsNotAssignedDespiteAvailableRuntime() {
        // 成员与运行时都 ACTIVE/AVAILABLE，但 mapper 中没有任何 ACTIVE 身份事实
        assertTrue(service.assignNextCandidate("SESSION01", "CATEGORY01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    /** 指定人派单（会话重开）：同样要求身份核验通过，被禁账号不得“优先找回” */
    @Test
    void disabledPreferredIdentityIsNotAssignedOnReopen() {
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    /** 正向基线：身份核验通过（count=1）时，常规与指定人两种派单都能成功并写入 assignment */
    @Test
    void activeEngineerCanReceiveBothNormalAndPreferredAssignments() {
        when(members.countActiveEngineer("ENG01")).thenReturn(1);
        assertEquals("ENG01", service.assignNextCandidate("SESSION01", "CATEGORY01", now).orElseThrow().getEngineerId());
        assertEquals("ENG01", service.assignPreferred("SESSION01", "ENG01", now).orElseThrow().getEngineerId());
        verify(assignments, times(2)).insert(any(Assignment.class));
    }

    /**
     * 指定人派单的三重门槛逐层收紧（每层失败都必须空手而归）：
     *  1) 路由表里仍有该分类路由；2) 该工程师仍属当前路由团队；
     *  3) 工程师对该分类的能力标记未被禁用。最后断言全程未写 assignment。
     */
    @Test
    void preferredEngineerMustStillBelongToACurrentRouteAndHaveCategoryCapability() {
        when(members.countActiveEngineer("ENG01")).thenReturn(1);
        // 门槛1：分类路由消失
        when(routes.selectList(any())).thenReturn(List.of());
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        // 门槛2：路由恢复但工程师已离开团队
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of());
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        // 门槛3：成员关系恢复但分类能力被禁用
        TeamMember member = new TeamMember();
        member.setEngineerId("ENG01");
        when(members.selectList(any())).thenReturn(List.of(member));
        EngineerCategoryCapability capability = new EngineerCategoryCapability();
        capability.setEngineerId("ENG01");
        capability.setEnabled(false);
        when(capabilities.selectList(any())).thenReturn(List.of(capability));
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    /**
     * 身份核验 SQL 契约（防回归的文本级断言）：
     * countActiveEngineer 必须同时满足——账号 ACTIVE、角色为 ENGINEER、角色未被吊销，
     * 且 engineerId 以参数绑定传入（本用例同时验证参数名映射正确）。
     */
    @Test
    void identityQueryRequiresActiveAccountAndUnrevokedEngineerRole() {
        var configuration = new com.baomidou.mybatisplus.core.MybatisConfiguration();
        configuration.addMapper(TeamMemberMapper.class);
        var sql = configuration.getMappedStatement(TeamMemberMapper.class.getName() + ".countActiveEngineer")
                .getBoundSql(java.util.Map.of("engineerId", "ENG01"));
        assertTrue(sql.getSql().contains("u.status = 'ACTIVE'"));
        assertTrue(sql.getSql().contains("r.role_code = 'ENGINEER'"));
        assertTrue(sql.getSql().contains("r.revoked_at IS NULL"));
        assertEquals("engineerId", sql.getParameterMappings().get(0).getProperty());
    }
}