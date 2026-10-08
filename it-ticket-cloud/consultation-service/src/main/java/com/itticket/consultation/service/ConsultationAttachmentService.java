package com.itticket.consultation.service;

import com.itticket.consultation.api.*;
import com.itticket.consultation.dto.AttachmentProjection;
import com.itticket.consultation.entity.*;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.mapper.*;
import com.itticket.consultation.support.Hashes;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import java.util.*;

@Service
public class ConsultationAttachmentService {
    private final ConsultationAttachmentMapper attachments;
    private final ConsultationMessageMapper messages;
    private final ConsultationTransitionService transitions;
    private final AuthzService authz;
    private final ConsultationAttachmentStorage storage;

    public ConsultationAttachmentService(ConsultationAttachmentMapper attachments,
            ConsultationMessageMapper messages, ConsultationTransitionService transitions, AuthzService authz,
            @Value("${itticket.attachment.storage-dir:./data/attachments}") String storageDirectory) {
        this.attachments = attachments; this.messages = messages;
        this.transitions = transitions; this.authz = authz;
        this.storage = new ConsultationAttachmentStorage(storageDirectory);
    }

    @Transactional
    public AttachmentProjection upload(CurrentUser user, String sessionId, MultipartFile file) {
        Consultation session = transitions.loadForUpdate(sessionId);
        authz.requireParticipant(user, session);
        requireHumanState(session);
        byte[] bytes = storage.readUpload(file);
        String namespace = namespace(sessionId, user.userId());
        String hash = ConsultationAttachmentStorage.hash(bytes);
        ConsultationAttachment existing = attachments.findDraft(namespace, hash);
        if (existing != null) {
            requireDraft(existing, namespace, user.userId());
            return AttachmentProjection.of(existing);
        }
        String objectKey = storage.save(bytes);
        try {
            ConsultationAttachment row = new ConsultationAttachment();
            row.setAttachmentId("ATT" + UUID.randomUUID().toString().replace("-", ""));
            row.setBizType("CONSULTATION"); row.setBizId(namespace); row.setUploaderId(user.userId());
            row.setObjectKey(objectKey); row.setFileName(ConsultationAttachmentStorage.fileName(file.getOriginalFilename()));
            row.setSize((long) bytes.length); row.setHash(hash);
            row.setContentType(ConsultationAttachmentStorage.contentType(bytes, file.getContentType()));
            // Existing local fallback: PASSED means local validation ONLY, never an actual malware scan.
            row.setScanStatus("PASSED");
            var now = Times.nowUtc();
            row.setUploadedAt(now); row.setCreatedAt(now); row.setUpdatedAt(now);
            attachments.insert(row);
            return AttachmentProjection.of(row);
        } catch (RuntimeException e) {
            storage.delete(objectKey);
            throw e;
        }
    }

    @Transactional
    public void withdraw(CurrentUser user, String sessionId, String attachmentId) {
        Consultation session = transitions.loadForUpdate(sessionId);
        authz.requireParticipant(user, session);
        String namespace = namespace(sessionId, user.userId());
        String tombstone = Hashes.sha256Hex(Json.write(List.of("withdrawn", namespace, attachmentId)));
        ConsultationAttachment row = attachments.selectById(attachmentId);
        if (row == null || !"CONSULTATION".equals(row.getBizType()) || !user.userId().equals(row.getUploaderId())
                || !(namespace.equals(row.getBizId()) || tombstone.equals(row.getBizId()))) throw ApiException.notFound();
        if (row.getWithdrawnAt() != null) return;
        if (attachments.withdrawDraft(attachmentId, namespace, user.userId(), tombstone, Times.nowUtc()) != 1) {
            throw ApiException.notFound();
        }
        storage.deleteAfterCommit(row.getObjectKey());
    }

    public record AttachmentContent(String fileName, String contentType, byte[] bytes, boolean isImage) { }

    @Transactional
    public AttachmentContent readContent(CurrentUser user, String sessionId, String attachmentId) {
        Consultation session = transitions.loadForUpdate(sessionId);
        authz.requireParticipant(user, session);
        ConsultationAttachment row = attachments.selectById(attachmentId);
        if (row == null || row.getWithdrawnAt() != null || !"PASSED".equals(row.getScanStatus())) throw ApiException.notFound();
        if ("MESSAGE".equals(row.getBizType())) {
            ConsultationMessage message = messages.selectById(row.getBizId());
            if (message == null || !sessionId.equals(message.getSessionId()) || message.getWithdrawnAt() != null) {
                throw ApiException.notFound();
            }
        } else {
            requireDraft(row, namespace(sessionId, user.userId()), user.userId());
            if (!isHumanState(session)) throw ApiException.notFound();
        }
        byte[] bytes = storage.read(row.getObjectKey());
        String type = ConsultationAttachmentStorage.contentType(bytes, row.getContentType());
        return new AttachmentContent(row.getFileName(), type, bytes, AttachmentProjection.isPreviewType(type));
    }

    /** Called inside the existing message idempotency transaction, after locking the session. */
    @Transactional(propagation = Propagation.MANDATORY)
    public List<AttachmentProjection> bind(CurrentUser user, Consultation session, String messageId, List<String> ids) {
        authz.requireParticipant(user, session);
        requireHumanState(session);
        validateIds(ids);
        if (ids == null || ids.isEmpty()) return List.of();
        String namespace = namespace(session.getSessionId(), user.userId());
        List<ConsultationAttachment> rows = new ArrayList<>();
        for (String id : ids) {
            ConsultationAttachment row = attachments.selectById(id);
            requireDraft(row, namespace, user.userId());
            rows.add(row);
        }
        // Validate the entire batch before mutating anything. Conditional updates defend against stale ownership.
        for (ConsultationAttachment row : rows) {
            if (attachments.bindDraft(row.getAttachmentId(), namespace, user.userId(), messageId, Times.nowUtc()) != 1) {
                throw ApiException.notFound();
            }
        }
        return rows.stream().map(AttachmentProjection::of).toList();
    }

    static void validateIds(List<String> ids) {
        if (ids != null && (ids.size() > 10 || ids.stream().anyMatch(id -> id == null || id.isBlank() || id.length() > 64)
                || new HashSet<>(ids).size() != ids.size())) {
            throw ApiException.validation(List.of(FieldIssue.invalid("attachment_ids", "最多 10 个不重复的有效附件 ID")));
        }
    }

    static void requireHumanState(Consultation session) {
        if (!isHumanState(session)) throw new ApiException(ApiCode.ILLEGAL_STATE_TRANSITION, "仅人工会话可上传或发送附件和消息");
    }

    private static boolean isHumanState(Consultation session) {
        return session.getStatus() == ConsultationStatus.WAITING_ENGINEER
                || session.getStatus() == ConsultationStatus.HUMAN_ACTIVE
                || session.getStatus() == ConsultationStatus.PENDING_CONFIRMATION;
    }

    private static String namespace(String sessionId, String uploaderId) {
        // Encode the pair unambiguously ("ab"/"c" must not collide with "a"/"bc").
        return Hashes.sha256Hex(Json.write(List.of(sessionId, uploaderId)));
    }

    private static void requireDraft(ConsultationAttachment row, String namespace, String uploader) {
        if (row == null || !"CONSULTATION".equals(row.getBizType()) || !namespace.equals(row.getBizId())
                || !uploader.equals(row.getUploaderId()) || row.getWithdrawnAt() != null
                || !"PASSED".equals(row.getScanStatus())) throw ApiException.notFound();
    }
}
