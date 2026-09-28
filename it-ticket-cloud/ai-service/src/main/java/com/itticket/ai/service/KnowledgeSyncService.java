package com.itticket.ai.service;

import com.itticket.ai.config.AiProperties;
import com.itticket.ai.feign.TicketClient;
import com.itticket.common.api.Result;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 知识回流:定时从 ticket-service 拉取「已完成」工单,把「问题+工程师解决方案」入库,
 * 让 AI 能力随工单积累持续增长。幂等:同一工单号只入一次(existsBySource 防重)。
 * 任务异常不抛出,避免影响调度线程。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeSyncService {

    /** 增量游标:本轮拉取只取 solved_at 晚于该时间的工单;首次为 null(全量) */
    private final AtomicReference<LocalDateTime> lastSyncTime = new AtomicReference<>();

    private final TicketClient ticketClient;
    private final KnowledgeService knowledgeService;
    private final AiProperties properties;

    @Scheduled(fixedDelayString = "${ai.sync.fixed-delay-ms:600000}",
            initialDelayString = "${ai.sync.initial-delay-ms:60000}")
    public void syncSolvedTickets() {
        if (!properties.getSync().isEnabled()) {
            return;
        }
        try {
            // since 传 ISO 格式,ticket-service 端 LocalDateTime.parse 可直接解析
            LocalDateTime since = lastSyncTime.get();
            Result<List<TicketClient.SolvedTicket>> result = ticketClient.solvedTickets(
                    since == null ? null : since.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME), 100);
            if (result == null || result.getCode() != 0 || result.getData() == null) {
                log.warn("[SYNC] 拉取已完成工单失败: {}", result == null ? "无响应" : result.getMsg());
                return;
            }

            int imported = 0;
            LocalDateTime maxSolvedAt = since;
            for (TicketClient.SolvedTicket ticket : result.getData()) {
                // 幂等防重:同一张工单只回流一次
                if (knowledgeService.existsBySource("TICKET", ticket.ticketId())) {
                    continue;
                }
                String solution = (ticket.solutionRemark() == null || ticket.solutionRemark().isBlank())
                        ? "（工程师未填写详细处理结论）" : ticket.solutionRemark();
                // 入库文本 = 分类 + 问题 + 解决方案;注意:工单内容为企业内部数据,入库前请确保已脱敏
                String content = "问题分类：" + ticket.category()
                        + "\n问题：" + ticket.title() + "。" + ticket.description()
                        + "\n解决方案：" + solution;
                knowledgeService.add(ticket.title(), content, ticket.category(), "TICKET", ticket.ticketId());
                imported++;

                LocalDateTime solvedAt = parseSolvedAt(ticket.solvedAt());
                if (solvedAt != null && (maxSolvedAt == null || solvedAt.isAfter(maxSolvedAt))) {
                    maxSolvedAt = solvedAt;
                }
            }
            if (maxSolvedAt != null) {
                lastSyncTime.set(maxSolvedAt);
            }
            log.info("[SYNC] 知识回流完成,本次拉取 {} 张已完成工单,新入库 {} 张",
                    result.getData().size(), imported);
        } catch (Exception e) {
            log.error("[SYNC] 知识回流任务失败: {}", e.getMessage());
        }
    }

    /** 兼容展示格式(yyyy-MM-dd HH:mm:ss)与 ISO 格式 */
    private static LocalDateTime parseSolvedAt(String text) {
        if (text == null || text.isBlank()) {
            return null;
        }
        try {
            return LocalDateTime.parse(text, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        } catch (Exception e) {
            try {
                return LocalDateTime.parse(text.trim());
            } catch (Exception ex) {
                return null;
            }
        }
    }
}
