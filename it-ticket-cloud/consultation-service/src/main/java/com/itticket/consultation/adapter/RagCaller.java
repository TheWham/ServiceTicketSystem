package com.itticket.consultation.adapter;
public record RagCaller(String userId, String role) {
    public RagCaller {
        if (userId == null || userId.isBlank() || role == null || role.isBlank())
            throw new IllegalArgumentException("Authenticated caller required");
    }
}
