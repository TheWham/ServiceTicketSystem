package com.itticket.consultation.adapter.generation;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.util.List;
public record GenerationResult(AiReplyType replyType, String answerText,
        List<String> usedVersionIds, BigDecimal confidence, AiRefusalReason refusalReason,
        String modelVersion) {
    public GenerationResult { usedVersionIds = List.copyOf(usedVersionIds); }
}
