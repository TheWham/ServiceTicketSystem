package com.itticket.consultation.support;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 支撑工具类纯单元测试(Times / Ids / Hashes / Json)。
 *
 * <p>契约来源:
 * <ul>
 *   <li>DM-001 / DM-001.1:持久化时间一律是 UTC 挂钟时间,精度对齐 DATETIME(6);
 *       对外 JSON 输出 ISO 8601 带时区(AI-002);</li>
 *   <li>DM-003:SessionId 以 CS 为前缀,长度不超过 32;</li>
 *   <li>RD-002:幂等请求摘要为 64 位十六进制,同一请求体必须得到稳定摘要;</li>
 *   <li>EV-007:JSON 列与事件 envelope 的序列化必须稳定可重放,属性按字典序输出。</li>
 * </ul>
 *
 * <p>测试名按 TR-001 携带 F-13(AI/RAG 支撑)与 AC-07(幂等)标识。
 */
class SupportUtilsTest {

    @Nested
    @DisplayName("Times(DM-001 时间口径)")
    class TimesTest {

        @Test
        @DisplayName("F-13 nowUtc 截断到微秒,匹配 DATETIME(6) 精度")
        void f13_now_utc_is_truncated_to_microseconds() {
            for (int i = 0; i < 20; i++) {
                LocalDateTime now = Times.nowUtc();
                assertThat(now.getNano() % 1000)
                        .as("纳秒部分必须已被截断到微秒")
                        .isZero();
            }
        }

        @Test
        @DisplayName("F-13 nowUtc 返回 UTC 挂钟时间,不受 JVM 默认时区影响")
        void f13_now_utc_is_utc_wall_clock() {
            LocalDateTime reference = LocalDateTime.now(ZoneOffset.UTC);
            LocalDateTime now = Times.nowUtc();

            assertThat(now).isAfter(reference.minusMinutes(1));
            assertThat(now).isBefore(reference.plusMinutes(1));
        }

        @Test
        @DisplayName("F-13 iso 输出 ISO 8601 带 Z 且保留 6 位微秒(AI-002)")
        void f13_iso_renders_iso8601_with_microseconds() {
            assertThat(Times.iso(LocalDateTime.of(2026, 3, 2, 1, 2, 3, 123_456_000)))
                    .isEqualTo("2026-03-02T01:02:03.123456Z");
            assertThat(Times.iso(LocalDateTime.of(2026, 3, 2, 1, 2, 3)))
                    .isEqualTo("2026-03-02T01:02:03.000000Z");
            assertThat(Times.iso(Times.nowUtc()))
                    .matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6}Z");
        }

        @Test
        @DisplayName("F-13 toInstant 与 fromInstant 按 UTC 往返一致")
        void f13_instant_round_trip_is_stable() {
            LocalDateTime utc = LocalDateTime.of(2026, 3, 2, 1, 2, 3, 123_456_000);

            Instant instant = Times.toInstant(utc);

            assertThat(instant).isEqualTo(utc.toInstant(ZoneOffset.UTC));
            assertThat(Times.fromInstant(instant)).isEqualTo(utc);
        }

        @Test
        @DisplayName("F-13 fromInstant 同样截断到微秒,纳秒精度不会写进存储口径")
        void f13_from_instant_truncates_to_microseconds() {
            Instant nanos = Instant.parse("2026-03-02T01:02:03.123456789Z");

            LocalDateTime utc = Times.fromInstant(nanos);

            assertThat(utc).isEqualTo(LocalDateTime.of(2026, 3, 2, 1, 2, 3, 123_456_000));
            assertThat(utc.getNano() % 1000).isZero();
        }

