package com.itticket.consultation.adapter.policy;
import com.itticket.consultation.adapter.*;
public interface RequestClassifier { RequestVerdict classify(RagQuery query, RagCallContext context); }
