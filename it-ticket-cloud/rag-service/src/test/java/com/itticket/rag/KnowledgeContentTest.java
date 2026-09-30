package com.itticket.rag;

import com.itticket.rag.support.KnowledgeContent;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

/**
 * 知识正文 content 列（V2_2 之后的 JSON 列）读写测试，权威四键：title / summary / keywords / body。
 *
 * <p>规范关联：DM-004 核心持久化实体（specs/01-data-model-strong-types.md:100）规定
 * knowledge_version.content 的键结构；读取侧对脏数据（非 JSON/缺键/空值）必须容错兜底，
 * 不因单条历史数据异常中断检索或索引重建。</p>
 */
public class KnowledgeContentTest {

    @Test
    public void buildProducesAllFourKeys() {
        String json = KnowledgeContent.build("VPN 排查", "摘要内容", "vpn 连接", "正文步骤");

        Assertions.assertTrue(json.contains("\"title\":\"VPN 排查\""), json);
        Assertions.assertTrue(json.contains("\"summary\":\"摘要内容\""), json);
        Assertions.assertTrue(json.contains("\"keywords\":\"vpn 连接\""), json);
        Assertions.assertTrue(json.contains("\"body\":\"正文步骤\""), json);
    }

    @Test
    public void buildFillsMissingKeysWithEmptyStrings() {
        String json = KnowledgeContent.build(null, null, null, null);

        Assertions.assertEquals("", KnowledgeContent.summaryOf(json));
        Assertions.assertEquals("", KnowledgeContent.keywordsOf(json));
        Assertions.assertEquals(KnowledgeContent.TITLE_PLACEHOLDER, KnowledgeContent.titleOf(json));
    }

    @Test
    public void readRoundTripsTitleSummaryAndBody() {
        String json = KnowledgeContent.build("打印机离线排查", "网络/驱动/队列三类原因", "打印机 离线", "1. 检查电源\n2. 检查网线");

        Assertions.assertEquals("打印机离线排查", KnowledgeContent.titleOf(json));
        Assertions.assertEquals("网络/驱动/队列三类原因", KnowledgeContent.summaryOf(json));
        Assertions.assertEquals("打印机 离线", KnowledgeContent.keywordsOf(json));
        Assertions.assertTrue(KnowledgeContent.bodyOf(json).contains("检查网线"));
    }

    @Test
    public void titleFallsBackToSummaryThenBodyThenPlaceholder() {
        // 只有 summary
        Assertions.assertTrue(KnowledgeContent.titleOf(KnowledgeContent.build("", "只有摘要", "", ""))
                .startsWith("只有摘要"));
        // 只有 body
        Assertions.assertTrue(KnowledgeContent.titleOf(KnowledgeContent.build("", "", "", "只有正文内容"))
                .startsWith("只有正文内容"));
        // 全空
        Assertions.assertEquals(KnowledgeContent.TITLE_PLACEHOLDER,
                KnowledgeContent.titleOf(KnowledgeContent.build("", "", "", "")));
    }

    @Test
    public void malformedJsonDegradesGracefully() {
        // 非 JSON 文本不得抛异常，正文回退为原文本
        Assertions.assertEquals("明文正文", KnowledgeContent.bodyOf("明文正文"));
        Assertions.assertTrue(KnowledgeContent.titleOf("明文正文").length() > 0);
        Assertions.assertEquals("", KnowledgeContent.summaryOf("明文正文"));
        // null / 空白
        Assertions.assertEquals("", KnowledgeContent.bodyOf(null));
        Assertions.assertEquals(KnowledgeContent.TITLE_PLACEHOLDER, KnowledgeContent.titleOf(null));
    }
}
