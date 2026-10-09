package com.itticket.consultation.adapter;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Per-request execution state; audit versions never authorize answer citations. */
public final class RagExecutionAudit {
    private final Set<String> retrievedVersions = new LinkedHashSet<>();

    public synchronized void recordRetrievedVersions(List<String> versions) {
        retrievedVersions.addAll(versions);
    }

    public synchronized List<String> retrievedVersionIds() {
        return List.copyOf(retrievedVersions);
    }
}
