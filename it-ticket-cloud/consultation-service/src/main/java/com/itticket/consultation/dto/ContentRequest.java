package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * OpenAPI 05 Content(字段名为 snake_case,与 AI-003 的 camelCase DTO 不同,两者各自遵循所属契约)。
 * Schema 的 anyOf 要求 content 与 attachment_ids 至少有一个；附件仅支持人工会话。
 */
public record ContentRequest(
        @Size(min = 1, max = 12000) String content,
        @NotBlank @Size(max = 64) @JsonProperty("client_message_id") String clientMessageId,
        @Size(min = 1, max = 10) @JsonProperty("attachment_ids") List<@NotBlank @Size(max = 64) String> attachmentIds) {

    /** Schema 的 anyOf:content 与 attachment_ids 至少提供一个,两者皆空必须拒绝。 */
    @JsonIgnore
    @AssertTrue(message = "content 与 attachment_ids 至少提供一个")
    public boolean isPayloadPresent() {
        boolean hasContent = content != null && !content.isBlank();
        boolean hasAttachments = attachmentIds != null && !attachmentIds.isEmpty();
        return hasContent || hasAttachments;
    }
}
