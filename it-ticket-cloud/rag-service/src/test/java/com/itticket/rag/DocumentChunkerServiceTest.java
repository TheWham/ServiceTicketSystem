package com.itticket.rag;

import com.itticket.rag.dto.ChunkConfigDTO;
import com.itticket.rag.service.DocumentChunkerService;
import com.itticket.rag.vo.KnowledgeChunkVO;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.util.List;

/**
 * 文档切片服务测试：Markdown 标题层级分块、章节标题继承、切片度量字段完整性。
 *
 * <p>规范关联：切片是 MR-004（specs/10-model-rag-integration.md:70）检索链路的输入，
 * 切片质量直接决定召回；本组件不感知知识状态机（SM-KNOWLEDGE-001），
 * 草稿/发布分支由 RagPipelineService 编排。</p>
 * 文档切片器（DocumentChunkerService）冒烟回归。
 * 知识库入库时，一篇 Markdown 正文会被切成多个带重叠窗口的切片（chunk），
 * 每个切片生成稳定的 chunk_id、标题与字符数统计，供后续向量化与 ES 索引使用。
 * 本测试用真实的 VPN 排查指南文本验证：
 *  - 按 chunkSize=150 / chunkOverlap=20 配置能切出非空切片列表；
 *  - 每个切片字段完整（chunk_id 不为空、char_count > 0、标题保留）；
 *  - 标题行（# / ##）参与了切片标题提取（从控制台输出人工核对切片边界）。
 */
public class DocumentChunkerServiceTest {

    private final DocumentChunkerService chunkerService = new DocumentChunkerService();

    /**
     * Markdown 切片主流程：
     * 用两级标题的真实文档，验证产出切片数量、字段完整性与标题推导。
     * 输出每片边界到 stdout，便于调参（chunkSize / overlap）时人工核对。
     */
    @Test
    public void testMarkdownChunking() {
        // 覆盖：一级标题综述 + 两个二级小节 + 有序/无序列表混排（知识库最常见排版）
        String markdown = """
                # 常见网络与VPN问题排查指南

                本指南用于指导企业员工在遇到网络连接中断或企业内部 VPN 连接失败时进行基础自助排查。

                ## 一、检查物理网线与Wi-Fi连接
                1. 请确认右下角任务栏网络图标是否显示已连接。
                2. 若使用无线网络，请确保已连接到企业内网 SSID 并完成认证。

                ## 二、VPN客户端登录错误处理
                当客户端提示证书过期或认证失败时：
                - 请先尝试退出客户端并重新输入域账号密码登录。
                - 若仍失败，请联系 IT 服务台重置 VPN 证书。
                """;

        ChunkConfigDTO config = new ChunkConfigDTO();
        config.setChunkSize(150);
        config.setChunkOverlap(20);

        List<KnowledgeChunkVO> chunks = chunkerService.chunkDocument(markdown, "网络故障排查", config);

        Assertions.assertNotNull(chunks);
        Assertions.assertFalse(chunks.isEmpty(), "至少切出一片");
        for (KnowledgeChunkVO chunk : chunks) {
            Assertions.assertNotNull(chunk.getChunkId(), "每个切片必须有稳定 chunk_id");
            Assertions.assertTrue(chunk.getCharCount() > 0, "每个切片必须统计正文字符数");
            Assertions.assertNotNull(chunk.getTitle(), "每个切片必须保留/推导出标题");
            System.out.println("Chunk #" + chunk.getChunkIndex() + " [" + chunk.getTitle() + "]: " + chunk.getCharCount() + " chars");
        }
    }
}