package com.itticket.consultation.adapter.policy;
import java.util.Set;
/**
 * 一次判定的完整结果：走哪条路 + 要不要调工具。
 *
 * <p>拒答（{@link OfficeDomain#OFF_TOPIC} / {@link OfficeDomain#HIGH_RISK}）、
 * 澄清（{@link OfficeDomain#UNCERTAIN}）、正常作答（{@link OfficeDomain#OFFICE_IT}）
 * 与「调哪个 function」本是同一个决策空间的取值，这里收进一个对象，
 * 由一次判定统一给出 —— 不再由关键词、检索分数各判各的。
 *
 * <p>{@link #tool} 直接用 Python 侧 {@code tool_specs()} 里的工具名，
 * 不在 Java 侧另造一套符号；取值不在白名单内一律视为 {@link #NO_TOOL}。
 */
public record RequestVerdict(OfficeDomain domain, String tool) {
    public static final String NO_TOOL = "NONE";
    /** 工具名白名单，与 Python 侧 tool_specs() 的 name 一一对应（防两端漂移，见契约测试）。 */
    public static final Set<String> TOOLS = Set.of("query_my_tickets", "prepare_ticket");

    public static RequestVerdict of(OfficeDomain domain, String tool) {
        return new RequestVerdict(domain, normalize(tool));
    }

    /** 白名单外的取值一律归一为 NONE —— 判定器与下游都不必再判合法性。 */
    public static String normalize(String tool) {
        return tool != null && TOOLS.contains(tool) ? tool : NO_TOOL;
    }
}
