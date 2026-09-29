package com.itticket.ticket.controller;

import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.ContractEnvelope;
import com.itticket.ticket.dto.DraftPayload;
import com.itticket.ticket.dto.SaveDraftRequest;
import com.itticket.ticket.service.TicketDraftService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 提单草稿(spec 05:PUT /ticket-drafts/{id} = saveTicketDraft)。
 *
 * <p>GET/DELETE 为 05 未定义的配套端点,供前端「登录后提示恢复草稿 / 提交后清理」
 * 使用(PRD 10.4),已标注为待回写项。请求/响应用 PRD 21.1 新包络。
 */
@RestController
@RequestMapping("/api/v1/ticket-drafts")
@RequiredArgsConstructor
public class TicketDraftController {

    private final TicketDraftService draftService;

    @PutMapping("/{id}")
    public ContractEnvelope<DraftPayload> save(
            @PathVariable String id,
            @RequestHeader(value = "X-Request-Id", required = false) String requestId,
            @RequestBody(required = false) SaveDraftRequest request) {
        return ContractEnvelope.ok(requestId, "草稿已保存", draftService.save(UserContext.get(), id, request));
    }

    @GetMapping("/{id}")
    public ContractEnvelope<DraftPayload> load(
            @PathVariable String id,
            @RequestHeader(value = "X-Request-Id", required = false) String requestId) {
        return ContractEnvelope.ok(requestId, "SUCCESS", draftService.load(UserContext.get(), id));
    }

    @DeleteMapping("/{id}")
    public ContractEnvelope<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-Request-Id", required = false) String requestId) {
        draftService.delete(UserContext.get(), id);
        return ContractEnvelope.ok(requestId, "草稿已清理", null);
    }
}
