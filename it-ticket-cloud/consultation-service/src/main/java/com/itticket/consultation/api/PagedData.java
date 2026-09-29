package com.itticket.consultation.api;

import java.util.List;

/** 分页数据体(OpenAPI 05 PagedEnvelope.data)。 */
public record PagedData<T>(List<T> items, int page, int pageSize, long total) {
}
