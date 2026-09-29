package com.itticket.rag.service;

import com.itticket.rag.config.RagRetrievalProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * ============================================================================
 * 高风险主题拦截器 (HighRiskGuardrail)
 * ============================================================================
 *
 * <p>契约 AI-001：账号权限、安全事件、数据丢失、高风险命令、硬件拆修等主题必须返回 REFUSE，
 * 并提供转人工与直接提单入口；PRD §17.1 同样要求这类问题优先引导转人工。</p>
 *
 * <p>词表可配置（rag.retrieval.high-risk-keywords），命中即拦截，不进入检索与后续生成，
 * 既满足合规，也避免把高风险问题交给下游模型自由发挥。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class HighRiskGuardrail {

    private final RagRetrievalProperties properties;

    /**
     * 拦截判定结果。
     *
     * @param blocked         是否命中高风险主题
     * @param matchedKeyword  命中的关键词（用于审计与排查）
     */
    public record HighRiskVerdict(boolean blocked, String matchedKeyword) {

        public static HighRiskVerdict pass() {
            return new HighRiskVerdict(false, null);
        }
    }

    /** 判定提问是否命中高风险主题（先词表、再正则规则） */
    public HighRiskVerdict inspect(String message) {
        if (message == null || message.isBlank()) {
            return HighRiskVerdict.pass();
        }
        String lowerMessage = message.toLowerCase(Locale.ROOT);

        if (properties.getHighRiskKeywords() != null) {
            for (String keyword : properties.getHighRiskKeywords()) {
                if (keyword == null || keyword.isBlank()) {
                    continue;
                }
                if (lowerMessage.contains(keyword.toLowerCase(Locale.ROOT))) {
                    log.info("High-risk topic intercepted by keyword [{}]", keyword);
                    return new HighRiskVerdict(true, keyword);
                }
            }
        }

        // 正则兜底：捕获关键词被限定语打断的高风险意图（如「重置我的域账号密码」）
        if (properties.getHighRiskPatterns() != null) {
            for (String regex : properties.getHighRiskPatterns()) {
                if (regex == null || regex.isBlank()) {
                    continue;
                }
                try {
                    if (Pattern.compile(regex, Pattern.CASE_INSENSITIVE).matcher(message).find()) {
                        log.info("High-risk topic intercepted by pattern [{}]", regex);
                        return new HighRiskVerdict(true, regex);
                    }
                } catch (PatternSyntaxException e) {
                    log.warn("高风险规则正则非法，已跳过: {}", regex);
                }
            }
        }
        return HighRiskVerdict.pass();
    }
}
