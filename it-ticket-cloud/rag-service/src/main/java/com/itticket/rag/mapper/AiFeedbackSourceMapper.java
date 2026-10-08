package com.itticket.rag.mapper;

import com.itticket.rag.dto.AiFeedbackCandidate;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import java.util.List;

public interface AiFeedbackSourceMapper {
    /** 使用请求键匹配问答，避免多轮/并发问答按时间配错；已入库的来源不再消费。 */
    @Select("""
        SELECT i.interaction_id, i.session_id, c.creator_id AS author_id,
               c.category_id, q.content AS question, a.content AS answer
        FROM ai_interaction i
        JOIN consultation c ON c.session_id = i.session_id
        JOIN consultation_message a ON a.session_id = i.session_id
          AND a.sender_type = 'AI'
          AND JSON_UNQUOTE(JSON_EXTRACT(a.citation_json, '$.interactionId')) = i.interaction_id
        JOIN consultation_message q ON q.session_id = a.session_id
          AND q.sender_type = 'EMPLOYEE'
          AND q.client_message_id = CONCAT('ai-q:', SUBSTRING(a.client_message_id, 6))
        WHERE i.feedback = 'HELPFUL' AND i.interaction_id > #{afterId}
          AND a.client_message_id LIKE 'ai-a:%'
          AND a.withdrawn_at IS NULL AND q.withdrawn_at IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(a.citation_json, '$.replyType')) = 'ANSWER'
          AND JSON_UNQUOTE(JSON_EXTRACT(a.citation_json, '$.generalAnswer')) = 'true'
          AND JSON_LENGTH(JSON_EXTRACT(a.citation_json, '$.citations')) = 0
          AND NOT EXISTS (SELECT 1 FROM knowledge_article k
              WHERE k.article_id = CONCAT('ai-', LEFT(SHA2(i.interaction_id, 256), 60)))
        ORDER BY i.interaction_id
        LIMIT #{batchSize}
        """)
    List<AiFeedbackCandidate> findPending(@Param("afterId") String afterId, @Param("batchSize") int batchSize);
}
