package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

/** Existing shared attachment table; no additional columns or business types. */
@Data
@TableName("attachment")
public class ConsultationAttachment {
    @TableId(value = "attachment_id", type = IdType.INPUT)
    private String attachmentId;
    private String bizType;
    private String bizId;
    private String uploaderId;
    private String objectKey;
    private String fileName;
    private Long size;
    private String hash;
    private String contentType;
    private String scanStatus;
    private LocalDateTime uploadedAt;
    private LocalDateTime withdrawnAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
