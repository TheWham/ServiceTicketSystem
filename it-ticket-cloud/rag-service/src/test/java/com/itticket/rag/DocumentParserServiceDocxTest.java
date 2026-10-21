package com.itticket.rag;

import com.itticket.common.api.BizException;
import com.itticket.rag.service.DocPreprocessPort;
import com.itticket.rag.service.DocumentParserService;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 文档解析服务 DOCX 委托测试：
 * 验证装配时供应商选择（rag.preprocess.base-url）驱动下的解析行为——
 * 未装配清洗端口时 DOCX 上传显式拒绝（不静默回退）；装配后 DOCX 经
 * doc-ingest-service 清洗的条目 Markdown 被正确合并为解析结果。
 */
public class DocumentParserServiceDocxTest {

    /** 最小 ObjectProvider 桩：只承载"有无实现"这一个装配事实。 */
    private static ObjectProvider<DocPreprocessPort> provider(DocPreprocessPort port) {
        return new ObjectProvider<>() {
            @Override
            public DocPreprocessPort getObject(Object... args) {
                return require(port);
            }

            @Override
            public DocPreprocessPort getObject() {
                return require(port);
            }

            @Override
            public DocPreprocessPort getIfAvailable() {
                return port;
            }

            @Override
            public DocPreprocessPort getIfUnique() {
                return port;
            }

            private DocPreprocessPort require(DocPreprocessPort p) {
                if (p == null) throw new IllegalStateException("no bean");
                return p;
            }
        };
    }

    private static MockMultipartFile file(String name, String content) {
        return new MockMultipartFile("file", name, "application/octet-stream",
                content.getBytes(StandardCharsets.UTF_8));
    }

    @Test
    public void docxRejectedWhenPreprocessNotAssembled() {
        DocumentParserService parser = new DocumentParserService(provider(null));
        BizException ex = Assertions.assertThrows(BizException.class,
                () -> parser.parse(file("常见问题库.docx", "bin"), null));
        Assertions.assertTrue(ex.getMessage().contains("doc-ingest-service"));
    }

    @Test
    public void legacyDocRejectedExplicitly() {
        DocumentParserService parser = new DocumentParserService(provider(null));
        Assertions.assertThrows(BizException.class,
                () -> parser.parse(file("旧文档.doc", "bin"), null));
    }

    @Test
    public void docxCombinedFromPreprocessEntries() {
        DocPreprocessPort fakePort = (filename, fileBytes) -> List.of(
                DocPreprocessPort.CleanedEntry.builder()
                        .code("NET-001").title("电脑无法连接公司WiFi")
                        .markdown("# 【NET-001】电脑无法连接公司WiFi\n\n## 现象描述\n- 搜不到SSID").build(),
                DocPreprocessPort.CleanedEntry.builder()
                        .code("VPN-001").title("VPN连接失败")
                        .markdown("# 【VPN-001】VPN连接失败\n\n## 现象描述\n- 提示错误809").build());
        DocumentParserService parser = new DocumentParserService(provider(fakePort));

        DocumentParserService.ParsedDocument doc = parser.parse(file("知识库.docx", "bin"), "IT常见问题手册");
        Assertions.assertEquals("docx", doc.getFileExtension());
        Assertions.assertEquals("IT常见问题手册", doc.getExtractedTitle());
        Assertions.assertTrue(doc.getFullContent().contains("# 【NET-001】电脑无法连接公司WiFi"));
        Assertions.assertTrue(doc.getFullContent().contains("# 【VPN-001】VPN连接失败"));
        Assertions.assertTrue(doc.getLineCount() > 0);
        Assertions.assertEquals(doc.getCharacterCount(), doc.getFullContent().length());
    }

    @Test
    public void docxTitleFallsBackToFileStem() {
        DocPreprocessPort fakePort = (filename, fileBytes) -> List.of(
                DocPreprocessPort.CleanedEntry.builder()
                        .code("NET-001").title("条目A").markdown("# 【NET-001】条目A").build());
        DocumentParserService parser = new DocumentParserService(provider(fakePort));
        DocumentParserService.ParsedDocument doc = parser.parse(file("运维经验沉淀.docx", "bin"), null);
        Assertions.assertEquals("运维经验沉淀", doc.getExtractedTitle());
    }

    @Test
    public void markdownStillParsesLocallyWithoutPreprocess() {
        DocumentParserService parser = new DocumentParserService(provider(null));
        DocumentParserService.ParsedDocument doc = parser.parse(
                file("指南.md", "# VPN 排障指南\n\n第一步：检查证书。\n"), null);
        Assertions.assertEquals("VPN 排障指南", doc.getExtractedTitle());
        Assertions.assertEquals("md", doc.getFileExtension());
    }
}
