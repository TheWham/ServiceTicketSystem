package com.itticket.ai.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.ai.dto.KnowledgeAddRequest;
import com.itticket.ai.entity.AiKnowledge;
import com.itticket.ai.mapper.AiKnowledgeMapper;
import com.itticket.ai.service.KnowledgeService;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

/**
 * 知识库管理(客服/主管维护 FAQ、SOP 等外部知识;历史工单由定时任务自动回流)。
 * 录入时自动切片并向量化,立即参与检索。
 */
@RestController
@RequestMapping("/api/v1/ai/knowledge")
@RequiredArgsConstructor
public class KnowledgeController {

    private final KnowledgeService knowledgeService;
    private final AiKnowledgeMapper knowledgeMapper;

    /** 手工录入知识 */
    @PostMapping
    public Result<Map<String, Object>> add(@RequestBody KnowledgeAddRequest request) {
        checkManager();
        if (request.getTitle() == null || request.getTitle().isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "标题不能为空");
        }
        if (request.getContent() == null || request.getContent().trim().length() < 10) {
            throw new BizException(ErrorCode.PARAM_INVALID, "知识内容至少 10 个字符");
        }
        // 每篇文档一个批次号,source_id 用于防重与追溯
        String sourceId = "manual-" + UUID.randomUUID();
        int chunks = knowledgeService.add(request.getTitle().trim(), request.getContent().trim(),
                request.getCategory(), "MANUAL", sourceId);
        return Result.ok("录入成功", Map.of("chunks", chunks));
    }

    /** 分页列表 */
    @GetMapping
    public Result<Page<AiKnowledge>> list(@RequestParam(defaultValue = "1") int page,
                                          @RequestParam(defaultValue = "10") int page_size,
                                          @RequestParam(required = false) String source_type) {
        checkManager();
        QueryWrapper<AiKnowledge> query = new QueryWrapper<>();
        if (source_type != null && !source_type.isBlank()) {
            query.eq("source_type", source_type);
        }
        // 列表不返回大字段向量,减少传输
        query.select(AiKnowledge.class, i -> !"embedding".equals(i.getColumn()))
                .orderByDesc("id");
        return Result.ok(knowledgeMapper.selectPage(new Page<>(page, page_size), query));
    }

    /** 删除知识切片 */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        checkManager();
        knowledgeMapper.deleteById(id);
        return Result.ok();
    }

    /** 角色守卫:客服或主管 */
    private void checkManager() {
        UserContext.checkRole(UserContext.get(), "customer_service", "supervisor");
    }
}
