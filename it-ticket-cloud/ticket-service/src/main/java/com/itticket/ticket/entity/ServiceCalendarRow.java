package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 服务日历(SQL-010 service_calendar)。[LOCAL] 只读,由平台管理员维护。 */
@Data
@TableName("service_calendar")
public class ServiceCalendarRow {

    @TableId(value = "calendar_id", type = IdType.INPUT)
    private String calendarId;
    private String timezone;
    /** ISO 工作日数组 JSON,如 [1,2,3,4,5]。 */
    private String workWeekJson;
    /** 工作时段数组 JSON,如 [{"start":"09:00","end":"18:00"}]。 */
    private String workIntervalsJson;
    private Boolean lunchPauses;
    private Long version;
    private LocalDateTime effectiveFrom;
    private LocalDateTime effectiveTo;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
