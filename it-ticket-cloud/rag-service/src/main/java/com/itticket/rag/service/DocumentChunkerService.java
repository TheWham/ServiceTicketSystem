package com.itticket.rag.service;

import com.itticket.rag.dto.ChunkConfigDTO;
import com.itticket.rag.vo.KnowledgeChunkVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * ============================================================================
 * RAG 阶段二：文档智能切片服务 (DocumentChunkerService)
 * ============================================================================
 *
 * 【算法设计与切片原则】：
 * 1. 语义边界保持（Semantic Boundary Preservation）：
 *    - 优先以 Markdown 标题（# / ## / ###）与双换行段落作为天然边界进行分块。
 *    - 切片过程中自动继承当前的章节标题，确保每个独立切片均具备上下文语义指向。
 *
 * 2. 滑动窗口与重叠机制（Sliding Window with Overlap）：
 *    - 默认切片目标字符数为 500 字符（chunkSize）。
 *    - 设置 50 字符的重叠窗口（chunkOverlap），防止跨切片的上下文信息被硬性切断。
 *
 * 3. 碎片合并与异常防范：
 *    - 末尾不足最小阈值（minChunkSize，默认 30 字符）的内容自动向前合并，避免无意义的碎片切片。
 *    - 超长段落（超过 chunkSize）采用固定步长滚动窗口切分。
 *
 * 4. Token 估算：
 *    - 针对中英混合技术文档，按 ~1.3 字符/Token 算法精确估算 Token 消耗。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
public class DocumentChunkerService {

    /**
     * 对解析后的文档内容执行智能语义切片
     *
     * @param fullContent   文档纯文本正文
     * @param documentTitle 文档主标题（作为切片首选顶层章节）
     * @param config        切片配置参数（包含 chunkSize、chunkOverlap、minChunkSize）
     * @return List<KnowledgeChunkVO> 有序语义切片列表
     */
    public List<KnowledgeChunkVO> chunkDocument(String fullContent, String documentTitle, ChunkConfigDTO config) {
        if (config == null) {
            config = new ChunkConfigDTO();
        }
        // 边界安全校验：切片大小至少 100 字符，重叠大小最多不超过切片一半
        int targetSize = Math.max(100, config.getChunkSize());
        int overlap = Math.min(targetSize / 2, Math.max(0, config.getChunkOverlap()));
        int minSize = Math.max(10, config.getMinChunkSize());

        List<KnowledgeChunkVO> chunkList = new ArrayList<>();
        String[] rawLines = fullContent.split("\n");

        String currentHeading = documentTitle != null ? documentTitle : "正文";
        StringBuilder currentBuffer = new StringBuilder();
        int chunkIndex = 0;

        for (String line : rawLines) {
            String trimmedLine = line.trim();

            // 规则 1：识别 Markdown 标题层级
            if (trimmedLine.startsWith("#")) {
                // 若已有累积内容，先封闭当前切片，并保留 overlap 重叠字符
                if (currentBuffer.length() >= minSize) {
                    chunkIndex++;
                    chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
                    currentBuffer = getOverlapBuffer(currentBuffer, overlap);
                }
                // 更新当前切片所处的章节标题
                currentHeading = cleanHeading(trimmedLine);
                continue;
            }

            // 规则 2：空行（段落边界）
            if (trimmedLine.isEmpty()) {
                if (currentBuffer.length() >= targetSize) {
                    chunkIndex++;
                    chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
                    currentBuffer = getOverlapBuffer(currentBuffer, overlap);
                }
                continue;
            }

            // 规则 3：处理单行超长文本（如单段长代码或无换行长文本）
            if (trimmedLine.length() > targetSize) {
                if (currentBuffer.length() >= minSize) {
                    chunkIndex++;
                    chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
                    currentBuffer = new StringBuilder();
                }

                List<String> subSegments = splitLongText(trimmedLine, targetSize, overlap);
                for (String seg : subSegments) {
                    chunkIndex++;
                    chunkList.add(createChunk(chunkIndex, currentHeading, seg.trim()));
                }
                continue;
            }

            // 规则 4：字符累积达到目标切片大小
            if (currentBuffer.length() + trimmedLine.length() + 1 > targetSize && currentBuffer.length() >= minSize) {
                chunkIndex++;
                chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
                currentBuffer = getOverlapBuffer(currentBuffer, overlap);
            }

            if (currentBuffer.length() > 0) {
                currentBuffer.append("\n");
            }
            currentBuffer.append(trimmedLine);
        }

        // 规则 5：处理文档末尾剩余的文本缓冲区
        if (currentBuffer.length() >= minSize) {
            chunkIndex++;
            chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
        } else if (currentBuffer.length() > 0 && !chunkList.isEmpty()) {
            // 末尾残余碎片向前合并至上一块切片
            KnowledgeChunkVO last = chunkList.get(chunkList.size() - 1);
            String merged = last.getContent() + "\n" + currentBuffer.toString().trim();
            last.setContent(merged);
            last.setCharCount(merged.length());
            last.setTokenCountEstimate(estimateTokens(merged));
        } else if (currentBuffer.length() > 0) {
            // 文档过短仅有一段且小于 minSize
            chunkIndex++;
            chunkList.add(createChunk(chunkIndex, currentHeading, currentBuffer.toString().trim()));
        }

        log.info("Document chunking completed: generated {} chunks with avg length ~{} chars",
                chunkList.size(), chunkList.isEmpty() ? 0 : fullContent.length() / chunkList.size());

        return chunkList;
    }

    /**
     * 构建单个切片值对象
     */
    private KnowledgeChunkVO createChunk(int index, String heading, String content) {
        int charCount = content.length();
        int tokenEstimate = estimateTokens(content);
        return KnowledgeChunkVO.builder()
                .chunkIndex(index)
                .chunkId("chk-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16))
                .title(heading)
                .content(content)
                .charCount(charCount)
                .tokenCountEstimate(tokenEstimate)
                .status("CHUNKED")
                .build();
    }

    /**
     * 提取切片尾部指定长度作为下一切片的重叠前缀
     */
    private StringBuilder getOverlapBuffer(StringBuilder buffer, int overlap) {
        if (overlap <= 0 || buffer.length() <= overlap) {
            return new StringBuilder();
        }
        String tail = buffer.substring(buffer.length() - overlap);
        return new StringBuilder(tail);
    }

    /**
     * 对超长单行长文本进行滑动窗口拆分
     */
    private List<String> splitLongText(String text, int targetSize, int overlap) {
        List<String> list = new ArrayList<>();
        int step = Math.max(50, targetSize - overlap);
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(text.length(), start + targetSize);
            list.add(text.substring(start, end));
            if (end == text.length()) {
                break;
            }
            start += step;
        }
        return list;
    }

    /**
     * 清洗 Markdown 标题标记（如去除 "## "）
     */
    private String cleanHeading(String headingLine) {
        return headingLine.replaceAll("^#+\\s*", "").trim();
    }

    /**
     * 估算切片的 Token 数量（中文约 1.2 字符/Token，代码与英文约 4 字符/Token，综合加权 ~1.3）
     */
    private int estimateTokens(String text) {
        if (text == null || text.isEmpty()) return 0;
        return (int) Math.ceil(text.length() / 1.3);
    }
}
