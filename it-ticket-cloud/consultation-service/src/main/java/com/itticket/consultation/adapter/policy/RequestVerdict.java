package com.itticket.consultation.adapter.policy;
import java.util.Set;
/**
 * 一次判定的完整结果：走哪条路 + 要不要调工具 + 是不是跨工单分析请求。
 *
 * <p>拒答（{@link OfficeDomain#OFF_TOPIC} / {@link OfficeDomain#HIGH_RISK}）、
 * 澄清（{@link OfficeDomain#UNCERTAIN}）、正常作答（{@link OfficeDomain#OFFICE_IT}）
 * 与「调哪个 function」本是同一个决策空间的取值，这里收进一个对象，
 * 由一次判定统一给出 —— 不再由关键词、检索分数各判各的。
 *
 * <p>{@link #tool} 直接用 Python 侧 {@code tool_specs()} 里的工具名，
 * 不在 Java 侧另造一套符号；取值不在白名单内一律视为 {@link #NO_TOOL}。
 *
 * <p>{@link #analytics} 是**第三个独立维度**，刻意不复用 {@code tool}：
 * 跨工单分析走的是确定性聚合链路，不是 function call —— 塞进工具位会让
 * {@code ComposedRagAdapter} 把它当成"工具意图作答"而标记 {@code generalAnswer=true}
 * （那是"无知识依据的通用建议"通道），而分析型回答恰恰有硬数据依据，语义完全不同。
 *
 * <p>不变量在紧凑构造器里收口：{@code tool} 一律归一；{@code analytics} 只可能在
 * {@link OfficeDomain#OFFICE_IT} 下成立 —— 越界与高风险请求没有"做统计"的余地。
 */
public record RequestVerdict(OfficeDomain domain, String tool, boolean analytics) {
    public static final String NO_TOOL = "NONE";
    /** 工具名白名单，与 Python 侧 tool_specs() 的 name 一一对应（防两端漂移，见契约测试）。 */
    public static final Set<String> TOOLS = Set.of("query_my_tickets", "prepare_ticket");

    public RequestVerdict {
        tool = normalize(tool);
        analytics = analytics && domain == OfficeDomain.OFFICE_IT;
    }

    public static RequestVerdict of(OfficeDomain domain, String tool) {
        return new RequestVerdict(domain, tool, false);
    }

    /** 跨工单分析请求：必然落在 OFFICE_IT 域，且不携带工具。 */
    public static RequestVerdict analyticsRequest() {
        return new RequestVerdict(OfficeDomain.OFFICE_IT, NO_TOOL, true);
    }

    /** 白名单外的取值一律归一为 NONE —— 判定器与下游都不必再判合法性。 */
    public static String normalize(String tool) {
        return tool != null && TOOLS.contains(tool) ? tool : NO_TOOL;
    }
}