package com.itticket.rag;

import com.itticket.common.api.BizException;
import com.itticket.rag.config.DifyProperties;
import com.itticket.rag.dto.DifyRetrievalRequest;
import com.itticket.rag.service.DifyDatasetClient;
import com.itticket.rag.service.DifyKnowledgeService;
import com.itticket.rag.vo.DifyDocumentUploadResultVO;
import com.itticket.rag.vo.DifyRetrievalResultVO;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.mock.web.MockMultipartFile;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Dify 知识库通道测试：覆盖启用开关、文档上传（文件/文本）、索引状态轮询与混合召回映射。
 *
 * <p>纯单元测试：Mockito 打桩 DifyDatasetClient，不依赖真实 Dify 服务。</p>
 */
class DifyKnowledgeServiceTest {

    private DifyProperties enabledProperties() {
        DifyProperties properties = new DifyProperties();
        properties.setEnabled(true);
        properties.setApiKey("dataset-test-key");
        properties.setDatasetId("ds-001");
        properties.setTopK(3);
        properties.setScoreThreshold(0.2);
        return properties;
    }

    @Test
    void shouldRejectAllEndpointsWhenChannelDisabled() {
        DifyProperties properties = enabledProperties();
        properties.setEnabled(false);
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);

        DifyRetrievalRequest request = new DifyRetrievalRequest();
        request.setQuery("如何重置域账号密码");

        BizException retrievalFailure = Assertions.assertThrows(BizException.class, () -> service.retrieve(request));
        Assertions.assertTrue(retrievalFailure.getMessage().contains("Dify 通道未启用"));

        MockMultipartFile file = new MockMultipartFile("file", "a.md", "text/markdown", "内容".getBytes());
        Assertions.assertThrows(BizException.class, () -> service.uploadDocument(file, 0, 50, 0));
        Assertions.assertThrows(BizException.class,
                () -> service.createDocumentByText("a.md", "内容", 0, 50, 0));
        Assertions.assertThrows(BizException.class, () -> service.getIndexingStatus("batch-1"));

        verifyNoInteractions(client);
    }

    @Test
    void shouldUploadDocumentAndPollUntilCompleted() {
        DifyProperties properties = enabledProperties();
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        Mockito.when(client.ensureDataset())
                .thenReturn(DifyDatasetClient.Dataset.builder().id("ds-001").name("it-ticket-knowledge").build());
        Mockito.when(client.createDocumentByFile(eq("wifi.md"), any(byte[].class), eq(0), eq(50)))
                .thenReturn(DifyDatasetClient.DocumentCreateResult.builder()
                        .batch("batch-1")
                        .documentId("doc-1")
                        .documentName("wifi.md")
                        .indexingStatus("waiting")
                        .build());
        // 第一次仍在 indexing，第二次 completed —— 验证轮询而非一次性读取
        Mockito.when(client.getIndexingStatus("batch-1"))
                .thenReturn(List.of(DifyDatasetClient.IndexingStatus.builder()
                        .documentId("doc-1").indexingStatus("indexing").build()))
                .thenReturn(List.of(DifyDatasetClient.IndexingStatus.builder()
                        .documentId("doc-1").indexingStatus("completed").wordCount(128).build()));

        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);
        MockMultipartFile file = new MockMultipartFile("file", "wifi.md", "text/markdown",
                "# WiFi 配置\n步骤一二三".getBytes());

        DifyDocumentUploadResultVO result = service.uploadDocument(file, 0, 50, 30);

        Assertions.assertEquals("batch-1", result.getBatch());
        Assertions.assertEquals("ds-001", result.getDatasetId());
        Assertions.assertTrue(result.isWaited());
        Assertions.assertEquals("completed", result.getIndexingStatus());
        Assertions.assertEquals(1, result.getStatuses().size());
        Assertions.assertEquals(Integer.valueOf(128), result.getStatuses().get(0).getWordCount());
    }

    @Test
    void shouldCreateDocumentByTextWithoutWaitingWhenWaitSecondsZero() {
        DifyProperties properties = enabledProperties();
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        Mockito.when(client.createDocumentByText(eq("vpn.md"), anyString(), eq(200), eq(30)))
                .thenReturn(DifyDatasetClient.DocumentCreateResult.builder()
                        .batch("batch-2").documentId("doc-2").documentName("vpn.md")
                        .indexingStatus("waiting").build());

        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);
        DifyDocumentUploadResultVO result = service.createDocumentByText("vpn.md", "VPN 配置说明", 200, 30, 0);

        Assertions.assertEquals("batch-2", result.getBatch());
        Assertions.assertFalse(result.isWaited());
        Assertions.assertTrue(result.getStatuses().isEmpty());
        Mockito.verify(client, Mockito.never()).getIndexingStatus(anyString());
    }

    @Test
    void shouldRejectBlankTextDocument() {
        DifyProperties properties = enabledProperties();
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);

        Assertions.assertThrows(BizException.class, () -> service.createDocumentByText("n.md", "  ", 0, 50, 0));
        verifyNoInteractions(client);
    }

    @Test
    void shouldMapRetrieveRecordsAndDefaultSearchMethod() {
        DifyProperties properties = enabledProperties();
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        Mockito.when(client.retrieve(eq("打印机离线"), eq(null), eq(2), eq(null)))
                .thenReturn(DifyDatasetClient.RetrieveResult.builder()
                        .query("打印机离线")
                        .records(List.of(
                                DifyDatasetClient.RetrievedRecord.builder()
                                        .segmentId("seg-1").position(1).documentId("doc-1")
                                        .documentName("printer.md").content("重启打印服务")
                                        .keywords(List.of("打印机")).score(0.83).build(),
                                DifyDatasetClient.RetrievedRecord.builder()
                                        .segmentId("seg-2").position(2).documentId("doc-1")
                                        .documentName("printer.md").content("检查网络连通性")
                                        .score(0.41).build()))
                        .build());

        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);
        DifyRetrievalRequest request = new DifyRetrievalRequest();
        request.setQuery("打印机离线");
        request.setTopK(2);

        DifyRetrievalResultVO result = service.retrieve(request);

        Assertions.assertEquals("hybrid_search", result.getSearchMethod());
        Assertions.assertEquals("ds-001", result.getDatasetId());
        Assertions.assertEquals(2, result.getRecords().size());
        Assertions.assertEquals(0.83, result.getRecords().get(0).getScore());
        Assertions.assertEquals(List.of("打印机"), result.getRecords().get(0).getKeywords());
        Assertions.assertEquals("printer.md", result.getRecords().get(1).getDocumentName());
    }

    @Test
    void shouldUseRequestedSearchMethodWhenProvided() {
        DifyProperties properties = enabledProperties();
        DifyDatasetClient client = Mockito.mock(DifyDatasetClient.class);
        Mockito.when(client.retrieve(anyString(), eq("full_text_search"), anyInt(), any()))
                .thenReturn(DifyDatasetClient.RetrieveResult.builder().query("q").records(List.of()).build());

        DifyKnowledgeService service = new DifyKnowledgeService(client, properties);
        DifyRetrievalRequest request = new DifyRetrievalRequest();
        request.setQuery("q");
        request.setSearchMethod("full_text_search");
        request.setTopK(4);
        request.setScoreThreshold(0.5);

        DifyRetrievalResultVO result = service.retrieve(request);

        Assertions.assertEquals("full_text_search", result.getSearchMethod());
        Assertions.assertTrue(result.getRecords().isEmpty());
    }
}
