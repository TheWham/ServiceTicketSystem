package com.itticket.rag.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * ============================================================================
 * RAG 阶段一：文档解析与结构化提取服务 (DocumentParserService)
 * ============================================================================
 * 
 * 【业务背景与职责】：
 * 1. 负责知识库管理员上传文档的格式校验与字符流读取。
 * 2. 统一编码为 UTF-8，清洗无效控制字符，提取文档结构化元数据（标题、字符数、行数、文件大小等）。
 * 3. 智能解析 Markdown 一级标题（# Title），若文档未显式指定标题则自动提取，避免人工重复输入。
 * 
 * 【支持格式】：
 * - Markdown 格式（.md、.markdown）
 * - 纯文本格式（.txt）
 * 
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
public class DocumentParserService {

    /**
     * 文档解析结果载体对象（包含文本正文及元数据度量指标）
     */
    @Data
    @Builder
    public static class ParsedDocument {
        /** 原始上传文件名，例如 "VPN故障排查指南.md" */
        private String originalFileName;

        /** 文件后缀名，例如 "md"、"txt" */
        private String fileExtension;

        /** 原始文件物理大小（字节数） */
        private long fileSizeBytes;

        /** 提取或指定的文档主标题 */
        private String extractedTitle;

        /** 解析清洗后的完整正文字符串 */
        private String fullContent;

        /** 文档总有效行数 */
        private int lineCount;

        /** 文档总字符数 */
        private int characterCount;

        /** 识别到的主要章节列表（预留扩展） */
        private List<String> sections;
    }

    /**
     * 执行文档解析主流程
     *
     * @param file        前端上传的 MultipartFile 文件流
     * @param customTitle 管理员在界面手动填写的自定义标题（可选）
     * @return ParsedDocument 解析后的结构化实体
     * @throws BizException 当文件为空或格式不受支持时抛出业务异常
     */
    public ParsedDocument parse(MultipartFile file, String customTitle) {
        // 1. 基础参数非空校验
        if (file == null || file.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "上传文件不能为空");
        }

        String originalName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document.txt";
        String ext = getFileExtension(originalName).toLowerCase();

        // 2. 文件格式白名单校验（首期严格支持 Markdown 与 TXT）
        if (!ext.equals("md") && !ext.equals("txt") && !ext.equals("markdown")) {
            throw new BizException(ErrorCode.PARAM_INVALID, "目前仅支持 Markdown (.md) 和 纯文本 (.txt) 格式文档");
        }

        StringBuilder contentBuilder = new StringBuilder();
        List<String> lines = new ArrayList<>();
        String extractedTitle = null;

        // 3. 自动识别编码（优先 UTF-8，兼容带 BOM 及 Windows GBK 编码）并逐行读取
        byte[] fileBytes;
        try {
            fileBytes = file.getBytes();
        } catch (Exception e) {
            log.error("Failed to read file bytes: {}", originalName, e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "读取上传文件失败: " + e.getMessage());
        }

        String rawContent = decodeTextBytes(fileBytes);
        // 清洗 UTF-8 BOM 字符（\uFEFF）
        if (rawContent.startsWith("\uFEFF")) {
            rawContent = rawContent.substring(1);
        }

        String[] rawLines = rawContent.split("\\r?\\n");
        for (String line : rawLines) {
            // 清洗行内 BOM
            String cleanLine = line.replace("\uFEFF", "");
            lines.add(cleanLine);
            contentBuilder.append(cleanLine).append("\n");

            // 规则：若未设置标题，自动提取首个 Markdown 一级标题（如 "# 常见网络与VPN问题排查"）
            if (extractedTitle == null && cleanLine.trim().startsWith("# ")) {
                extractedTitle = cleanLine.trim().substring(2).trim();
            }
        }

        String fullText = contentBuilder.toString().trim();
        if (fullText.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "文档内容为空，无法进行切片入库");
        }

        // 4. 确定最终主标题优先级：手动指定 > Markdown H1 提取 > 文件名默认
        if (customTitle != null && !customTitle.isBlank()) {
            extractedTitle = customTitle.trim();
        } else if (extractedTitle == null || extractedTitle.isBlank()) {
            int dotIndex = originalName.lastIndexOf('.');
            extractedTitle = dotIndex > 0 ? originalName.substring(0, dotIndex) : originalName;
        }

        log.info("Document parsed successfully: [{}] (Length: {} chars, Lines: {})",
                extractedTitle, fullText.length(), lines.size());

        // 5. 组装返回结构化解析对象
        return ParsedDocument.builder()
                .originalFileName(originalName)
                .fileExtension(ext)
                .fileSizeBytes(file.getSize())
                .extractedTitle(extractedTitle)
                .fullContent(fullText)
                .lineCount(lines.size())
                .characterCount(fullText.length())
                .build();
    }

    /**
     * 安全提取文件名后缀
     */
    private String getFileExtension(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1) : "";
    }

    /**
     * 智能解码字节流（优先 UTF-8，发生乱码或异常时回退到 GB18030/GBK）
     */
    private String decodeTextBytes(byte[] bytes) {
        if (bytes == null || bytes.length == 0) return "";
        try {
            java.nio.charset.CharsetDecoder utf8Decoder = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                    .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT);
            return utf8Decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString();
        } catch (Exception utf8Ex) {
            log.warn("UTF-8 strict decoding failed, attempting GB18030 / GBK fallback decoding");
            try {
                return new String(bytes, java.nio.charset.Charset.forName("GB18030"));
            } catch (Exception gbkEx) {
                return new String(bytes, StandardCharsets.UTF_8);
            }
        }
    }
}
