package com.itticket.rag;

import com.itticket.rag.dto.ChunkConfigDTO;
import com.itticket.rag.service.DocumentChunkerService;
import com.itticket.rag.vo.KnowledgeChunkVO;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.util.List;

public class DocumentChunkerServiceTest {

    private final DocumentChunkerService chunkerService = new DocumentChunkerService();

    @Test
    public void testMarkdownChunking() {
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
        Assertions.assertFalse(chunks.isEmpty());
        for (KnowledgeChunkVO chunk : chunks) {
            Assertions.assertNotNull(chunk.getChunkId());
            Assertions.assertTrue(chunk.getCharCount() > 0);
            Assertions.assertNotNull(chunk.getTitle());
            System.out.println("Chunk #" + chunk.getChunkIndex() + " [" + chunk.getTitle() + "]: " + chunk.getCharCount() + " chars");
        }
    }
}
