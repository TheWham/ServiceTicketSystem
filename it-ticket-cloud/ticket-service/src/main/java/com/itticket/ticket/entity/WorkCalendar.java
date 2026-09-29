package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalTime;

/** 服务日历（PRD §11.1：节假日平台管理员维护；默认周一~五 09:00-18:00） */
@Data
@TableName("work_calendar")
public class WorkCalendar {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private LocalDate calDate;
    /** WORKDAY / HOLIDAY */
    private String dayType;
    /** 默认 09:00 */
    private LocalTime startTime;
    /** 默认 18:00 */
    private LocalTime endTime;
    private Integer lunchPause;
}
