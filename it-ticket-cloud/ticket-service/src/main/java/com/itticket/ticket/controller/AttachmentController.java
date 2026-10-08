package com.itticket.ticket.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.service.AttachmentService;
import com.itticket.ticket.vo.AttachmentUploadVO;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

/**
 * 工单照片附件接口（挂在 /api/v1/tickets 下，走 gateway 的 ticket-service 路由）。
 * 上传 → 返回 attachment_id；创建工单时把 id 放入 attachments 字段完成绑定；
 * 查看走 /{id}/content（带 JWT，按提单人/处理人/主管鉴权）。
 */
@RestController
@RequestMapping("/api/v1/tickets/attachments")
@RequiredArgsConstructor
public class AttachmentController {

    private final AttachmentService attachmentService;

    /** 上传照片（multipart/form-data，字段名 file） */
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<AttachmentUploadVO> upload(@RequestParam("file") MultipartFile file) {
        return Result.ok(attachmentService.upload(UserContext.get(), file));
    }

    /** 撤回草稿态照片（绑定工单后不可撤回） */
    @DeleteMapping("/{attachmentId}")
    public Result<Void> withdraw(@PathVariable String attachmentId) {
        attachmentService.withdraw(UserContext.get(), attachmentId);
        return Result.ok();
    }

    /** 查看照片内容（img 无法带 JWT，前端用 axios blob 拉取） */
    @GetMapping("/{attachmentId}/content")
    public ResponseEntity<byte[]> content(@PathVariable String attachmentId) {
        AttachmentService.AttachmentContent c = attachmentService.readContent(UserContext.get(), attachmentId);
        String name = URLEncoder.encode(c.fileName(), StandardCharsets.UTF_8).replace("+", "%20");
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(c.contentType()))
                .header("Content-Disposition", "inline; filename*=UTF-8''" + name)
                .body(c.bytes());
    }
}
