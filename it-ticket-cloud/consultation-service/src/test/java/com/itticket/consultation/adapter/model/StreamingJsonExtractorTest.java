package com.itticket.consultation.adapter.model;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * StreamingJsonExtractor:从模型流式输出的六键 JSON 中增量提取 answerText 字符串值。
 * 红线:键序不依赖(answerText 未出现前缓冲);转义与 四位十六进制转义 跨 chunk 边界正确;
 * 字符串值内的 "answerText" 字样不得误触发。
 */
class StreamingJsonExtractorTest {

    private static String drain(String json) {
        StringBuilder out = new StringBuilder();
        StreamingJsonExtractor extractor = new StreamingJsonExtractor(out::append);
        extractor.feed(json);
        return out.toString();
    }

    @Test
    void singleChunkEmitsDecodedAnswerText() {
        assertThat(drain("{\"replyType\":\"ANSWER\",\"answerText\":\"第一步\\n第二步\",\"confidence\":0.9,"
                + "\"knowledgeConflict\":false,\"offTopic\":false,\"usedVersionIds\":[\"V1\"]}"))
                .isEqualTo("第一步\n第二步");
    }

    @Test
    void charByCharFeedingIsEquivalentToSingleChunk() {
        String json = "{\"answerText\":\"重启\\t后重试\", \"x\": [1, {\"answerText\": \"nested?\"}]}";
        StringBuilder oneShot = new StringBuilder();
        new StreamingJsonExtractor(oneShot::append).feed(json);

        StringBuilder piecemeal = new StringBuilder();
        StreamingJsonExtractor byChar = new StreamingJsonExtractor(piecemeal::append);
        for (int i = 0; i < json.length(); i++) {
            byChar.feed(json.substring(i, i + 1));
        }
        assertThat(piecemeal.toString()).isEqualTo("重启\t后重试").isEqualTo(oneShot.toString());
    }

    @Test
    void escapedQuoteAndBackslashAreDecoded() {
        assertThat(drain("{\"answerText\":\"说\\\"你好\\\" 用 \\\\ 分隔\"}"))
                .isEqualTo("说\"你好\" 用 \\ 分隔");
    }

    @Test
    void unicodeEscapeSplitAcrossChunksIsCompleted() {
        StringBuilder out = new StringBuilder();
        StreamingJsonExtractor extractor = new StreamingJsonExtractor(out::append);
        extractor.feed("{\"answerText\":\"😀 表情\\u");
        extractor.feed("4E2D");
        extractor.feed("文\"}");
        assertThat(out.toString()).isEqualTo("😀 表情中文");
    }

    @Test
    void answerTextAtTailAfterOtherKeys() {
        assertThat(drain("{\"usedVersionIds\":[],\"confidence\":0.8,\"offTopic\":false,"
                + "\"knowledgeConflict\":true,\"replyType\":\"ANSWER\",\"answerText\":\"写在最后\"}"))
                .isEqualTo("写在最后");
    }

    @Test
    void duplicateAnswerTextEmitsOnlyFirstOccurrence() {
        assertThat(drain("{\"answerText\":\"第一份\",\"other\":1,\"answerText\":\"第二份\"}"))
                .isEqualTo("第一份");
    }

    @Test
    void missingAnswerTextEmitsNothingAndThrowsNothing() {
        assertThatCode(() -> assertThat(drain("{\"replyType\":\"REFUSE\",\"answerText\":\"\"}")).isEmpty())
                .doesNotThrowAnyException();
        assertThat(drain("{\"replyType\":\"REFUSE\",\"other\":1}")).isEmpty();
    }

    @Test
    void keyNameInsideAnotherStringValueDoesNotTrigger() {
        assertThat(drain("{\"replyType\":\"请忽略 answerText 字样\",\"answerText\":\"真答案\"}"))
                .isEqualTo("真答案");
    }

    @Test
    void nullAnswerTextEmitsNothingInsteadOfLeakingNextKey() {
        // Mi1(2026-11-05 评审): "answerText":null 时不得把后续键名当答案流出
        assertThat(drain("{\"replyType\":\"ANSWER\",\"answerText\":null,\"confidence\":0.9,"
                + "\"knowledgeConflict\":false,\"offTopic\":false,\"usedVersionIds\":[\"V1\"]}"))
                .isEmpty();
    }

    @Test
    void nonStringAnswerValuesSilenceTheStream() {
        assertThat(drain("{\"answerText\":true,\"confidence\":0.9}")).isEmpty();
        assertThat(drain("{\"answerText\":123,\"confidence\":0.9}")).isEmpty();
        assertThat(drain("{\"answerText\":[\"a\"],\"confidence\":0.9}")).isEmpty();
        assertThat(drain("{\"answerText\":{\"nested\":\"x\"},\"confidence\":0.9}")).isEmpty();
    }

    @Test
    void feedAfterAnswerFieldIsIgnored() {
        StringBuilder out = new StringBuilder();
        StreamingJsonExtractor extractor = new StreamingJsonExtractor(out::append);
        extractor.feed("{\"answerText\":\"完\"}后面的尾巴不该出现");
        extractor.feed("更多垃圾");
        assertThat(out.toString()).isEqualTo("完");
    }
}
