package com.itticket.consultation.service;

import com.itticket.common.web.UserContext;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.statemachine.Actor;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/**
 * 服务端统一授权判定(AX-001)。
 *
 * <p>判定顺序:认证有效 → 角色有效 → 对象存在且可见 → 当前责任关系 → 状态动作守卫。
 * 前四步在本类完成,状态动作守卫由 {@code ConsultationStateMachine} 完成。
 * 按 AX-001「不向无权主体泄露对象存在性」,不可见一律返回 OBJECT_NOT_FOUND 而非 FORBIDDEN。
 */
@Service
@RequiredArgsConstructor
public class AuthzService {

    private final ConsultationProperties properties;

    /** 解析当前主体。缺少网关透传头时 UserContext 会抛出鉴权异常,由异常处理器转 UNAUTHENTICATED。 */
    public CurrentUser currentUser() {
        UserContext.CurrentUser raw = UserContext.get();
        RoleCode role = resolveRole(raw.getRole());
        return new CurrentUser(raw.getUserId(), role, Actor.of(role));
    }

    /**
     * 旧角色值到 DM-002 RoleCode 的映射(AX-005 未决项)。
     * 未配置或未知值按"无咨询权限"处理,不猜测,不降级为员工。
     */
    private RoleCode resolveRole(String rawRole) {
        if (rawRole == null || rawRole.isBlank()) {
            return null;
        }
        String mapped = properties.getRoleMapping().get(rawRole);
        String candidate = mapped == null ? rawRole : mapped;
        try {
            return RoleCode.valueOf(candidate.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /** READ_BASIC:本人咨询、当前负责咨询、平台管理员(AX-006)。 */
    public void requireReadBasic(CurrentUser user, Consultation consultation) {
        if (user.isPlatformAdmin()
                || user.userId().equals(consultation.getCreatorId())
                || user.userId().equals(consultation.getCurrentEngineerId())) {
            return;
        }
        throw ApiException.notFound();
    }

    /**
     * READ_CHAT / SEND_MESSAGE:仅会话参与者。
     * AX-006 未给平台管理员授予咨询聊天权限,历史工程师在咨询表中也无任何条目,一律拒绝。
     */
    public void requireParticipant(CurrentUser user, Consultation consultation) {
        if (user.userId().equals(consultation.getCreatorId())
                || user.userId().equals(consultation.getCurrentEngineerId())) {
            return;
        }
        throw ApiException.notFound();
    }

    /** 只有会话发起员工可执行的动作(转人工、关闭、确认解决、恢复、转工单)。 */
    public void requireCreator(CurrentUser user, Consultation consultation) {
        if (!user.userId().equals(consultation.getCreatorId())) {
            throw ApiException.notFound();
        }
    }

    /**
     * 当前责任工程师校验。
     * SM-001 要求在事务内校验对象归属;责任人已变化时返回 ASSIGNMENT_CHANGED 而非 FORBIDDEN。
     */
    public void requireCurrentEngineer(CurrentUser user, Consultation consultation) {
        if (consultation.getCurrentEngineerId() == null) {
            throw new ApiException(ApiCode.ASSIGNMENT_CHANGED, "该咨询当前没有责任工程师");
        }
        if (!consultation.getCurrentEngineerId().equals(user.userId())) {
            throw new ApiException(ApiCode.ASSIGNMENT_CHANGED, "该咨询的责任工程师已变化");
        }
    }
}
