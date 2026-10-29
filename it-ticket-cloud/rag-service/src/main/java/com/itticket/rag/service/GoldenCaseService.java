package com.itticket.rag.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.dto.GoldenCaseUpsertRequest;
import com.itticket.rag.entity.GoldenCase;
import com.itticket.rag.mapper.GoldenCaseMapper;
import com.itticket.rag.vo.GoldenCaseView;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.Map;

/**
 * 黄金问题集管理(golden_case,V2_6)。表为评测基准唯一真源:
 * 评测管道仍读 JSON 文件,由 db/tools/golden_export.py 从本表导出。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GoldenCaseService {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> SOURCE_TYPES = Set.of("SEED", "BAD_CASE", "MANUAL");

    private final GoldenCaseMapper goldenCaseMapper;

    public Map<String, Object> page(int page, int pageSize, Boolean isAdversarial,
                                    String sourceType, String keyword) {
        Page<GoldenCase> result = goldenCaseMapper.selectPage(
                new Page<>(Math.max(1, page), Math.min(Math.max(1, pageSize), 100)),
                new LambdaQueryWrapper<GoldenCase>()
                        .eq(GoldenCase::getEnabled, 1)
                        .eq(isAdversarial != null, GoldenCase::getIsAdversarial, isAdversarial)
                        .eq(StringUtils.hasText(sourceType) && SOURCE_TYPES.contains(sourceType),
                                GoldenCase::getSourceType, sourceType)
                        .like(StringUtils.hasText(keyword), GoldenCase::getQuery, keyword)
                        .orderByDesc(GoldenCase::getCreatedAt));
        List<GoldenCaseView> items = new ArrayList<>();
        for (GoldenCase entity : result.getRecords()) {
            items.add(toView(entity));
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("items", items);
        data.put("page", result.getCurrent());
        data.put("pageSize", result.getSize());
        data.put("total", result.getTotal());
        data.put("stats", stats());
        return data;
    }

    public GoldenCaseView upsert(GoldenCaseUpsertRequest request, String operatorId) {
        if (request.id() != null) {
            GoldenCase existing = goldenCaseMapper.selectById(request.id());
            if (existing == null || existing.getEnabled() == 0) {
                throw new BizException(ErrorCode.PARAM_INVALID, "黄金条目不存在");
            }
            applyFields(existing, request);
            goldenCaseMapper.updateById(existing);
            log.info("[golden-case] 编辑条目 id={} operator={}", existing.getId(), operatorId);
            return toView(existing);
        }
        GoldenCase entity = new GoldenCase();
        entity.setNaturalKey("manual-" + UUID.randomUUID());
        applyFields(entity, request);
        entity.setSourceType("MANUAL");
        entity.setEnabled(1);
        entity.setCreatedBy(operatorId);
        entity.setCreatedAt(LocalDateTime.now());
        goldenCaseMapper.insert(entity);
        log.info("[golden-case] 手工新增条目 id={} operator={}", entity.getId(), operatorId);
        return toView(entity);
    }

    public void softDelete(Long id, String operatorId) {
        GoldenCase existing = goldenCaseMapper.selectById(id);
        if (existing == null) {
            throw new BizException(ErrorCode.PARAM_INVALID, "黄金条目不存在");
        }
        existing.setEnabled(0);
        goldenCaseMapper.updateById(existing);
        log.info("[golden-case] 软删条目 id={} operator={}", id, operatorId);
    }

    // ---------------------------------------------------------------- 内部

    private void applyFields(GoldenCase entity, GoldenCaseUpsertRequest request) {
        entity.setCategory(StringUtils.hasText(request.category()) ? request.category().trim() : "general");
        entity.setDifficulty(StringUtils.hasText(request.difficulty())
                ? request.difficulty().trim().toUpperCase(Locale.ROOT) : "MEDIUM");
        entity.setQuery(request.query().trim());
        entity.setGroundTruthAnswer(request.groundTruthAnswer().trim());
        entity.setReferenceChunkIdsJson(toJsonArray(request.referenceChunkIds()));
        entity.setExpectedKeywordsJson(toJsonArray(request.expectedKeywords()));
        entity.setIsConflictCheck(Boolean.TRUE.equals(request.isConflictCheck()) ? 1 : 0);
        entity.setIsAdversarial(Boolean.TRUE.equals(request.isAdversarial()) ? 1 : 0);
    }

    private Map<String, Object> stats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("total", goldenCaseMapper.selectCount(new LambdaQueryWrapper<GoldenCase>()
                .eq(GoldenCase::getEnabled, 1)));
        stats.put("adversarial", goldenCaseMapper.selectCount(new LambdaQueryWrapper<GoldenCase>()
                .eq(GoldenCase::getEnabled, 1).eq(GoldenCase::getIsAdversarial, 1)));
        stats.put("fromBadCase", goldenCaseMapper.selectCount(new LambdaQueryWrapper<GoldenCase>()
                .eq(GoldenCase::getEnabled, 1).eq(GoldenCase::getSourceType, "BAD_CASE")));
        return stats;
    }

    private GoldenCaseView toView(GoldenCase entity) {
        return new GoldenCaseView(entity.getId(), entity.getNaturalKey(), entity.getCategory(),
                entity.getDifficulty(), entity.getQuery(), entity.getGroundTruthAnswer(),
                readList(entity.getReferenceChunkIdsJson()), readList(entity.getExpectedKeywordsJson()),
                intToBool(entity.getIsConflictCheck()), intToBool(entity.getIsAdversarial()),
                entity.getSourceType(), entity.getSourceAiMessageId(),
                intToBool(entity.getEnabled()), entity.getCreatedBy(), entity.getCreatedAt());
    }

    private String toJsonArray(String raw) {
        List<String> values = new ArrayList<>();
        if (StringUtils.hasText(raw)) {
            if (raw.trim().startsWith("[")) {
                try {
                    values = JSON.readValue(raw, new TypeReference<List<String>>() { });
                } catch (Exception e) {
                    throw new BizException(ErrorCode.PARAM_INVALID, "JSON 数组格式不合法: " + raw);
                }
            } else {
                for (String item : raw.split("[,;,]")) {
                    if (!item.isBlank()) values.add(item.trim());
                }
            }
        }
        try {
            return JSON.writeValueAsString(values);
        } catch (Exception e) {
            return "[]";
        }
    }

    private List<String> readList(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            return JSON.readValue(json, new TypeReference<List<String>>() { });
        } catch (Exception e) {
            return List.of();
        }
    }

    private boolean intToBool(Integer value) {
        return value != null && value == 1;
    }
}
