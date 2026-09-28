package com.itticket.ai.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.ai.config.AiProperties;
import com.itticket.ai.entity.AiKnowledge;
import com.itticket.ai.mapper.AiKnowledgeMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * 知识库:切片入库 + 向量相似度检索。
 * 检索实现为「全量读向量 + 内存余弦相似度」,知识量万级以内足够;
 * 数据量大后只需把 search() 换成 Milvus/PgVector 调用,上层零改动。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeService {

    /** 命中结果(知识条目 + 相似度得分) */
    public record Hit(AiKnowledge knowledge, double score) {
    }

    private final AiKnowledgeMapper knowledgeMapper;
    private final EmbeddingClient embeddingClient;
    private final AiProperties properties;
    private final ObjectMapper objectMapper;

    // ---------------- 入库 ----------------

    /**
     * 知识入库:按 chunkSize 切片(重叠 chunkOverlap),逐片向量化后落库。
     * @return 实际入库的切片数
     */
    public int add(String title, String content, String category, String sourceType, String sourceId) {
        List<String> chunks = split(content, properties.getRag().getChunkSize(),
                properties.getRag().getChunkOverlap());
        int saved = 0;
        for (int i = 0; i < chunks.size(); i++) {
            AiKnowledge knowledge = new AiKnowledge();
            knowledge.setTitle(chunks.size() > 1 ? title + "(" + (i + 1) + "/" + chunks.size() + ")" : title);
            knowledge.setContent(chunks.get(i));
            knowledge.setCategory(category);
            knowledge.setSourceType(sourceType);
            knowledge.setSourceId(sourceId);
            // embedding 不可用时仍存文本,后续可通过重跑同步补向量(检索时自动跳过无向量条目)
            float[] vector = embeddingClient.isEnabled() ? embeddingClient.embed(chunks.get(i)) : null;
            knowledge.setEmbedding(vector == null ? null : toJson(vector));
            knowledgeMapper.insert(knowledge);
            saved++;
        }
        return saved;
    }

    /** 同一来源是否已入库(知识回流防重) */
    public boolean existsBySource(String sourceType, String sourceId) {
        QueryWrapper<AiKnowledge> query = new QueryWrapper<>();
        query.eq("source_type", sourceType).eq("source_id", sourceId).last("LIMIT 1");
        return knowledgeMapper.selectCount(query) > 0;
    }

    // ---------------- 检索 ----------------

    /**
     * 相似度检索 TopK(得分 ≥ minScore)。embedding 未配置时返回空列表(RAG 降级)。
     */
    public List<Hit> search(String question) {
        if (!embeddingClient.isEnabled()) {
            return List.of();
        }
        float[] queryVector = embeddingClient.embed(question);
        if (queryVector == null) {
            return List.of();
        }

        // 全量读入(只取有向量的条目),内存算余弦相似度
        QueryWrapper<AiKnowledge> query = new QueryWrapper<>();
        query.isNotNull("embedding");
        List<AiKnowledge> all = knowledgeMapper.selectList(query);

        double minScore = properties.getRag().getMinScore();
        List<Hit> hits = new ArrayList<>();
        for (AiKnowledge knowledge : all) {
            float[] docVector = fromJson(knowledge.getEmbedding());
            if (docVector == null || docVector.length != queryVector.length) {
                continue;   // 向量缺失或模型更换导致维度不一致,跳过
            }
            double score = cosine(queryVector, docVector);
            if (score >= minScore) {
                hits.add(new Hit(knowledge, score));
            }
        }
        hits.sort(Comparator.comparingDouble(Hit::score).reversed());
        return hits.size() > properties.getRag().getTopK()
                ? hits.subList(0, properties.getRag().getTopK())
                : hits;
    }

    // ---------------- 工具 ----------------

    /** 定长切片,片间保留重叠,避免语义被截断 */
    static List<String> split(String text, int chunkSize, int overlap) {
        List<String> chunks = new ArrayList<>();
        String clean = text == null ? "" : text.trim();
        if (clean.length() <= chunkSize) {
            if (!clean.isEmpty()) {
                chunks.add(clean);
            }
            return chunks;
        }
        int start = 0;
        while (start < clean.length()) {
            int end = Math.min(start + chunkSize, clean.length());
            chunks.add(clean.substring(start, end));
            if (end >= clean.length()) {
                break;
            }
            start = end - overlap;
        }
        return chunks;
    }

    /** 余弦相似度 */
    static double cosine(float[] a, float[] b) {
        double dot = 0, normA = 0, normB = 0;
        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        return (normA == 0 || normB == 0) ? 0 : dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    private String toJson(float[] vector) {
        try {
            return objectMapper.writeValueAsString(vector);
        } catch (Exception e) {
            return null;
        }
    }

    private float[] fromJson(String json) {
        try {
            List<Double> list = objectMapper.readValue(json, new TypeReference<>() {
            });
            float[] vector = new float[list.size()];
            for (int i = 0; i < list.size(); i++) {
                vector[i] = list.get(i).floatValue();
            }
            return vector;
        } catch (Exception e) {
            return null;
        }
    }
}
