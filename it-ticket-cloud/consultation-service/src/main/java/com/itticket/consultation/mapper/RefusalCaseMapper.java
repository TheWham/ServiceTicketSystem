package com.itticket.consultation.mapper;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.consultation.dto.RefusalCaseRow;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 拒答案例实时联查:AI REFUSE 消息 + 同会话最近一条员工提问 + ai_interaction 置信度
 * + LEFT JOIN bad_case_review 处置状态(零同步队列,待处置天然实时)。
 */
@Mapper
public interface RefusalCaseMapper {

    @Select("""
            SELECT
              ai_msg.message_id AS messageId,
              ai_msg.session_id AS sessionId,
              q.content AS questionText,
              JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.refusalReason')) AS refusalReason,
              it.confidence AS confidence,
              ai_msg.sent_at AS sentAt,
              CASE WHEN r.id IS NULL THEN 'PENDING' ELSE 'REVIEWED' END AS reviewStatus,
              r.decision AS decision
            FROM consultation_message ai_msg
            JOIN consultation_message q
              ON q.session_id = ai_msg.session_id
             AND q.sender_type = 'EMPLOYEE'
             AND q.sent_at = (
                   SELECT MAX(q2.sent_at) FROM consultation_message q2
                   WHERE q2.session_id = ai_msg.session_id
                     AND q2.sender_type = 'EMPLOYEE'
                     AND q2.sent_at < ai_msg.sent_at)
            LEFT JOIN ai_interaction it
              ON it.interaction_id = JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.interactionId'))
            LEFT JOIN bad_case_review r ON r.ai_message_id = ai_msg.message_id
            WHERE ai_msg.sender_type = 'AI'
              AND ai_msg.withdrawn_at IS NULL
              AND JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.replyType')) = 'REFUSE'
              AND (#{status} = 'ALL'
                   OR (#{status} = 'PENDING' AND r.id IS NULL)
                   OR (#{status} = 'REVIEWED' AND r.id IS NOT NULL))
              AND (#{keyword} IS NULL OR q.content LIKE CONCAT('%', #{keyword}, '%'))
            ORDER BY ai_msg.sent_at DESC, ai_msg.message_id DESC
            """)
    Page<RefusalCaseRow> selectRefusalCases(Page<RefusalCaseRow> page,
                                            @Param("status") String status,
                                            @Param("keyword") String keyword);
}
