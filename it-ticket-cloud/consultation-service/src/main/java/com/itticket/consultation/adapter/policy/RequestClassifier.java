package com.itticket.consultation.adapter.policy;
import com.itticket.consultation.adapter.*;
/**
 * 链路第 ① 环：意图判定（全景图见本包 package-info）。
 *
 * <p>实现二选一，由装配决定：{@link SemanticRequestClassifier}（provider=openai-compatible，
 * 默认）语义判定；{@link KeywordRequestClassifier}（provider=local，以及语义输出不合法时的降级）。
 * 消费方只有一个：{@code ComposedRagAdapter}——domain 做门禁，tool 做工具放行。
 */
public interface RequestClassifier { RequestVerdict classify(RagQuery query, RagCallContext context); }
