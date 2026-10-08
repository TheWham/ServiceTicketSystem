package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.AttachmentProjection;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationAttachmentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/api/v1/consultations/{sessionId}/attachments")
@RequiredArgsConstructor
public class ConsultationAttachmentController {
    private final ConsultationAttachmentService attachments;
    private final AuthzService authz;

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiEnvelope<AttachmentProjection> upload(@PathVariable String sessionId,
                                                    @RequestPart("file") MultipartFile file) {
        return ApiEnvelope.ok(attachments.upload(authz.currentUser(), sessionId, file), RequestContext.get());
    }

    @GetMapping("/{attachmentId}/content")
    public ResponseEntity<byte[]> content(@PathVariable String sessionId, @PathVariable String attachmentId) {
        var content = attachments.readContent(authz.currentUser(), sessionId, attachmentId);
        ContentDisposition disposition = (content.isImage() ? ContentDisposition.inline() : ContentDisposition.attachment())
                .filename(content.fileName(), StandardCharsets.UTF_8).build();
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(content.contentType()))
                .contentLength(content.bytes().length)
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .header("X-Content-Type-Options", "nosniff")
                .header(HttpHeaders.CACHE_CONTROL, "no-store")
                .body(content.bytes());
    }

    @DeleteMapping("/{attachmentId}")
    public ApiEnvelope<Void> withdraw(@PathVariable String sessionId, @PathVariable String attachmentId) {
        attachments.withdraw(authz.currentUser(), sessionId, attachmentId);
        return ApiEnvelope.ok(null, RequestContext.get());
    }
}
