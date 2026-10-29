package com.itticket.consultation.adapter.policy;
import com.itticket.consultation.adapter.*;
import java.util.List;
import java.util.Locale;
/**
 * 关键词兜底判定 —— 判定的降级路径（链路第 ① 环，全景图见 package-info）。
 *
 * <p>何时轮到它：① 装配 provider=local（不接模型）；② {@link SemanticRequestClassifier}
 * 遇到「模型输出不合法」（INVALID_RESPONSE）整条退回这里。传输层失败不走这里（上抛给断路器）。
 *
 * <p>语义方向：保守规则，不匹配即 UNCERTAIN（宁可澄清不可乱答）——降级期间
 * 可用性下降但安全方向不变。规则与词表的取舍见各字段注释。
 */
public final class KeywordRequestClassifier implements RequestClassifier {
    private static final List<String> HIGH_RISK = List.of("绕过认证", "绕过权限", "提升权限", "修改权限", "提权",
            "破解", "删库", "数据恢复", "恢复丢失", "生产变更", "拆机", "勒索", "安全事件", "rm -rf");
    private static final List<String> OFF_TOPIC = List.of("小说", "电影", "股票", "医疗", "法律", "菜谱", "旅游", "情书", "诗歌");
    private static final List<String> OFFICE = List.of("电脑", "打印", "网络", "邮箱", "会议", "开会", "屏幕",
            "表格", "登录", "密码", "软件", "文件", "连接", "vpn", "excel", "word", "鼠标", "键盘");
    // 工具意图的关键词兜底（模型不可用时的降级路径）。动作动词优先于对象：
    // 「提交工单」是建单，「工单状态」是查询，先判建单再判查询。
    // 口语会把两字词拆开（「提个单」不含「提单」），常见拆法要逐个收录。
    private static final List<String> CREATE_TOOL = List.of("报修", "提单", "建单", "提交工单",
            "提个单", "提张单", "建个单", "开个单", "报个修", "报修单");
    private static final List<String> QUERY_TOOL = List.of("工单");
    // 跨工单分析的兜底关键词。强信号单独即可定性；弱信号必须叠加「时间范围」或
    // 「集合范围」才成立 —— 「帮我总结一下这个报错」里有"总结"但不是分析题，
    // 靠叠加条件把它排除掉。这套阈值与 Python 侧 analytics_service.classifier
    // 的 rule_route 是同构的，两边都要维护，改动时记得对齐。
    private static final List<String> ANALYTICS_STRONG = List.of("共性根因", "共性问题", "采购建议",
            "巡检建议", "全面总结", "综合分析", "占比", "分布情况", "趋势分析", "规律", "盘点");
    private static final List<String> ANALYTICS_WEAK = List.of("总结", "归纳", "汇总", "统计", "分布",
            "趋势", "根因", "分析", "建议", "展望");
    private static final List<String> ANALYTICS_WINDOW = List.of("本季度", "这个季度", "这季度", "上季度",
            "上一季度", "本月", "这个月", "上个月", "今年", "当季");
    private static final List<String> ANALYTICS_SCOPE = List.of("全部", "所有", "整体", "跨", "数十",
            "各大类", "各类", "哪些类型");
    // 相对时间范围（"近 90 天""最近 3 个月""Q2""2026 年"）与季度词表合起来才算覆盖完整 ——
    // 只列固定词会漏掉「分析近 90 天的趋势」这类说法（单测实测踩到过）。
    private static final java.util.regex.Pattern ANALYTICS_WINDOW_RE =
            java.util.regex.Pattern.compile(
                    "(?:近|最近|过去|前)\\s*\\d+\\s*(?:天|日|周|个?星期|个?月)|\\bq[1-4]\\b|20\\d{2}\\s*年");
    @Override public RequestVerdict classify(RagQuery query, RagCallContext context) {
        context.timeoutMillis(Long.MAX_VALUE);
        String question = query.question().toLowerCase(Locale.ROOT);
        if (HIGH_RISK.stream().anyMatch(question::contains)
                || contains(question, List.of("格式化", "删除", "擦除", "清空", "重置"))
                   && contains(question, List.of("硬盘", "数据库", "生产", "系统", "账户", "账号"))
                || contains(question, List.of("提升", "修改", "绕过", "关闭", "禁用"))
                   && contains(question, List.of("权限", "认证", "防火墙", "安全", "杀毒")))
            return RequestVerdict.of(OfficeDomain.HIGH_RISK, RequestVerdict.NO_TOOL);
        if (OFF_TOPIC.stream().anyMatch(question::contains))
            return RequestVerdict.of(OfficeDomain.OFF_TOPIC, RequestVerdict.NO_TOOL);
        String tool = toolIntent(question);
        // 分析型请求优先于工具位：它走确定性聚合链路，不是 function call。
        // 也刻意不走下面的 technicalSubject/symptomOrHelp 判据 —— 「统计本季度工单分布」
        // 既没有故障词也不是"求助排查"，那条判据会把它落到 UNCERTAIN（要求澄清），
        // 而它其实是本域内一个明确的、可执行的请求。
        if (analyticsIntent(question)) return RequestVerdict.analyticsRequest();
        boolean technicalSubject = OFFICE.stream().anyMatch(question::contains);
        boolean symptomOrHelp = contains(question, List.of("故障", "打不开", "不行", "不能", "不上", "听不到",
                "看不到", "没声音", "黑屏", "过期", "错误", "报错", "失败", "卡住", "怎么设置", "如何设置",
                "如何连接", "怎么连接", "如何安装", "怎么安装", "无法", "一直黑"));
        if (technicalSubject && symptomOrHelp) return RequestVerdict.of(OfficeDomain.OFFICE_IT, tool);
        return RequestVerdict.of(OfficeDomain.UNCERTAIN, tool);
    }
    /** 工具意图兜底：命中即给具体工具名，供门禁放行判断使用。 */
    private static String toolIntent(String question) {
        if (CREATE_TOOL.stream().anyMatch(question::contains)) return "prepare_ticket";
        if (QUERY_TOOL.stream().anyMatch(question::contains)) return "query_my_tickets";
        return RequestVerdict.NO_TOOL;
    }
    /** 分析意图兜底：强信号直接命中；弱信号需叠加时间或集合范围。 */
    private static boolean analyticsIntent(String question) {
        if (ANALYTICS_STRONG.stream().anyMatch(question::contains)) return true;
        if (ANALYTICS_WEAK.stream().noneMatch(question::contains)) return false;
        return ANALYTICS_WINDOW.stream().anyMatch(question::contains)
                || ANALYTICS_SCOPE.stream().anyMatch(question::contains)
                || ANALYTICS_WINDOW_RE.matcher(question).find();
    }
    private static boolean contains(String question, List<String> terms) {
        return terms.stream().anyMatch(question::contains);
    }
}
