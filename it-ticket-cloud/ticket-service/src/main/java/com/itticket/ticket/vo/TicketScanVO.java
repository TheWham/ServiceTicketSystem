package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 工单分析投影（脱敏）。
 *
 * <p><b>为什么是「投影」而不是聚合结果</b>：这张表里存的是**未清洗**的原始工单，
 * 直接 {@code GROUP BY category_id} 会把联调测试单算进分母；而且按「故障症状」聚合
 * 需要词表（{@code analytics_service/configs/taxonomy.yaml}），SQL 表达不了。
 * 所以 Java 侧只负责按时间窗把脱敏明细拉出来，去噪、剥离模板话术、词表抽取与聚合
 * 全部收口在 Python 侧 —— 这样才能保证「排除口径」与两个分母绝对一致。
 *
 * <p><b>为什么不含姓名与联系方式</b>：跨工单聚合是跨人分析，调用方只需要知道
 * 「哪类故障多少单」，不需要知道「是谁报的」。{@code creator_id}/{@code assignee_id}/
 * {@code contact}/{@code location} 一律不出现在投影里；工单号本身是业务单号，保留
 * 用于下钻核验。
 */
@Data
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class TicketScanVO {

    private String ticketId;
    private String categoryId;
    private String title;
    private String description;
    private LocalDateTime createdAt;
    /** 处理时长统计用；三列在主表里已存在，零 DDL 即可产出。 */
    private LocalDateTime firstResponseAt;
    private LocalDateTime solvedAt;
    private LocalDateTime completedAt;
    /**
     * 处理方案（{@code ticket_resolution.solution}）。当前无数据时为空串。
     *
     * <p>根因维度**只从这里抽取**，不从工单描述推断 —— 从描述猜根因正是幻觉的主要来源。
     * 读取路径提前就位：等工单开始沉淀解决方案记录，无需改代码即可产出根因占比。
     */
    private String resolution;
}