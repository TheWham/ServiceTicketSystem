package com.itticket.consultation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.consultation.entity.ConsultationMessage;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ConsultationMessageMapper extends BaseMapper<ConsultationMessage> {
    /** Match server-written AI replies before LIMIT; a client-supplied ai-q prefix alone is not provenance. */
    @Select("""
            SELECT m.message_id, m.sender_type, m.content
            FROM consultation_message m
            WHERE m.session_id = #{sessionId}
              AND m.withdrawn_at IS NULL
              AND (#{currentClientMessageId} IS NULL OR m.client_message_id <> #{currentClientMessageId})
              AND (
                (m.sender_type = 'EMPLOYEE' AND m.sender_id = #{creatorId} AND m.client_message_id LIKE 'ai-q:%'
                 AND EXISTS (
                   SELECT 1 FROM consultation_message a
                   WHERE a.session_id = m.session_id AND a.sender_type = 'AI'
                     AND a.client_message_id = CONCAT('ai-a:', SUBSTRING(m.client_message_id, 6))))
                OR
                (m.sender_type = 'AI' AND m.client_message_id LIKE 'ai-a:%'
                 AND EXISTS (
                   SELECT 1 FROM consultation_message q
                   WHERE q.session_id = m.session_id AND q.sender_type = 'EMPLOYEE'
                     AND q.sender_id = #{creatorId} AND q.withdrawn_at IS NULL
                     AND q.client_message_id = CONCAT('ai-q:', SUBSTRING(m.client_message_id, 6))
                     AND (#{currentClientMessageId} IS NULL OR q.client_message_id <> #{currentClientMessageId})))
              )
              AND m.content IS NOT NULL
              AND TRIM(REPLACE(REPLACE(REPLACE(m.content, CHAR(9), ''), CHAR(10), ''), CHAR(13), '')) <> ''
            ORDER BY m.sent_at DESC, m.message_id DESC
            LIMIT #{maxMessages}
            """)
    List<ConsultationMessage> selectAiHistory(@Param("sessionId") String sessionId,
                                              @Param("creatorId") String creatorId,
                                              @Param("currentClientMessageId") String currentClientMessageId,
                                              @Param("maxMessages") int maxMessages);
}
