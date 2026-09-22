package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.user.dto.DraftRequest;
import com.itticket.user.service.DraftService;
import com.itticket.user.vo.DraftVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 提单草稿(每用户一条) */
@RestController
@RequestMapping("/api/v1/users/drafts")
@RequiredArgsConstructor
public class DraftController {

    private final DraftService draftService;

    @GetMapping
    public Result<DraftVO> getDraft() {
        return Result.ok(draftService.getDraft(UserContext.get().getUserId()));
    }

    @PostMapping
    public Result<Void> saveDraft(@RequestBody DraftRequest request) {
        draftService.saveDraft(UserContext.get().getUserId(), request);
        return Result.ok("草稿已保存", null);
    }

    @DeleteMapping
    public Result<Void> deleteDraft() {
        draftService.deleteDraft(UserContext.get().getUserId());
        return Result.ok("草稿已清除", null);
    }
}
