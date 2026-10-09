package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;
import java.util.List;

/** 已提交工单内容；不接收状态、优先级或任何计时字段。 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class EditTicketRequest {
    private String nature;
    private String categoryId;
    private String title;
    private String description;
    private String impactDescription;
    private String urgencyDescription;
    private String location;
    private String contact;
    private String assetId;
    /** null 保留附件，空列表移除原照片，非空列表为最终照片集合。 */
    private List<String> attachments;
}
