package com.itticket.rag.dto;

/** 只由数据库读取的反馈来源，不能由客户端提交知识正文。 */
public record AiFeedbackCandidate(String interactionId, String sessionId, String authorId,
                                  String categoryId, String question, String answer) {
}
