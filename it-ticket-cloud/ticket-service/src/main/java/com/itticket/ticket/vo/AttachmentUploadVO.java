package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;

/** 照片附件上传结果（snake_case 输出） */
@Data
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AttachmentUploadVO {
    /** 附件 id（创建工单时放入 attachments 字段完成绑定） */
    private String attachmentId;
    private String fileName;
    private Long size;
}
