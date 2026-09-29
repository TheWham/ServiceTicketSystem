package com.itticket.consultation.statemachine;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.enums.ConsultationStatus;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 咨询状态机(SM-CONSULT-001 的唯一实现)。
 *
 * <p>本类是纯函数,不访问数据库,也不产生副作用。它只回答一个问题:
 * 给定 (当前状态, 业务动作, 操作者类别),这次迁移是否合法、目标状态是什么。
 *
 * <p>SM-001 的两条硬约束在此落实:
 * <ul>
 *   <li>任何未列出的 (当前状态, 事件, 角色) 组合一律拒绝;</li>
 *   <li>客户端不得直接传入目标状态绕过动作白名单 —— 因此入口只接受动作码,不接受目标状态。</li>
 * </ul>
 * 终态默认不可迁移,仅 RESOLVED 允许在窗口内恢复;窗口是否过期由服务层校验(状态机不掌握时间)。
 */
public final class ConsultationStateMachine {

    /** 非终态集合,用于展开迁移表中的"任意非终态"两行。 */
    private static final Set<ConsultationStatus> NON_TERMINAL = EnumSet.of(
            ConsultationStatus.AI_ACTIVE,
            ConsultationStatus.WAITING_ENGINEER,
            ConsultationStatus.HUMAN_ACTIVE,
            ConsultationStatus.PENDING_CONFIRMATION);

    private static final List<TransitionRule> RULES = buildRules();
    /** (当前状态, 动作) → 规则。构建时断言无重复键,避免将来新增行被静默吞掉。 */
    private static final Map<RuleKey, TransitionRule> RULE_INDEX = indexRules(RULES);

    private ConsultationStateMachine() {
    }

    private static List<TransitionRule> buildRules() {
        List<TransitionRule> rules = new ArrayList<>();
        // 起点 | 开始 AI 咨询 | AI_ACTIVE | 员工
        rules.add(TransitionRule.of(null, ConsultationEvent.CONSULTATION_START_AI,
                ConsultationStatus.AI_ACTIVE, Actor.EMPLOYEE));
        // 起点 | 跳过 AI 转人工 | WAITING_ENGINEER | 员工
        rules.add(TransitionRule.of(null, ConsultationEvent.CONSULTATION_START_HUMAN,
                ConsultationStatus.WAITING_ENGINEER, Actor.EMPLOYEE));
        // AI_ACTIVE | 转人工 | WAITING_ENGINEER | 员工
        rules.add(TransitionRule.of(ConsultationStatus.AI_ACTIVE, ConsultationEvent.CONSULTATION_TRANSFER,
                ConsultationStatus.WAITING_ENGINEER, Actor.EMPLOYEE));
        // WAITING_ENGINEER | 首次有效回复 | HUMAN_ACTIVE | 工程师
        rules.add(TransitionRule.of(ConsultationStatus.WAITING_ENGINEER, ConsultationEvent.CONSULTATION_RESPOND,
                ConsultationStatus.HUMAN_ACTIVE, Actor.ENGINEER));
        // HUMAN_ACTIVE | 提交解决结论 | PENDING_CONFIRMATION | 工程师
        rules.add(TransitionRule.of(ConsultationStatus.HUMAN_ACTIVE, ConsultationEvent.CONSULTATION_SUBMIT_RESOLUTION,
                ConsultationStatus.PENDING_CONFIRMATION, Actor.ENGINEER));
        // PENDING_CONFIRMATION | 员工确认解决 | RESOLVED | 员工
        rules.add(TransitionRule.of(ConsultationStatus.PENDING_CONFIRMATION, ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED,
                ConsultationStatus.RESOLVED, Actor.EMPLOYEE));
        // AI_ACTIVE | 员工主动确认 AI 已解决 | RESOLVED | 员工
        rules.add(TransitionRule.of(ConsultationStatus.AI_ACTIVE, ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED,
                ConsultationStatus.RESOLVED, Actor.EMPLOYEE));
        // PENDING_CONFIRMATION | 断开且 10 分钟无回复 | RESOLVED | 系统
        rules.add(TransitionRule.of(ConsultationStatus.PENDING_CONFIRMATION, ConsultationEvent.CONSULTATION_AUTO_RESOLVE,
                ConsultationStatus.RESOLVED, Actor.SYSTEM));
        // PENDING_CONFIRMATION | 员工回复未解决 | HUMAN_ACTIVE | 员工
        rules.add(TransitionRule.of(ConsultationStatus.PENDING_CONFIRMATION, ConsultationEvent.CONSULTATION_REJECT_RESOLUTION,
                ConsultationStatus.HUMAN_ACTIVE, Actor.EMPLOYEE));
        // 任意非终态 | 确认创建工单 | CONVERTED_TO_TICKET | 员工
        // 任意非终态 | 主动结束 | CLOSED | 员工
        for (ConsultationStatus from : NON_TERMINAL) {
            rules.add(TransitionRule.of(from, ConsultationEvent.CONSULTATION_CONVERT,
                    ConsultationStatus.CONVERTED_TO_TICKET, Actor.EMPLOYEE));
            rules.add(TransitionRule.of(from, ConsultationEvent.CONSULTATION_CLOSE,
                    ConsultationStatus.CLOSED, Actor.EMPLOYEE));
        }
        // RESOLVED | 24 小时内恢复 | WAITING_ENGINEER | 员工
        rules.add(TransitionRule.of(ConsultationStatus.RESOLVED, ConsultationEvent.CONSULTATION_REOPEN,
                ConsultationStatus.WAITING_ENGINEER, Actor.EMPLOYEE));
        return List.copyOf(rules);
    }

