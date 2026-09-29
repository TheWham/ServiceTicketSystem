package com.itticket.consultation.statemachine;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.RoleCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SM-CONSULT-001 咨询状态机纯单元测试。
 *
 * <p>契约来源:
 * <ul>
 *   <li>docs/specs/03-business-state-machine.md 的 SM-CONSULT-001 迁移表(逐行穷尽覆盖);</li>
 *   <li>SM-001「任何未列出的 (当前状态, 事件, 角色) 组合均拒绝」「终态默认不可迁移」;</li>
 *   <li>PRD 8.2 / 8.3 咨询状态与流转、PRD 24.2 的 AC-03 / AC-04 / AC-05;</li>
 *   <li>AX-006:PLATFORM_ADMIN / KNOWLEDGE_ADMIN 不在咨询迁移表内,不得获得迁移权。</li>
 * </ul>
 *
 * <p>测试名按 TR-001 携带 F-03 / AC-03 / AC-04 / AC-05 标识。
 */
class ConsultationStateMachineTest {

    /** 含员工主动确认 AI 已解决的迁移，共 18 行。 */
    private static final int EXPECTED_RULE_COUNT = 18;

    @Test
    void employeeCanConfirmAiAnswerResolvedButEngineerCannot() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(ConsultationStatus.AI_ACTIVE,
                ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, Actor.EMPLOYEE);
        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.RESOLVED);
        assertThat(ConsultationStateMachine.evaluate(ConsultationStatus.AI_ACTIVE,
                ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, Actor.ENGINEER).allowed()).isFalse();
    }

    /** 迁移表中 from 非 null 的行数(起点两行不落在 ConsultationStatus 笛卡尔积内)。 */
    private static final int EXPECTED_ALLOWED_COMBINATIONS = EXPECTED_RULE_COUNT - 2;

    private static final Set<ConsultationStatus> NON_TERMINAL = EnumSet.of(
            ConsultationStatus.AI_ACTIVE,
            ConsultationStatus.WAITING_ENGINEER,
            ConsultationStatus.HUMAN_ACTIVE,
            ConsultationStatus.PENDING_CONFIRMATION);

    // ------------------------------------------------------------------
    // 一、迁移表合法行逐行覆盖
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-03 起点 | 开始 AI 咨询 | AI_ACTIVE | 员工")
    void f03_start_ai_from_scratch_goes_to_ai_active() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                null, ConsultationEvent.CONSULTATION_START_AI, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.AI_ACTIVE);
        assertThat(decision.failureCode()).isNull();
        assertThat(decision.message()).isNull();
    }

    @Test
    @DisplayName("AC-03 起点 | 跳过 AI 直接转人工 | WAITING_ENGINEER | 员工")
    void ac03_start_human_from_scratch_goes_to_waiting_engineer() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                null, ConsultationEvent.CONSULTATION_START_HUMAN, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.WAITING_ENGINEER);
    }

    @Test
    @DisplayName("AC-03 AI_ACTIVE | 转人工 | WAITING_ENGINEER | 员工")
    void ac03_transfer_from_ai_active_goes_to_waiting_engineer() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.AI_ACTIVE, ConsultationEvent.CONSULTATION_TRANSFER, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.WAITING_ENGINEER);
    }

    @Test
    @DisplayName("AC-03 WAITING_ENGINEER | 工程师首次有效回复 | HUMAN_ACTIVE | 工程师")
    void ac03_respond_from_waiting_engineer_goes_to_human_active() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.WAITING_ENGINEER, ConsultationEvent.CONSULTATION_RESPOND, Actor.ENGINEER);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.HUMAN_ACTIVE);
    }

    @Test
    @DisplayName("AC-04 HUMAN_ACTIVE | 提交解决结论 | PENDING_CONFIRMATION | 工程师")
    void ac04_submit_resolution_from_human_active_goes_to_pending_confirmation() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.HUMAN_ACTIVE, ConsultationEvent.CONSULTATION_SUBMIT_RESOLUTION, Actor.ENGINEER);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.PENDING_CONFIRMATION);
    }

    @Test
    @DisplayName("AC-04 PENDING_CONFIRMATION | 员工确认解决 | RESOLVED | 员工")
    void ac04_confirm_resolved_from_pending_confirmation_goes_to_resolved() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.PENDING_CONFIRMATION,
                ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.RESOLVED);
    }

    @Test
    @DisplayName("AC-04 PENDING_CONFIRMATION | 断开且 10 分钟无回复 | RESOLVED | 系统")
    void ac04_auto_resolve_from_pending_confirmation_goes_to_resolved() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.PENDING_CONFIRMATION,
                ConsultationEvent.CONSULTATION_AUTO_RESOLVE, Actor.SYSTEM);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.RESOLVED);
    }

    @Test
    @DisplayName("AC-04 PENDING_CONFIRMATION | 员工回复未解决 | HUMAN_ACTIVE | 员工")
    void ac04_reject_resolution_from_pending_confirmation_goes_back_to_human_active() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.PENDING_CONFIRMATION,
                ConsultationEvent.CONSULTATION_REJECT_RESOLUTION, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        assertThat(decision.to()).isEqualTo(ConsultationStatus.HUMAN_ACTIVE);
    }

    @Test
    @DisplayName("AC-05 RESOLVED | 24 小时内恢复 | WAITING_ENGINEER | 员工")
    void ac05_reopen_from_resolved_goes_to_waiting_engineer() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.RESOLVED, ConsultationEvent.CONSULTATION_REOPEN, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isTrue();
        // 恢复回到 WAITING_ENGINEER 而非 HUMAN_ACTIVE:SM-CONSULT-001 要求重新启动人工响应 SLA
        assertThat(decision.to()).isEqualTo(ConsultationStatus.WAITING_ENGINEER);
    }

    @Test
    @DisplayName("F-03 任意非终态 | 确认创建工单 | CONVERTED_TO_TICKET | 员工(4 个非终态逐个覆盖)")
    void f03_convert_is_allowed_from_every_non_terminal_state() {
        for (ConsultationStatus from : NON_TERMINAL) {
            TransitionDecision decision = ConsultationStateMachine.evaluate(
                    from, ConsultationEvent.CONSULTATION_CONVERT, Actor.EMPLOYEE);

            assertThat(decision.allowed())
                    .as("非终态 %s 应允许员工确认创建工单", from)
                    .isTrue();
            assertThat(decision.to()).isEqualTo(ConsultationStatus.CONVERTED_TO_TICKET);
        }
    }

    @Test
    @DisplayName("F-03 任意非终态 | 员工主动结束 | CLOSED | 员工(4 个非终态逐个覆盖)")
    void f03_close_is_allowed_from_every_non_terminal_state() {
        for (ConsultationStatus from : NON_TERMINAL) {
            TransitionDecision decision = ConsultationStateMachine.evaluate(
                    from, ConsultationEvent.CONSULTATION_CLOSE, Actor.EMPLOYEE);

            assertThat(decision.allowed())
                    .as("非终态 %s 应允许员工主动结束", from)
                    .isTrue();
            assertThat(decision.to()).isEqualTo(ConsultationStatus.CLOSED);
        }
    }

    @Test
    @DisplayName("F-03 非终态集合恰为 4 个,且与 ConsultationStatus.isTerminal() 一致")
    void f03_non_terminal_set_matches_status_enum() {
        for (ConsultationStatus status : ConsultationStatus.values()) {
            assertThat(status.isTerminal())
                    .as("状态 %s 的终态判定应与 SM-CONSULT-001 一致", status)
                    .isEqualTo(!NON_TERMINAL.contains(status));
        }
        assertThat(NON_TERMINAL).hasSize(4);
    }

    // ------------------------------------------------------------------
    // 二、负例:状态不匹配 -> ILLEGAL_STATE_TRANSITION(SM-001)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-04 AI_ACTIVE 下提交解决结论被拒:ILLEGAL_STATE_TRANSITION")
    void ac04_submit_resolution_in_ai_active_is_illegal_state() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.AI_ACTIVE,
                ConsultationEvent.CONSULTATION_SUBMIT_RESOLUTION, Actor.ENGINEER);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
        assertThat(decision.to()).isNull();
        assertThat(decision.message()).contains("CONSULTATION_SUBMIT_RESOLUTION");
    }

    @Test
    @DisplayName("AC-04 WAITING_ENGINEER 下员工确认解决被拒:ILLEGAL_STATE_TRANSITION")
    void ac04_confirm_resolved_in_waiting_engineer_is_illegal_state() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.WAITING_ENGINEER,
                ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
    }

    @Test
    @DisplayName("AC-03 AI_ACTIVE 下工程师回复被拒:CONSULTATION_RESPOND 只在 WAITING_ENGINEER 合法")
    void ac03_respond_in_ai_active_is_illegal_state() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.AI_ACTIVE, ConsultationEvent.CONSULTATION_RESPOND, Actor.ENGINEER);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
    }

    @Test
    @DisplayName("AC-05 非 RESOLVED 状态执行恢复被拒:ILLEGAL_STATE_TRANSITION")
    void ac05_reopen_outside_resolved_is_illegal_state() {
        for (ConsultationStatus from : ConsultationStatus.values()) {
            if (from == ConsultationStatus.RESOLVED) {
                continue;
            }
            TransitionDecision decision = ConsultationStateMachine.evaluate(
                    from, ConsultationEvent.CONSULTATION_REOPEN, Actor.EMPLOYEE);

            assertThat(decision.allowed()).as("%s 不应允许恢复", from).isFalse();
            assertThat(decision.failureCode()).isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
        }
    }

    @Test
    @DisplayName("AC-03 已存在会话时重复执行起点动作被拒(起点动作只在 from=null 合法)")
    void ac03_start_events_are_rejected_on_existing_session() {
        for (ConsultationStatus from : ConsultationStatus.values()) {
            assertThat(ConsultationStateMachine.evaluate(
                    from, ConsultationEvent.CONSULTATION_START_AI, Actor.EMPLOYEE).failureCode())
                    .as("%s 不应允许重新开始 AI 咨询", from)
                    .isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
            assertThat(ConsultationStateMachine.evaluate(
                    from, ConsultationEvent.CONSULTATION_START_HUMAN, Actor.EMPLOYEE).failureCode())
                    .as("%s 不应允许重新开始人工咨询", from)
                    .isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
        }
    }

    // ------------------------------------------------------------------
    // 三、负例:状态匹配但角色不对 -> FORBIDDEN(SM-001)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-03 员工执行 CONSULTATION_RESPOND 被拒:FORBIDDEN")
    void ac03_employee_cannot_respond_as_engineer() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.WAITING_ENGINEER, ConsultationEvent.CONSULTATION_RESPOND, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
        assertThat(decision.to()).isNull();
    }

    @Test
    @DisplayName("AC-03 工程师执行 CONSULTATION_CLOSE 被拒:主动结束只属于员工")
    void ac03_engineer_cannot_close_consultation() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.HUMAN_ACTIVE, ConsultationEvent.CONSULTATION_CLOSE, Actor.ENGINEER);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
    }

    @Test
    @DisplayName("AC-04 系统执行 CONSULTATION_CONFIRM_RESOLVED 被拒:确认解决只属于员工")
    void ac04_system_cannot_confirm_resolution_on_behalf_of_employee() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.PENDING_CONFIRMATION,
                ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, Actor.SYSTEM);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
    }

    @Test
    @DisplayName("AC-04 员工执行 CONSULTATION_AUTO_RESOLVE 被拒:自动解决只属于系统")
    void ac04_employee_cannot_trigger_auto_resolve() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.PENDING_CONFIRMATION,
                ConsultationEvent.CONSULTATION_AUTO_RESOLVE, Actor.EMPLOYEE);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
    }

    @Test
    @DisplayName("AC-03 工程师或系统执行起点动作被拒:创建会话只属于员工")
    void ac03_engineer_cannot_start_consultation() {
        assertThat(ConsultationStateMachine.evaluate(
                null, ConsultationEvent.CONSULTATION_START_AI, Actor.ENGINEER).failureCode())
                .isEqualTo(ApiCode.FORBIDDEN);
        assertThat(ConsultationStateMachine.evaluate(
                null, ConsultationEvent.CONSULTATION_START_HUMAN, Actor.ENGINEER).failureCode())
                .isEqualTo(ApiCode.FORBIDDEN);
        assertThat(ConsultationStateMachine.evaluate(
                null, ConsultationEvent.CONSULTATION_START_AI, Actor.SYSTEM).failureCode())
                .isEqualTo(ApiCode.FORBIDDEN);
    }

    @Test
    @DisplayName("AC-05 工程师执行 CONSULTATION_REOPEN 被拒:恢复只属于员工")
    void ac05_engineer_cannot_reopen_consultation() {
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                ConsultationStatus.RESOLVED, ConsultationEvent.CONSULTATION_REOPEN, Actor.ENGINEER);

        assertThat(decision.allowed()).isFalse();
        assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
    }

    // ------------------------------------------------------------------
    // 四、AX-006:管理员角色不参与咨询迁移
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-03 RoleCode 到 Actor 的映射:管理员角色不参与咨询迁移,返回 null")
    void f03_actor_of_maps_only_employee_and_engineer() {
        assertThat(Actor.of(RoleCode.EMPLOYEE)).isEqualTo(Actor.EMPLOYEE);
        assertThat(Actor.of(RoleCode.ENGINEER)).isEqualTo(Actor.ENGINEER);
        assertThat(Actor.of(RoleCode.PLATFORM_ADMIN)).isNull();
        assertThat(Actor.of(RoleCode.KNOWLEDGE_ADMIN)).isNull();
        assertThat(Actor.of(null)).isNull();
    }

    @Test
    @DisplayName("F-03 管理员(Actor 为 null)执行迁移表中任何一行都返回 FORBIDDEN")
    void f03_admin_roles_are_forbidden_on_every_transition() {
        Actor platformAdmin = Actor.of(RoleCode.PLATFORM_ADMIN);
        Actor knowledgeAdmin = Actor.of(RoleCode.KNOWLEDGE_ADMIN);

        for (TransitionRule rule : ConsultationStateMachine.rules()) {
            for (Actor admin : new Actor[]{platformAdmin, knowledgeAdmin}) {
                TransitionDecision decision =
                        ConsultationStateMachine.evaluate(rule.from(), rule.event(), admin);

                assertThat(decision.allowed())
                        .as("管理员不应被允许执行 %s / %s", rule.from(), rule.event())
                        .isFalse();
                assertThat(decision.failureCode()).isEqualTo(ApiCode.FORBIDDEN);
            }
        }
    }

    // ------------------------------------------------------------------
    // 五、终态不可迁移(SM-001)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-03 CONVERTED_TO_TICKET 与 CLOSED 为终态:任何动作、任何角色都被拒")
    void f03_terminal_states_reject_every_event() {
        for (ConsultationStatus terminal : EnumSet.of(
                ConsultationStatus.CONVERTED_TO_TICKET, ConsultationStatus.CLOSED)) {
            for (ConsultationEvent event : ConsultationEvent.values()) {
                for (Actor actor : Actor.values()) {
                    TransitionDecision decision =
                            ConsultationStateMachine.evaluate(terminal, event, actor);

                    assertThat(decision.allowed())
                            .as("终态 %s 不应允许 %s / %s", terminal, event, actor)
                            .isFalse();
                    assertThat(decision.failureCode()).isEqualTo(ApiCode.ILLEGAL_STATE_TRANSITION);
                }
            }
        }
    }

    @Test
    @DisplayName("AC-05 RESOLVED 只接受员工的 CONSULTATION_REOPEN,其余动作一律拒绝")
    void ac05_resolved_only_accepts_reopen() {
        for (ConsultationEvent event : ConsultationEvent.values()) {
            for (Actor actor : Actor.values()) {
                TransitionDecision decision =
                        ConsultationStateMachine.evaluate(ConsultationStatus.RESOLVED, event, actor);

                boolean expectedAllowed = event == ConsultationEvent.CONSULTATION_REOPEN
                        && actor == Actor.EMPLOYEE;
                assertThat(decision.allowed())
                        .as("RESOLVED / %s / %s", event, actor)
                        .isEqualTo(expectedAllowed);
                if (!expectedAllowed) {
                    assertThat(decision.failureCode())
                            .isIn(ApiCode.ILLEGAL_STATE_TRANSITION, ApiCode.FORBIDDEN);
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // 六、规则表自身一致性:防止将来误加规则
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-03 迁移表行数恰为 SM-CONSULT-001 展开后的 17 行,且无重复 (状态, 动作) 键")
    void f03_rule_table_size_matches_spec() {
        assertThat(ConsultationStateMachine.rules()).hasSize(EXPECTED_RULE_COUNT);

        Set<String> keys = new HashSet<>();
        for (TransitionRule rule : ConsultationStateMachine.rules()) {
            assertThat(keys.add(rule.from() + "/" + rule.event()))
                    .as("迁移表不应存在重复的 (状态, 动作) 键: %s / %s", rule.from(), rule.event())
                    .isTrue();
            // 迁移表中没有「多角色共享」的行,每行只授权唯一一个操作者类别
            assertThat(rule.actors())
                    .as("迁移表行 %s / %s 应只授权一个操作者类别", rule.from(), rule.event())
                    .hasSize(1);
        }
        assertThat(keys).hasSize(EXPECTED_RULE_COUNT);
    }

    @Test
    @DisplayName("F-03 全笛卡尔积中被允许的组合数恰好等于迁移表非起点行数(SM-001 默认拒绝)")
    void f03_only_spec_listed_combinations_are_allowed() {
        int allowed = 0;
        for (ConsultationStatus from : ConsultationStatus.values()) {
            for (ConsultationEvent event : ConsultationEvent.values()) {
                for (Actor actor : Actor.values()) {
                    if (ConsultationStateMachine.evaluate(from, event, actor).allowed()) {
                        allowed++;
                    }
                }
            }
        }
        assertThat(allowed).isEqualTo(EXPECTED_ALLOWED_COMBINATIONS);
    }

    @Test
    @DisplayName("F-03 被允许的组合目标状态必须与迁移表一致,且放行时 failureCode 恒为 null")
    void f03_allowed_decisions_carry_spec_target_state() {
        for (TransitionRule rule : ConsultationStateMachine.rules()) {
            Actor actor = rule.actors().iterator().next();
            TransitionDecision decision =
                    ConsultationStateMachine.evaluate(rule.from(), rule.event(), actor);

            assertThat(decision.allowed())
                    .as("迁移表行 %s / %s 应被放行", rule.from(), rule.event())
                    .isTrue();
            assertThat(decision.to()).isEqualTo(rule.to());
            assertThat(decision.failureCode()).isNull();
        }
    }

    // ------------------------------------------------------------------
    // 七、allowedEvents:前端按钮可见性
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-03 起点可用动作:员工可开始 AI 或直接转人工,工程师与系统无动作")
    void f03_allowed_events_at_origin() {
        assertThat(ConsultationStateMachine.allowedEvents(null, Actor.EMPLOYEE))
                .containsExactlyInAnyOrder(
                        ConsultationEvent.CONSULTATION_START_AI,
                        ConsultationEvent.CONSULTATION_START_HUMAN);
        assertThat(ConsultationStateMachine.allowedEvents(null, Actor.ENGINEER)).isEmpty();
        assertThat(ConsultationStateMachine.allowedEvents(null, Actor.SYSTEM)).isEmpty();
    }

    @Test
    @DisplayName("AC-03 AI_ACTIVE 与 WAITING_ENGINEER 下各角色可用动作集合")
    void ac03_allowed_events_in_ai_and_waiting_states() {
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.AI_ACTIVE, Actor.EMPLOYEE))
                .containsExactlyInAnyOrder(
                        ConsultationEvent.CONSULTATION_TRANSFER,
                        ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED,
                        ConsultationEvent.CONSULTATION_CONVERT,
                        ConsultationEvent.CONSULTATION_CLOSE);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.AI_ACTIVE, Actor.ENGINEER)).isEmpty();
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.AI_ACTIVE, Actor.SYSTEM)).isEmpty();

        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.WAITING_ENGINEER, Actor.ENGINEER))
                .containsExactly(ConsultationEvent.CONSULTATION_RESPOND);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.WAITING_ENGINEER, Actor.EMPLOYEE))
                .containsExactlyInAnyOrder(
                        ConsultationEvent.CONSULTATION_CONVERT,
                        ConsultationEvent.CONSULTATION_CLOSE);
    }

    @Test
    @DisplayName("AC-04 HUMAN_ACTIVE 与 PENDING_CONFIRMATION 下各角色可用动作集合")
    void ac04_allowed_events_in_human_and_pending_states() {
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.HUMAN_ACTIVE, Actor.ENGINEER))
                .containsExactly(ConsultationEvent.CONSULTATION_SUBMIT_RESOLUTION);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.HUMAN_ACTIVE, Actor.EMPLOYEE))
                .containsExactlyInAnyOrder(
                        ConsultationEvent.CONSULTATION_CONVERT,
                        ConsultationEvent.CONSULTATION_CLOSE);

        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.PENDING_CONFIRMATION, Actor.EMPLOYEE))
                .containsExactlyInAnyOrder(
                        ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED,
                        ConsultationEvent.CONSULTATION_REJECT_RESOLUTION,
                        ConsultationEvent.CONSULTATION_CONVERT,
                        ConsultationEvent.CONSULTATION_CLOSE);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.PENDING_CONFIRMATION, Actor.SYSTEM))
                .containsExactly(ConsultationEvent.CONSULTATION_AUTO_RESOLVE);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.PENDING_CONFIRMATION, Actor.ENGINEER))
                .isEmpty();
    }

    @Test
    @DisplayName("AC-05 终态可用动作:仅 RESOLVED 对员工暴露恢复,其余终态全空")
    void ac05_allowed_events_in_terminal_states() {
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.RESOLVED, Actor.EMPLOYEE))
                .containsExactly(ConsultationEvent.CONSULTATION_REOPEN);
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.RESOLVED, Actor.ENGINEER)).isEmpty();
        assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.RESOLVED, Actor.SYSTEM)).isEmpty();

        for (Actor actor : Actor.values()) {
            assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.CONVERTED_TO_TICKET, actor))
                    .as("CONVERTED_TO_TICKET 对 %s 不应暴露任何动作", actor)
                    .isEmpty();
            assertThat(ConsultationStateMachine.allowedEvents(ConsultationStatus.CLOSED, actor))
                    .as("CLOSED 对 %s 不应暴露任何动作", actor)
                    .isEmpty();
        }
    }

    @Test
    @DisplayName("F-03 actor 为 null(管理员)时 allowedEvents 恒为空集")
    void f03_allowed_events_is_empty_for_null_actor() {
        assertThat(ConsultationStateMachine.allowedEvents(null, null)).isEmpty();
        for (ConsultationStatus status : ConsultationStatus.values()) {
            assertThat(ConsultationStateMachine.allowedEvents(status, null))
                    .as("状态 %s 对无咨询权限的角色不应暴露任何动作", status)
                    .isEmpty();
        }
    }

    @Test
    @DisplayName("F-03 allowedEvents 与 evaluate 结论一致:集合内必放行,集合外必拒绝")
    void f03_allowed_events_is_consistent_with_evaluate() {
        for (ConsultationStatus from : ConsultationStatus.values()) {
            for (Actor actor : Actor.values()) {
                Set<ConsultationEvent> allowed = ConsultationStateMachine.allowedEvents(from, actor);
                for (ConsultationEvent event : ConsultationEvent.values()) {
                    assertThat(ConsultationStateMachine.evaluate(from, event, actor).allowed())
                            .as("%s / %s / %s", from, event, actor)
                            .isEqualTo(allowed.contains(event));
                }
            }
        }
    }
}
