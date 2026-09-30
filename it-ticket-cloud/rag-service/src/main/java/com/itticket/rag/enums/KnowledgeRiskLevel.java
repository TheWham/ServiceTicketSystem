package com.itticket.rag.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 知识风险等级 —— 契约 DM-002 枚举目录（specs/01-data-model-strong-types.md:41）值域为 NORMAL / HIGH。
 *
 * <p>线上存量数据与上传接口历史上出现过 LOW / MEDIUM，故保留声明以兼容读取；
 * 写入前统一经 {@link #normalize()} 归一，避免出现第三、第四种落库值。
 * 高风险知识的发布守卫见 PRD §16.4（IT服务工单系统PRD-Ultimate.md:515）。</p>
 */
public enum KnowledgeRiskLevel {
    /** 常规知识 */
    NORMAL("NORMAL"),
    /** 高风险知识（账号权限/安全事件/数据丢失/高风险命令/硬件拆修），发布须平台管理员复核 */
    HIGH("HIGH"),

    // 兼容历史值域，不作为新写入值
    @Deprecated
    LOW("LOW"),
    @Deprecated
    MEDIUM("MEDIUM");

    @EnumValue
    @JsonValue
    private final String value;

    KnowledgeRiskLevel(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    /** 高风险知识：发布环节需要平台管理员复核（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515） */
    public boolean isHighRisk() {
        return this == HIGH;
    }

    /** 归一为契约值域：LOW / MEDIUM 一律落到 NORMAL，null 视为 NORMAL */
    public static KnowledgeRiskLevel normalize(KnowledgeRiskLevel level) {
        if (level == null || level == LOW || level == MEDIUM) {
            return NORMAL;
        }
        return level;
    }
}
