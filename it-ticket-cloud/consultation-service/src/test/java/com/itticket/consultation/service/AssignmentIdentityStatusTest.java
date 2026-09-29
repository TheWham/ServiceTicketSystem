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

    @BeforeEach void availableRuntimeDoesNotProveAnActiveIdentity() {
        for (Class<?> entity : List.of(EngineerRuntimeState.class, TeamMember.class, CategoryRoute.class,
                Assignment.class, EngineerCategoryCapability.class, Consultation.class)) {
            com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                    new org.apache.ibatis.builder.MapperBuilderAssistant(
                            new com.baomidou.mybatisplus.core.MybatisConfiguration(), "test"), entity);
        }
        CategoryRoute route = new CategoryRoute(); route.setTeamId("TEAM01"); route.setCategoryId("CATEGORY01");
        TeamMember member = new TeamMember(); member.setTeamId("TEAM01");
        member.setEngineerId("ENG01"); member.setStatus("ACTIVE");
        EngineerRuntimeState state = new EngineerRuntimeState(); state.setEngineerId("ENG01");
        state.setPresence(EngineerPresence.AVAILABLE);
        Consultation consultation = new Consultation(); consultation.setSessionId("SESSION01");
        consultation.setCategoryId("CATEGORY01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of(member));
        when(states.selectById("ENG01")).thenReturn(state);
        when(consultations.selectById("SESSION01")).thenReturn(consultation);
        WorkCalendar calendar = mock(WorkCalendar.class);
        when(calendar.deadlineUtc(any(), anyLong())).thenReturn(now.plusMinutes(10));
        when(calendars.current()).thenReturn(calendar);
    }

    @Test void disabledIdentityIsNotAssignedDespiteAvailableRuntime() {
        // No active identity fact exists in the mapper, even though membership and runtime remain active.
        assertTrue(service.assignNextCandidate("SESSION01", "CATEGORY01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    @Test void disabledPreferredIdentityIsNotAssignedOnReopen() {
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    @Test void activeEngineerCanReceiveBothNormalAndPreferredAssignments() {
        when(members.countActiveEngineer("ENG01")).thenReturn(1);
        assertEquals("ENG01", service.assignNextCandidate("SESSION01", "CATEGORY01", now).orElseThrow().getEngineerId());
        assertEquals("ENG01", service.assignPreferred("SESSION01", "ENG01", now).orElseThrow().getEngineerId());
        verify(assignments, times(2)).insert(any(Assignment.class));
    }

    @Test void preferredEngineerMustStillBelongToACurrentRouteAndHaveCategoryCapability() {
        when(members.countActiveEngineer("ENG01")).thenReturn(1);
        when(routes.selectList(any())).thenReturn(List.of());
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        CategoryRoute route = new CategoryRoute(); route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of());
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        TeamMember member = new TeamMember(); member.setEngineerId("ENG01");
        when(members.selectList(any())).thenReturn(List.of(member));
        EngineerCategoryCapability capability = new EngineerCategoryCapability();
        capability.setEngineerId("ENG01"); capability.setEnabled(false);
        when(capabilities.selectList(any())).thenReturn(List.of(capability));
        assertTrue(service.assignPreferred("SESSION01", "ENG01", now).isEmpty());
        verify(assignments, never()).insert(any(Assignment.class));
    }

    @Test void identityQueryRequiresActiveAccountAndUnrevokedEngineerRole() {
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
