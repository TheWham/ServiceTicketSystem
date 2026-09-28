package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.entity.Notification;
import com.itticket.ticket.mapper.NotificationMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 通知中心 —— PRD §14.2。站内通知拉取（前端通知中心轮询）。
 * 「查看≠行动」：通知仅作待办引导，行动通过 action_url 完成，不设已读状态。
 */
@RestController
@RequestMapping("/api/notifications")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationMapper notificationMapper;

    /** 我的站内通知列表（倒序分页） */
    @GetMapping
    public Result<Map<String, Object>> list(@RequestParam(defaultValue = "1") int page,
                                            @RequestParam(defaultValue = "20") int page_size) {
        String receiverId = UserContext.get().getUserId();
        QueryWrapper<Notification> qw = new QueryWrapper<Notification>()
                .eq("receiver_id", receiverId)
                .eq("channel", "INBOX")
                .orderByDesc("created_at");
        Page<Notification> p = notificationMapper.selectPage(new Page<>(page, page_size), qw);
        Map<String, Object> body = new HashMap<>();
        body.put("list", p.getRecords());
        body.put("total", p.getTotal());
        body.put("page", page);
        body.put("page_size", page_size);
        return Result.ok(body);
    }

    /** 待处理通知数（status=PENDING 或 SENT 的站内条数，用于角标） */
    @GetMapping("/pending-count")
    public Result<Long> pendingCount() {
        String receiverId = UserContext.get().getUserId();
        Long cnt = notificationMapper.selectCount(new QueryWrapper<Notification>()
                .eq("receiver_id", receiverId)
                .eq("channel", "INBOX"));
        return Result.ok(cnt);
    }
}
