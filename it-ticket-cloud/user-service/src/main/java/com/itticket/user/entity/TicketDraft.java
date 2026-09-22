package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 提单草稿表(it_user.ticket_draft),每用户一条 */
@Data
@TableName("ticket_draft")
public class TicketDraft {
    @TableId(value = "draft_id", type = IdType.AUTO)
    private Long draftId;
    private String userId;
    private String title;
    private String category;
    private String subCategory;
    private String priority;
    private String description;
    /** JSON 数组字符串,如 ["url1","url2"] */
    private String attachmentUrls;
    private String assetId;
    private LocalDateTime expectedFinishTime;
    private LocalDateTime updatedAt;
}
