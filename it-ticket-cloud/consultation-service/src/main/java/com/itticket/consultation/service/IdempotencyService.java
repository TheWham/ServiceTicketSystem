package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.IdempotencyRecord;
import com.itticket.consultation.enums.IdempotencyStatus;
import com.itticket.consultation.mapper.IdempotencyRecordMapper;
import com.itticket.consultation.support.Hashes;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDateTime;
import java.util.function.Supplier;

/**
 * 幂等执行器(RD-002)。
 *
 * <p>语义:
 * <ul>
 *   <li>相同 (主体, 操作, 幂等键) 且请求摘要相同 → 直接返回首次结果,不执行新动作;</li>
 *   <li>相同键但摘要不同 → 返回 IDEMPOTENCY_CONFLICT,不执行新动作;</li>
 *   <li>幂等记录与业务写入在同一事务内提交,因此不会出现"业务已生效但幂等记录丢失"。</li>
 * </ul>
 *
 * <p>实现要点:幂等记录在事务的最后插入。并发重复请求会在唯一索引上阻塞,先提交者成功,
 * 后到者拿到 DuplicateKeyException 并整体回滚,再读取已提交结果重放。因此
 * {@code IdempotencyStatus.IN_PROGRESS} 不会被写库 —— 记录一旦存在就必然对应一次已完成的业务动作。
 * 捕获必须发生在事务边界之外,否则回滚语义会被破坏,故这里使用 {@link TransactionTemplate}
 * 而不是 {@code @Transactional} 自调用。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class IdempotencyService {

    private final IdempotencyRecordMapper recordMapper;
    private final TransactionTemplate transactionTemplate;
    private final ConsultationProperties properties;

    public <T> IdempotentResult<T> execute(String ownerId, String operation, String idempotencyKey,
                                           Object requestPayload, Class<T> resultType, Supplier<T> action) {
        validateKey(idempotencyKey);
        String requestHash = Hashes.sha256Hex(operation + '|' + Json.write(requestPayload));

        IdempotencyRecord existing = find(ownerId, operation, idempotencyKey);
        if (existing != null) {
            return replay(existing, requestHash, resultType);
        }

        try {
            T value = transactionTemplate.execute(status -> {
                T result = action.get();
                insertRecord(ownerId, operation, idempotencyKey, requestHash, result);
                return result;
            });
            return new IdempotentResult<>(value, false);
        } catch (DuplicateKeyException e) {
            // 并发同键:本事务已整体回滚,胜出者的结果已提交,按重放返回。
            IdempotencyRecord winner = find(ownerId, operation, idempotencyKey);
            if (winner == null) {
                // 唯一冲突不是来自幂等表(例如 consultation_message 的 client_message_id)。
                throw new ApiException(ApiCode.IDEMPOTENCY_CONFLICT, "重复请求与已存在记录冲突");
            }
            return replay(winner, requestHash, resultType);
        }
    }

    private <T> IdempotentResult<T> replay(IdempotencyRecord record, String requestHash, Class<T> resultType) {
        if (!requestHash.equals(record.getRequestHash())) {
            throw new ApiException(ApiCode.IDEMPOTENCY_CONFLICT, "相同幂等键对应的请求内容不一致");
        }
        return new IdempotentResult<>(Json.read(record.getResultJson(), resultType), true);
    }

    private void validateKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank() || idempotencyKey.length() > 128) {
            throw ApiException.validation(java.util.List.of(
                    com.itticket.consultation.api.FieldIssue.required("Idempotency-Key",
                            "写操作必须携带 1-128 字符的 Idempotency-Key")));
        }
    }

    private IdempotencyRecord find(String ownerId, String operation, String idempotencyKey) {
        return recordMapper.selectOne(Wrappers.<IdempotencyRecord>lambdaQuery()
                .eq(IdempotencyRecord::getOwnerId, ownerId)
                .eq(IdempotencyRecord::getOperation, operation)
                .eq(IdempotencyRecord::getIdempotencyKey, idempotencyKey));
    }

    private void insertRecord(String ownerId, String operation, String idempotencyKey,
                              String requestHash, Object result) {
        LocalDateTime now = Times.nowUtc();
        IdempotencyRecord record = new IdempotencyRecord();
        record.setRecordId(Ids.idempotencyId());
        record.setOwnerId(ownerId);
        record.setOperation(operation);
        record.setIdempotencyKey(idempotencyKey);
        record.setRequestHash(requestHash);
        record.setStatus(IdempotencyStatus.SUCCEEDED);
        record.setResultJson(Json.write(result));
        record.setExpiresAt(now.plusHours(properties.getIdempotencyTtlHours()));
        record.setCreatedAt(now);
        record.setUpdatedAt(now);
        recordMapper.insert(record);
    }
}
