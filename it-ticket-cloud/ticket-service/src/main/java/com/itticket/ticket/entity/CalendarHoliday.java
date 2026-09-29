package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;

/**
 * 节假日与调休(SQL-010 calendar_holiday)。[LOCAL] 只读。
 * isWorkingDay=true 表示调休补班,该日按工作日计时。
 */
@Data
@TableName("calendar_holiday")
public class CalendarHoliday {

    @TableId(value = "holiday_id", type = IdType.INPUT)
    private String holidayId;
    private String calendarId;
    private LocalDate holidayDate;
    private String name;
    private Boolean isWorkingDay;
}