    /**
     * 判定一次迁移是否合法。
     *
     * @param from   当前状态;null 表示起点
     * @param event  业务动作码
     * @param actor  操作者类别;null 表示该角色不参与咨询迁移,直接拒绝
     */
    public static TransitionDecision evaluate(ConsultationStatus from, ConsultationEvent event, Actor actor) {
        TransitionRule rule = RULE_INDEX.get(new RuleKey(from, event));
        if (rule == null) {
            return TransitionDecision.deny(ApiCode.ILLEGAL_STATE_TRANSITION,
                    "当前状态 " + describe(from) + " 不允许执行 " + event.name());
        }
        if (actor == null || !rule.actors().contains(actor)) {
            return TransitionDecision.deny(ApiCode.FORBIDDEN,
                    "当前角色无权执行 " + event.name());
        }
        return TransitionDecision.allow(rule.to());
    }

    /** 某状态下允许的动作,供前端按钮可见性与测试断言使用。 */
    public static Set<ConsultationEvent> allowedEvents(ConsultationStatus from, Actor actor) {
        return RULES.stream()
                .filter(rule -> rule.from() == from && actor != null && rule.actors().contains(actor))
                .map(TransitionRule::event)
                .collect(java.util.stream.Collectors.toCollection(() -> EnumSet.noneOf(ConsultationEvent.class)));
    }

    static List<TransitionRule> rules() {
        return RULES;
    }

    private static Map<RuleKey, TransitionRule> indexRules(List<TransitionRule> rules) {
        Map<RuleKey, TransitionRule> index = new HashMap<>(rules.size());
        for (TransitionRule rule : rules) {
            TransitionRule previous = index.put(new RuleKey(rule.from(), rule.event()), rule);
            if (previous != null) {
                throw new IllegalStateException(
                        "SM-CONSULT-001 迁移表存在重复的 (状态, 动作) 组合: "
                                + rule.from() + " / " + rule.event());
            }
        }
        return Map.copyOf(index);
    }

    private record RuleKey(ConsultationStatus from, ConsultationEvent event) {
    }

    private static String describe(ConsultationStatus status) {
        return status == null ? "起点" : status.getValue();
    }
}
