package com.itticket.rag.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.rag.dto.GoldenCaseUpsertRequest;
import com.itticket.rag.service.GoldenCaseService;
import com.itticket.rag.vo.GoldenCaseView;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * ============================================================================
 * 黄金数据集管理接口 (GoldenCaseController)
 * ============================================================================
 *
 * 【接口列表】:
 * 1. GET    /api/v1/rag/golden-cases          : 黄金条目分页列表(含统计)
 * 2. POST   /api/v1/rag/golden-cases          : 手工新增/编辑条目(MANUAL 来源)
 * 3. DELETE /api/v1/rag/golden-cases/{id}     : 软删(移出评测,不物理删除)
 *
 * 【数据来源】: SEED 由 db/tools/golden_seed_import.py 导入;
 * BAD_CASE 由 consultation-service 拒答处置事务写入。评测管道仍读 JSON 文件,
 * 由 db/tools/golden_export.py 从本表导出,评测代码零改动。
 *
 * 【角色守卫】: 知识库管理员 KNOWLEDGE_ADMIN / 平台管理员 PLATFORM_ADMIN
 * (与知识生命周期管理同权,见 support/Roles.java)。
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/rag/golden-cases")
@RequiredArgsConstructor
public class GoldenCaseController {

    private final GoldenCaseService goldenCaseService;

    /** 黄金条目分页列表(含 stats: total/adversarial/fromBadCase)。 */
    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(value = "page", required = false, defaultValue = "1") int page,
            @RequestParam(value = "pageSize", required = false, defaultValue = "15") int pageSize,
            @RequestParam(value = "isAdversarial", required = false) Boolean isAdversarial,
            @RequestParam(value = "sourceType", required = false) String sourceType,
            @RequestParam(value = "keyword", required = false) String keyword) {
        requireManageRole();
        return Result.ok(goldenCaseService.page(page, pageSize, isAdversarial, sourceType, keyword));
    }

    /** 手工新增/编辑黄金条目。 */
    @PostMapping
    public Result<GoldenCaseView> upsert(@Valid @RequestBody GoldenCaseUpsertRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        return Result.ok(goldenCaseService.upsert(request, user.getUserId()));
    }

    /** 软删(移出评测)。 */
    @DeleteMapping("/{id}")
    public Result<Void> softDelete(@PathVariable("id") Long id) {
        UserContext.CurrentUser user = requireManageRole();
        goldenCaseService.softDelete(id, user.getUserId());
        return Result.ok();
    }

    private UserContext.CurrentUser requireManageRole() {
        UserContext.CurrentUser user = UserContext.get();
        if (!com.itticket.rag.support.Roles.canManageKnowledge(user.getRole())) {
            throw new com.itticket.common.api.BizException(
                    com.itticket.common.api.ErrorCode.FORBIDDEN, "需要 知识库管理员 或 平台管理员 权限");
        }
        return user;
    }
}
