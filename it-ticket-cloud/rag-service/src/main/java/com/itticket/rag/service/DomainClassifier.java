package com.itticket.rag.service;

import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.enums.OfficeDomain;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * ============================================================================
 * 办公 IT 领域判定器 (DomainClassifier)
 * ============================================================================
 *
 * 【契约依据】MR-004（docs/specs/10-model-rag-integration.md:70）：
 * 判定结果独立于生成结果，四态为 OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN；
 * 「单个 IT 关键词或检索命中不构成领域许可」，检索资料与用户输入不得覆盖领域规则。
 *
 * 【AI-001（docs/specs/02-ai-api-json-schema.md:14）的高风险口径修正】：
 * 高风险只覆盖「动作 × 敏感对象」的组合（如「重置+密码」「删除+数据库」「拆+硬盘」），
 * 以及明确的命令/越权正则；普通登录排障（「账号登录失败」「忘记密码」）不得被误拦。
 *
 * 【判定顺序】：
 * 1. OFF_TOPIC —— 命中领域外词表（非办公 IT 问题）
 * 2. HIGH_RISK —— 命中高风险正则，或（动作词 ∩ 敏感对象）同时命中
 * 3. OFFICE_IT —— 命中办公 IT 词表
 * 4. UNCERTAIN —— 以上都不满足，交由上层 CLARIFY
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DomainClassifier {

    private final RagRetrievalProperties properties;

    /**
     * 判定结果。
     *
     * @param domain      四态领域判定
     * @param matchedRule 命中的规则（词或正则），用于审计与调参；未命中为 null
     */
    public record Verdict(OfficeDomain domain, String matchedRule) {

        public static Verdict of(OfficeDomain domain, String matchedRule) {
            return new Verdict(domain, matchedRule);
        }
    }

    /** 判定问题所属领域 */
    public Verdict classify(String message) {
        if (message == null || message.isBlank()) {
            return Verdict.of(OfficeDomain.UNCERTAIN, null);
        }
        String lower = message.toLowerCase(Locale.ROOT);

        // 1. 领域外：非办公 IT 问题（周报/翻译/订餐/股票等）
        for (String keyword : nullSafe(properties.getOffTopicKeywords())) {
            if (hasText(keyword) && lower.contains(keyword.toLowerCase(Locale.ROOT))) {
                log.info("Domain verdict OFF_TOPIC by keyword [{}]", keyword);
                return Verdict.of(OfficeDomain.OFF_TOPIC, keyword);
            }
        }

        // 2. 高风险正则（命令注入 / 提权复合表述）
        for (String regex : nullSafe(properties.getHighRiskPatterns())) {
            if (!hasText(regex)) {
                continue;
            }
            try {
                if (Pattern.compile(regex, Pattern.CASE_INSENSITIVE).matcher(message).find()) {
                    log.info("Domain verdict HIGH_RISK by pattern [{}]", regex);
                    return Verdict.of(OfficeDomain.HIGH_RISK, regex);
                }
            } catch (PatternSyntaxException e) {
                log.warn("高风险正则非法，已跳过: {}", regex);
            }
        }

        // 3. 动作 × 敏感对象（如「重置+密码」「删除+数据库」「恢复+数据」）
        boolean hasAction = containsAny(lower, properties.getHighRiskActions());
        boolean hasObject = containsAny(lower, properties.getHighRiskObjects());
        if (hasAction && hasObject) {
            log.info("Domain verdict HIGH_RISK by action+object");
            return Verdict.of(OfficeDomain.HIGH_RISK, "action+object");
        }

        // 4. 办公 IT 范围
        for (String keyword : nullSafe(properties.getOfficeItKeywords())) {
            if (hasText(keyword) && lower.contains(keyword.toLowerCase(Locale.ROOT))) {
                return Verdict.of(OfficeDomain.OFFICE_IT, keyword);
            }
        }

        // 5. 语义不明确
        return Verdict.of(OfficeDomain.UNCERTAIN, null);
    }

    private boolean containsAny(String haystack, java.util.List<String> needles) {
        for (String needle : nullSafe(needles)) {
            if (hasText(needle) && haystack.contains(needle.toLowerCase(Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static <T> java.util.List<T> nullSafe(java.util.List<T> list) {
        return list == null ? java.util.List.of() : list;
    }
}
