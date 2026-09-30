package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 附件 attachment —— PRD §20，先扫描后可用；保存哈希/上传人/扫描结果 */
@Data
@TableName("attachment")
public class Attachment {
    @TableId(value = "attachment_id", type = IdType.INPUT)
    private String attachmentId;
    /** CONSULTATION/TICKET/MESSAGE/SUPPLEMENT/KNOWLEDGE */
    private String bizType;
    private String bizId;
    private String uploaderId;
    private String objectKey;
    private String fileName;
    /** ≤20MB */
    private Long size;
    /** 文件哈希 */
    private String hash;
    private String contentType;
    /** PENDING/PASSED/REJECTED/ERROR */
    private String scanStatus;
    private LocalDateTime uploadedAt;
    private LocalDateTime withdrawnAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
