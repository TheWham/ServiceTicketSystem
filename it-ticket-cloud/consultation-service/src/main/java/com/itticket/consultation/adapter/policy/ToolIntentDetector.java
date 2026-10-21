package com.itticket.consultation.adapter.policy;
import java.util.List;
import java.util.Locale;
/**
 * 工具意图识别 —— 识别「查工单 / 建单」这类应当交给 Function Calling 智能体的请求。
 *
 * <p><b>为什么需要它</b>：agent 的三个工具（查本人工单、产建单草稿、补搜知识）恰恰只在
 * 「预检索没拿到知识」时才被需要；而在 {@link com.itticket.consultation.adapter.ComposedRagAdapter}
 * 里，「检索无果」等价于直接低置信拒答。工具的存在条件与门禁的拦截条件重合，工具因此永不可达
 * （实测：agent 收到 0 次调用）。本类把这类意图认出来，允许其越过该拒答继续生成，由 agent 自己去调工具。
 *
 * <p><b>只在 Function Calling 开启时生效</b>：{@code enabled=false} 时恒返回 false。
 * 未开 agent 时越过拒答只会得到一段无依据的作答 —— 那是放宽拒答策略，不是本次要的。
 *
 * <p><b>词表刻意收窄</b>：只收明确指向工单对象的说法，不含「查询」这类泛动词，
 * 以免把知识问答一并放进来。命中即放行，未命中退回既有行为，故漏词不会带来安全风险，
 * 代价只是少一次走通的工具调用（与 {@code RagRetrievalProperties.officeItKeywords} 同类风险）。
 */
public final class ToolIntentDetector {
    private static final List<String> KEYWORDS = List.of(
            "工单", "报修", "提单", "建单"
    );
    private final boolean enabled;
    public ToolIntentDetector(boolean enabled) {
        this.enabled = enabled;
    }
    /** 该问题是否明确指向工单类工具操作 */
    public boolean matches(String question) {
        if (!enabled || question == null || question.isBlank()) return false;
        String lower = question.toLowerCase(Locale.ROOT);
        for (String keyword : KEYWORDS) {
            if (lower.contains(keyword)) return true;
        }
        return false;
    }
}