        @Test
        @DisplayName("F-13 null 入参一律返回 null,不抛异常")
        void f13_null_inputs_return_null() {
            assertThat(Times.iso(null)).isNull();
            assertThat(Times.toInstant(null)).isNull();
            assertThat(Times.fromInstant(null)).isNull();
        }
    }

    @Nested
    @DisplayName("Ids(DM-001 / DM-003 业务 ID)")
    class IdsTest {

        @Test
        @DisplayName("F-13 sessionId 以 CS 开头且长度不超过 32(DM-003)")
        void f13_session_id_matches_dm003_format() {
            String sessionId = Ids.sessionId();

            assertThat(sessionId).startsWith(Ids.SESSION_PREFIX);
            assertThat(sessionId).hasSize(22);
            assertThat(sessionId.length()).isLessThanOrEqualTo(32);
            // CS + yyyyMMdd + 12 位 Crockford Base32(去掉 I、L、O、U)
            assertThat(sessionId).matches("^CS\\d{8}[0-9A-HJKMNP-TV-Z]{12}$");
        }

        @Test
        @DisplayName("F-13 sessionId 多次调用不重复")
        void f13_session_ids_do_not_collide() {
            Set<String> ids = new HashSet<>();
            for (int i = 0; i < 500; i++) {
                ids.add(Ids.sessionId());
            }

            assertThat(ids).hasSize(500);
        }

        @Test
        @DisplayName("F-13 其余业务 ID 前缀稳定且长度可控,均不超过 32 字符")
        void f13_other_ids_keep_stable_prefix_and_length() {
            assertThat(Ids.messageId()).startsWith("MSG").hasSize(27);
            assertThat(Ids.interactionId()).startsWith("AIX").hasSize(27);
            assertThat(Ids.assignmentId()).startsWith("ASG").hasSize(27);
            assertThat(Ids.slaId()).startsWith("SLA").hasSize(27);
            assertThat(Ids.eventId()).startsWith("EV").hasSize(28);
            assertThat(Ids.auditId()).startsWith("AUD").hasSize(27);
            assertThat(Ids.idempotencyId()).startsWith("IDK").hasSize(27);
            assertThat(Ids.exceptionId()).startsWith("EXQ").hasSize(27);
        }
    }

    @Nested
    @DisplayName("Hashes(RD-002 幂等请求摘要)")
    class HashesTest {

        /** SHA-256("abc") 的标准向量。 */
        private static final String SHA256_ABC =
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
        /** SHA-256("") 的标准向量。 */
        private static final String SHA256_EMPTY =
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

        @Test
        @DisplayName("AC-07 sha256Hex 输出 64 位小写十六进制,与标准向量一致")
        void ac07_sha256_matches_standard_vectors() {
            assertThat(Hashes.sha256Hex("abc")).isEqualTo(SHA256_ABC);
            assertThat(Hashes.sha256Hex("")).isEqualTo(SHA256_EMPTY);
        }

        @Test
        @DisplayName("AC-07 摘要长度恒为 64 且只含小写十六进制字符(request_hash CHAR(64))")
        void ac07_sha256_is_lowercase_hex_of_length_64() {
            String hash = Hashes.sha256Hex("{\"title\":\"VPN 无法连接\"}");

            assertThat(hash).hasSize(64);
            assertThat(hash).matches("^[0-9a-f]{64}$");
        }

        @Test
        @DisplayName("AC-07 同输入同输出、不同输入不同输出:幂等键冲突判定可靠")
        void ac07_sha256_is_deterministic_and_collision_sensitive() {
            String payload = "{\"sessionId\":\"CS20260302ABCDEFGHJKMN\"}";

            assertThat(Hashes.sha256Hex(payload)).isEqualTo(Hashes.sha256Hex(payload));
            assertThat(Hashes.sha256Hex(payload)).isNotEqualTo(Hashes.sha256Hex(payload + " "));
            assertThat(Hashes.sha256Hex("中文请求体")).isEqualTo(Hashes.sha256Hex("中文请求体"));
            assertThat(Hashes.sha256Hex("中文请求体")).isNotEqualTo(Hashes.sha256Hex("中文请求休"));
        }
    }

    @Nested
    @DisplayName("Json(EV-007 稳定序列化)")
    class JsonTest {

        @Test
        @DisplayName("AC-07 Map 属性按字典序输出,保证 requestHash 对同一请求体稳定")
        void ac07_map_entries_are_ordered_by_key() {
            Map<String, Object> unordered = new LinkedHashMap<>();
            unordered.put("zeta", 1);
            unordered.put("alpha", "a");
            unordered.put("mid", true);

            assertThat(Json.write(unordered))
                    .isEqualTo("{\"alpha\":\"a\",\"mid\":true,\"zeta\":1}");
        }

        @Test
        @DisplayName("AC-07 嵌套 Map 同样按字典序输出,不同插入顺序得到同一摘要")
        void ac07_nested_maps_produce_identical_hash_regardless_of_insertion_order() {
            Map<String, Object> nestedA = new LinkedHashMap<>();
            nestedA.put("b", 2);
            nestedA.put("a", 1);
            Map<String, Object> first = new LinkedHashMap<>();
            first.put("payload", nestedA);
            first.put("actor", "U001");

            Map<String, Object> nestedB = new LinkedHashMap<>();
            nestedB.put("a", 1);
            nestedB.put("b", 2);
            Map<String, Object> second = new LinkedHashMap<>();
            second.put("actor", "U001");
            second.put("payload", nestedB);

            assertThat(Json.write(first)).isEqualTo(Json.write(second));
            assertThat(Hashes.sha256Hex(Json.write(first)))
                    .isEqualTo(Hashes.sha256Hex(Json.write(second)));
        }

        @Test
        @DisplayName("F-13 write / read 往返保持内容一致")
        void f13_write_and_read_round_trip() {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("sessionId", "CS20260302ABCDEFGHJKMN");
            payload.put("confidence", 1);
            payload.put("suggestTransfer", true);

            String json = Json.write(payload);
            Map<String, Object> restored = Json.readMap(json);

            assertThat(restored).containsExactlyInAnyOrderEntriesOf(payload);
        }

        @Test
        @DisplayName("F-13 readList 还原 JSON 数组")
        void f13_read_list_restores_array() {
            List<Map<String, Object>> citations = List.of(
                    Map.<String, Object>of("articleId", "KA-0001"),
                    Map.<String, Object>of("articleId", "KA-0002"));

            List<Map<String, Object>> restored = Json.readList(Json.write(citations));

            assertThat(restored).hasSize(2);
            assertThat(restored.get(0)).containsEntry("articleId", "KA-0001");
            assertThat(restored.get(1)).containsEntry("articleId", "KA-0002");
        }

        @Test
        @DisplayName("F-13 null 与空白入参:write 返回 null,read 返回 null,不抛异常")
        void f13_null_inputs_are_handled() {
            assertThat(Json.write(null)).isNull();
            assertThat(Json.read(null, Map.class)).isNull();
            assertThat(Json.read("", Map.class)).isNull();
            assertThat(Json.read("   ", Map.class)).isNull();
            assertThat(Json.readMap(null)).isNull();
            assertThat(Json.readList(null)).isNull();
        }

        @Test
        @DisplayName("F-13 非法 JSON 抛出 IllegalStateException,不静默返回 null")
        void f13_invalid_json_fails_loudly() {
            assertThat(catchIllegalState(() -> Json.read("{not-json", Map.class))).isTrue();
        }

        private boolean catchIllegalState(Runnable runnable) {
            try {
                runnable.run();
                return false;
            } catch (IllegalStateException expected) {
                return true;
            }
        }
    }
}
