package com.itticket.rag.service;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * 文档预处理端口：隔离 doc-ingest-service（Python 清洗管线）的装配与调用细节。
 *
 * <p>rag-service 上传链路通过本端口委托 DOCX 的 L1 规则清洗（保序解析、
 * 条目切分、字段摊平、PII 脱敏），取回结构化的 Markdown 条目。</p>
 *
 * <p>实现由装配阶段按 rag.preprocess.base-url 是否配置来决定（见
 * {@link DocPreprocessClient}）；运行时业务代码不做供应商分支判断。</p>
 */
public interface DocPreprocessPort {

    /**
     * 对上传的 DOCX 文件执行 L1 规则物理清洗。
     *
     * @param filename    原始文件名（用于服务端日志与 metadata）
     * @param fileBytes   文件全部字节
     * @return 清洗后的条目列表（顺序保持文档物理阅读顺序）
     * @throws com.itticket.common.api.BizException 依赖不可达、协议异常或文档非法时显式抛出，
     *         不做静默降级（调用方据此终止入库，落库与索引写入不会发生）
     */
    List<CleanedEntry> cleanDocx(String filename, byte[] fileBytes);

    /** 清洗后的单条知识条目（来自 doc-ingest-service /v1/preprocess/docx-clean）。 */
    @Data
    @Builder
    class CleanedEntry {
        /** 条目代码，如 NET-001；附录为 APPENDIX-N */
        private String code;
        /** 条目标题 */
        private String title;
        /** 所属分类（文档 H1 章节） */
        private String category;
        /** 检索关键词 */
        private List<String> keywords;
        /** 渲染后的纯净 Markdown（含 # 标题、字段列表与备注） */
        private String markdown;
    }
}
