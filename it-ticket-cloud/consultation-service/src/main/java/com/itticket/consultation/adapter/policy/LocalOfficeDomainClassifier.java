package com.itticket.consultation.adapter.policy;
import com.itticket.consultation.adapter.*;
import java.util.List;
import java.util.Locale;
/** Conservative explicit rules; this is not semantic model classification. */
public final class LocalOfficeDomainClassifier implements OfficeDomainClassifier {
    private static final List<String> HIGH_RISK = List.of("绕过认证", "绕过权限", "提升权限", "修改权限", "提权",
            "破解", "删库", "数据恢复", "恢复丢失", "生产变更", "拆机", "勒索", "安全事件", "rm -rf");
    private static final List<String> OFF_TOPIC = List.of("小说", "电影", "股票", "医疗", "法律", "菜谱", "旅游", "情书", "诗歌");
    private static final List<String> OFFICE = List.of("电脑", "打印", "网络", "邮箱", "会议", "开会", "屏幕",
            "表格", "登录", "密码", "软件", "文件", "连接", "vpn", "excel", "word", "鼠标", "键盘");
    @Override public OfficeDomain classify(RagQuery query, RagCallContext context) {
        context.timeoutMillis(Long.MAX_VALUE);
        String question = query.question().toLowerCase(Locale.ROOT);
        if (HIGH_RISK.stream().anyMatch(question::contains)
                || contains(question, List.of("格式化", "删除", "擦除", "清空", "重置"))
                   && contains(question, List.of("硬盘", "数据库", "生产", "系统", "账户", "账号"))
                || contains(question, List.of("提升", "修改", "绕过", "关闭", "禁用"))
                   && contains(question, List.of("权限", "认证", "防火墙", "安全", "杀毒"))) return OfficeDomain.HIGH_RISK;
        if (OFF_TOPIC.stream().anyMatch(question::contains)) return OfficeDomain.OFF_TOPIC;
        boolean technicalSubject = OFFICE.stream().anyMatch(question::contains);
        boolean symptomOrHelp = contains(question, List.of("故障", "打不开", "不行", "不能", "不上", "听不到",
                "看不到", "没声音", "黑屏", "过期", "错误", "报错", "失败", "卡住", "怎么设置", "如何设置",
                "如何连接", "怎么连接", "如何安装", "怎么安装", "无法", "一直黑"));
        if (technicalSubject && symptomOrHelp) return OfficeDomain.OFFICE_IT;
        return OfficeDomain.UNCERTAIN;
    }
    private static boolean contains(String question, List<String> terms) {
        return terms.stream().anyMatch(question::contains);
    }
}
