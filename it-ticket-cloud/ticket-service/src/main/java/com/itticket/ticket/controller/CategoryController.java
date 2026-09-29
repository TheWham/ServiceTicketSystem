package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.mapper.CategoryMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 工单分类查询 —— PRD §10.1 分类目录；提单仅允许选择末级（enabled 且无子节点）。
 */
@RestController
@RequestMapping("/api/v1/categories")
@RequiredArgsConstructor
public class CategoryController {

    private final CategoryMapper categoryMapper;

    /** 全部分类（ACTIVE），前端自行组树；返回扁平列表 */
    @GetMapping
    public Result<List<Category>> list() {
        List<Category> all = categoryMapper.selectList(new QueryWrapper<Category>()
                .eq("status", "ACTIVE").orderByAsc("category_id"));
        return Result.ok(all);
    }

    /** 末级分类（可提单选择）：ACTIVE 且无 ACTIVE 子节点 */
    @GetMapping("/leaf")
    public Result<List<Category>> leaf() {
        List<Category> all = categoryMapper.selectList(new QueryWrapper<Category>()
                .eq("status", "ACTIVE"));
        java.util.Set<String> parentIds = all.stream()
                .map(Category::getParentId)
                .filter(java.util.Objects::nonNull)
                .collect(Collectors.toSet());
        List<Category> leaf = all.stream()
                .filter(c -> !parentIds.contains(c.getCategoryId()))
                .toList();
        return Result.ok(leaf);
    }
}
