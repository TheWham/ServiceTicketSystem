package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.Assignment;
import com.itticket.consultation.entity.CategoryRoute;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.EngineerCategoryCapability;
import com.itticket.consultation.entity.EngineerRuntimeState;
import com.itticket.consultation.entity.ExceptionQueueItem;
import com.itticket.consultation.entity.TeamMember;
import com.itticket.consultation.enums.AssignmentBizType;
import com.itticket.consultation.enums.AssignmentEndReason;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.EngineerPresence;
import com.itticket.consultation.mapper.AssignmentMapper;
import com.itticket.consultation.mapper.CategoryRouteMapper;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.mapper.EngineerCategoryCapabilityMapper;
import com.itticket.consultation.mapper.EngineerRuntimeStateMapper;
import com.itticket.consultation.mapper.ExceptionQueueItemMapper;
import com.itticket.consultation.mapper.TeamMemberMapper;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * 转人工分配(PRD 8.4、12.1、12.2;防御规则 RD-005)。
 *
 * <p>算法:按末级分类读取有序候选团队 → 团队内筛选 AVAILABLE 且可接该分类的工程师 →
 * 选总加权负载最低者 → 负载相同选最久未收到新任务者 → 当前团队无候选人时试下一团队 →
 * 全部失败进入异常队列。每名候选人对同一咨询最多尝试一次,不无限循环。
 *
 * <p>所有候选数据在调用时实时读取(RD-005:分配前必须读取最新团队成员状态、负载和分类路由版本),
 * 不使用缓存快照。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AssignmentService {

    private final CategoryRouteMapper categoryRouteMapper;
    private final TeamMemberMapper teamMemberMapper;
    private final EngineerCategoryCapabilityMapper capabilityMapper;
    private final EngineerRuntimeStateMapper engineerStateMapper;
    private final AssignmentMapper assignmentMapper;
    private final ConsultationMapper consultationMapper;
    private final ExceptionQueueItemMapper exceptionQueueMapper;
    private final ServiceCalendarProvider calendarProvider;
    private final TicketWorkloadProvider ticketWorkloadProvider;
    private final ConsultationProperties properties;

    /**
     * 为咨询分配下一位候选工程师并创建分配任务。
     * 无候选人时返回空,由调用方决定是否入异常队列。
     */
    public Optional<Assignment> assignNextCandidate(String sessionId, String categoryId, LocalDateTime now) {
        Set<String> tried = triedEngineers(sessionId);
        if (tried.size() >= properties.getTransfer().getMaxCandidates()) {
            log.warn("[assign] 咨询 {} 候选人尝试次数已达上限 {}", sessionId,
                    properties.getTransfer().getMaxCandidates());
            return Optional.empty();
        }

        List<String> teams = orderedTeams(categoryId, now);
        if (teams.isEmpty()) {
            return Optional.empty();
        }

        for (String teamId : teams) {
            Optional<String> picked = pickFromTeam(teamId, categoryId, tried, now);
            if (picked.isPresent()) {
                return Optional.of(createAssignment(sessionId, picked.get(), now));
            }
        }
        return Optional.empty();
    }

    /** PRD 12.1 第 1 步:按末级分类读取有序候选团队,只取当前生效的路由版本。 */
    private List<String> orderedTeams(String categoryId, LocalDateTime now) {
        List<CategoryRoute> routes = categoryRouteMapper.selectList(Wrappers.<CategoryRoute>lambdaQuery()
                .eq(CategoryRoute::getCategoryId, categoryId)
                .le(CategoryRoute::getEffectiveAt, now)
                .and(w -> w.isNull(CategoryRoute::getExpiredAt).or().gt(CategoryRoute::getExpiredAt, now))
                .orderByAsc(CategoryRoute::getRouteOrder));
        List<String> teams = new ArrayList<>(routes.size());
        for (CategoryRoute route : routes) {
            if (!teams.contains(route.getTeamId())) {
                teams.add(route.getTeamId());
            }
        }
        return teams;
    }

    /** PRD 12.1 第 2~4 步。 */
    private Optional<String> pickFromTeam(String teamId, String categoryId, Set<String> tried, LocalDateTime now) {
        List<TeamMember> members = activeMembers(teamId);
        if (members.isEmpty()) {
            return Optional.empty();
        }

        Set<String> capable = capableEngineers(teamId, categoryId, now);
        List<Candidate> candidates = new ArrayList<>();
        for (TeamMember member : members) {
            String engineerId = member.getEngineerId();
            if (tried.contains(engineerId) || teamMemberMapper.countActiveEngineer(engineerId) == 0) {
                continue;
            }
            // capable 为 null 表示该团队未做分类细分,团队路由本身即代表可接该分类。
            if (capable != null && !capable.contains(engineerId)) {
                continue;
            }
            EngineerRuntimeState state = engineerStateMapper.selectById(engineerId);
            // PRD 6.2:只有 AVAILABLE 可分配新咨询;无状态记录视为未上线接待。
            if (state == null || state.getPresence() != EngineerPresence.AVAILABLE) {
                continue;
            }
            candidates.add(new Candidate(engineerId, weightedLoad(engineerId), state.getLastAssignedAt()));
        }
        if (candidates.isEmpty()) {
            return Optional.empty();
        }
        candidates.sort(Comparator
                .comparingInt(Candidate::load)
                // 负载相同时选最久未收到新任务者;从未分配过的排最前。
                .thenComparing(Candidate::lastAssignedAt, Comparator.nullsFirst(Comparator.naturalOrder()))
                .thenComparing(Candidate::engineerId));
        return Optional.of(candidates.get(0).engineerId());
    }

    private List<TeamMember> activeMembers(String teamId) {
        return teamMemberMapper.selectList(Wrappers.<TeamMember>lambdaQuery()
                .eq(TeamMember::getTeamId, teamId)
                .eq(TeamMember::getStatus, "ACTIVE")
                .inSql(TeamMember::getTeamId, "SELECT team_id FROM support_team WHERE status = 'ACTIVE'")
                .isNull(TeamMember::getLeftAt));
    }

    /** 返回该团队在该分类下配置的可接人员;未配置任何能力行时返回 null 表示不做细分过滤。 */
    private Set<String> capableEngineers(String teamId, String categoryId, LocalDateTime now) {
        List<EngineerCategoryCapability> rows = capabilityMapper.selectList(
                Wrappers.<EngineerCategoryCapability>lambdaQuery()
                        .eq(EngineerCategoryCapability::getTeamId, teamId)
                        .eq(EngineerCategoryCapability::getCategoryId, categoryId));
        if (rows.isEmpty()) {
            return null;
        }
        Set<String> capable = new HashSet<>();
        for (EngineerCategoryCapability row : rows) {
            boolean effective = Boolean.TRUE.equals(row.getEnabled())
                    && !row.getEffectiveAt().isAfter(now)
                    && (row.getExpiredAt() == null || row.getExpiredAt().isAfter(now));
            if (effective) {
                capable.add(row.getEngineerId());
            }
        }
        return capable;
    }

    /** PRD 12.2:活跃人工咨询按配置权重计分,工单侧负载由 TicketWorkloadProvider 提供。 */
    private int weightedLoad(String engineerId) {
        Long activeConsultations = consultationMapper.selectCount(Wrappers.<Consultation>lambdaQuery()
                .eq(Consultation::getCurrentEngineerId, engineerId)
                .in(Consultation::getStatus, ConsultationStatus.WAITING_ENGINEER,
                        ConsultationStatus.HUMAN_ACTIVE, ConsultationStatus.PENDING_CONFIRMATION));
        int consultationLoad = (activeConsultations == null ? 0 : activeConsultations.intValue())
                * properties.getTransfer().getConsultationLoadWeight();
        return consultationLoad + ticketWorkloadProvider.weightedTicketLoad(engineerId);
    }

    private Assignment createAssignment(String sessionId, String engineerId, LocalDateTime now) {
        WorkCalendar calendar = calendarProvider.current();
        LocalDateTime deadline = calendar.deadlineUtc(now,
                properties.getSla().getResponseTargetWorkSeconds());

        Assignment assignment = new Assignment();
        assignment.setAssignmentId(Ids.assignmentId());
        assignment.setBizType(AssignmentBizType.CONSULTATION);
        assignment.setBizId(sessionId);
        assignment.setEngineerId(engineerId);
        assignment.setAssignedAt(now);
        assignment.setResponseDeadline(deadline);
        assignment.setCreatedAt(now);
        assignment.setUpdatedAt(now);
        assignmentMapper.insert(assignment);

        // PRD 12.1 第 4 步依赖 lastAssignedAt 做同负载排序,分配后立即推进。
        engineerStateMapper.update(null, Wrappers.<EngineerRuntimeState>lambdaUpdate()
                .eq(EngineerRuntimeState::getEngineerId, engineerId)
                .set(EngineerRuntimeState::getLastAssignedAt, now)
                .set(EngineerRuntimeState::getUpdatedAt, now));
        return assignment;
    }

    /**
     * RD-005:自动响应超时时每名候选人最多尝试一次。
     *
     * <p>只把 end_reason=TIMEOUT 的分配计入"已尝试":曾经正常响应过的工程师不属于失败候选人,
     * 恢复咨询时仍应优先回到他手上(PRD 8.3 恢复规则)。
     */
    public Set<String> triedEngineers(String sessionId) {
        List<Assignment> assignments = assignmentMapper.selectList(Wrappers.<Assignment>lambdaQuery()
                .eq(Assignment::getBizType, AssignmentBizType.CONSULTATION)
                .eq(Assignment::getBizId, sessionId)
                .eq(Assignment::getEndReason, AssignmentEndReason.TIMEOUT));
        Set<String> tried = new HashSet<>(assignments.size());
        for (Assignment assignment : assignments) {
            tried.add(assignment.getEngineerId());
        }
        return tried;
    }

    /**
     * 指定工程师分配,用于 PRD 8.3"恢复咨询优先分配原工程师"。
     * 账号、角色、当前分类路由、团队成员、能力和在线状态均需仍有效，否则回退正常路由。
     */
    public Optional<Assignment> assignPreferred(String sessionId, String engineerId, LocalDateTime now) {
        if (engineerId == null || triedEngineers(sessionId).contains(engineerId)
                || teamMemberMapper.countActiveEngineer(engineerId) == 0) {
            return Optional.empty();
        }
        EngineerRuntimeState state = engineerStateMapper.selectById(engineerId);
        if (state == null || state.getPresence() != EngineerPresence.AVAILABLE) {
            return Optional.empty();
        }
        Consultation consultation = consultationMapper.selectById(sessionId);
        if (consultation == null || consultation.getCategoryId() == null) {
            return Optional.empty();
        }
        for (String teamId : orderedTeams(consultation.getCategoryId(), now)) {
            boolean member = activeMembers(teamId).stream()
                    .anyMatch(row -> engineerId.equals(row.getEngineerId()));
            if (!member) continue;
            Set<String> capable = capableEngineers(teamId, consultation.getCategoryId(), now);
            if (capable == null || capable.contains(engineerId)) {
                return Optional.of(createAssignment(sessionId, engineerId, now));
            }
        }
        return Optional.empty();
    }

    public Optional<Assignment> activeAssignment(String sessionId) {
        return Optional.ofNullable(assignmentMapper.selectOne(Wrappers.<Assignment>lambdaQuery()
                .eq(Assignment::getBizType, AssignmentBizType.CONSULTATION)
                .eq(Assignment::getBizId, sessionId)
                .isNull(Assignment::getEndReason)
                .orderByDesc(Assignment::getAssignedAt)
                .last("LIMIT 1")));
    }

    /**
     * 结束一个分配任务。带 endReason IS NULL 条件,保证同一任务只被结束一次,
     * 重复的超时扫描不会产生第二次转派(RD-004、RD-012)。
     */
    public boolean endAssignment(String assignmentId, AssignmentEndReason reason, LocalDateTime respondedAt) {
        return assignmentMapper.update(null, Wrappers.<Assignment>lambdaUpdate()
                .eq(Assignment::getAssignmentId, assignmentId)
                .isNull(Assignment::getEndReason)
                .set(Assignment::getEndReason, reason)
                .set(Assignment::getRespondedAt, respondedAt)
                .set(Assignment::getUpdatedAt, Times.nowUtc())) > 0;
    }

    /** AI-004.4 要求返回非负等待秒数:取距响应截止时间的剩余秒,已超时按 0。 */
    public long estimatedWaitSeconds(Assignment assignment, LocalDateTime now) {
        if (assignment == null || assignment.getResponseDeadline() == null) {
            return properties.getSla().getResponseTargetWorkSeconds();
        }
        long seconds = Duration.between(now, assignment.getResponseDeadline()).getSeconds();
        return Math.max(seconds, 0L);
    }

    /** 扫描到期的进行中分配任务,供响应超时调度器使用。 */
    public List<Assignment> findOverdueAssignments(LocalDateTime now, int limit) {
        return assignmentMapper.selectList(Wrappers.<Assignment>lambdaQuery()
                .eq(Assignment::getBizType, AssignmentBizType.CONSULTATION)
                .isNull(Assignment::getEndReason)
                .isNotNull(Assignment::getResponseDeadline)
                .le(Assignment::getResponseDeadline, now)
                .orderByAsc(Assignment::getResponseDeadline)
                .last("LIMIT " + limit));
    }

    /** RD-005:候选人耗尽或无路由时进入平台管理员异常队列,同一原因不重复入队。 */
    public void enqueueException(String sessionId, String reasonCode, String reason) {
        LocalDateTime now = Times.nowUtc();
        ExceptionQueueItem item = new ExceptionQueueItem();
        item.setExceptionId(Ids.exceptionId());
        item.setObjectType(ExceptionQueueItem.OBJECT_TYPE_CONSULTATION);
        item.setObjectId(sessionId);
        item.setReasonCode(reasonCode);
        item.setStatus(ExceptionQueueItem.STATUS_OPEN);
        item.setReason(reason);
        item.setCreatedAt(now);
        item.setUpdatedAt(now);
        try {
            exceptionQueueMapper.insert(item);
        } catch (DuplicateKeyException e) {
            log.info("[assign] 咨询 {} 的异常队列条目已存在: {}", sessionId, reasonCode);
        }
    }

    private record Candidate(String engineerId, int load, LocalDateTime lastAssignedAt) {
    }
}
