package com.itticket.ticket.mapper;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Param;

/**
 * 工单删除（PLATFORM_ADMIN 专属）：清理工单的全部关联行。
 * 各表均无外键约束，删除顺序无关紧要，须在事务内调用（见 TicketService#delete）。
 */
public interface TicketPurgeMapper {

    @Delete("DELETE FROM ticket_transition WHERE ticket_id = #{ticketId}")
    int purgeTransitions(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM ticket_message WHERE ticket_id = #{ticketId}")
    int purgeMessages(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM ticket_resolution WHERE ticket_id = #{ticketId}")
    int purgeResolutions(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM ticket_acceptance WHERE ticket_id = #{ticketId}")
    int purgeAcceptances(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM ticket_field_value WHERE ticket_id = #{ticketId}")
    int purgeFieldValues(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM supplement_request WHERE ticket_id = #{ticketId}")
    int purgeSupplements(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM external_wait WHERE ticket_id = #{ticketId}")
    int purgeExternalWaits(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM sla_instance WHERE ticket_id = #{ticketId}")
    int purgeSlaInstances(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM assignment WHERE biz_type = 'TICKET' AND biz_id = #{ticketId}")
    int purgeAssignments(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM attachment WHERE biz_type = 'TICKET' AND biz_id = #{ticketId}")
    int purgeAttachments(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM exception_queue WHERE object_type = 'TICKET' AND object_id = #{ticketId}")
    int purgeExceptions(@Param("ticketId") String ticketId);

    /** 通知无 ticket_id 列，action_url 有 /tickets/{id} 与 ?ticket={id} 两种格式，按工单号通配（TK+13位号段足够唯一） */
    @Delete("DELETE FROM notification WHERE action_url LIKE CONCAT('%', #{ticketId}, '%')")
    int purgeNotifications(@Param("ticketId") String ticketId);

    @Delete("DELETE FROM outbox_event WHERE aggregate_type = 'TICKET' AND aggregate_id = #{ticketId}")
    int purgeOutbox(@Param("ticketId") String ticketId);
}