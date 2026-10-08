package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.itticket.consultation.entity.ConsultationAttachment;
import java.util.Set;

public record AttachmentProjection(
        @JsonProperty("attachment_id") String attachmentId,
        @JsonProperty("file_name") String fileName,
        @JsonProperty("content_type") String contentType,
        long size,
        @JsonProperty("is_image") boolean isImage) {
    public static boolean isPreviewType(String type) {
        return type != null && Set.of("image/png", "image/jpeg", "image/gif", "image/bmp").contains(type);
    }

    public static AttachmentProjection of(ConsultationAttachment row) {
        return new AttachmentProjection(row.getAttachmentId(), row.getFileName(), row.getContentType(),
                row.getSize(), isPreviewType(row.getContentType()));
    }
}
