package com.itticket.rag.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;

/**
 * ============================================================================
 * RAG 检索策略配置 (RagRetrievalProperties)
 * ============================================================================
 *
 * <p>本模块只负责检索与知识策略判定，不承担大模型生成；大模型问答由 AI 客服服务对接本模块的
 * 检索接口后自行实现。因此这里只保留检索与策略相关参数，不包含任何模型调用配置。</p>
 *
 * <p>阈值可按评测结果调整（PRD §17.3 上线门槛）：相似度 ≥ confidenceThreshold 视为可靠命中；
 * 介于 lowConfidenceThreshold 与 confidenceThreshold 之间判定 LOW_CONFIDENCE；
 * 低于下限或无命中判定 NO_RELIABLE_KNOWLEDGE（AI-001）。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.retrieval")
public class RagRetrievalProperties {

    /** 默认返回的 Top-K 切片数 */
    private Integer topK = 5;

    /** 单次检索允许的最大 Top-K，防止调用方拉取过量数据 */
    private Integer maxTopK = 20;

    /** 可靠命中阈值：相似度 ≥ 该值才允许据此生成回答 */
    private BigDecimal confidenceThreshold = new BigDecimal("0.65");

    /** 无可靠知识下限：相似度 < 该值判定为无可靠命中 */
    private BigDecimal lowConfidenceThreshold = new BigDecimal("0.45");

    /** 引用片段长度上限（契约 AI-004.3 citation.snippet.maxLength=1000） */
    private Integer snippetLength = 1000;

    /** 高风险主题词表（命中即建议拒答 HIGH_RISK_TOPIC，AI-001） */
    private List<String> highRiskKeywords = List.of(
            "账号权限", "权限申请", "权限提升", "提权",
            "密码重置", "重置密码", "修改密码", "忘记密码",
            "删库", "删除数据库", "清空数据", "数据丢失", "数据恢复", "格式化",
            "安全漏洞", "漏洞", "入侵", "勒索", "病毒", "木马", "越权",
            "拆机", "拆卸", "拆硬盘", "刷机", "开盖",
            "rm -rf", "drop table", "truncate", "sudo", "shutdown", "reboot",
            "域账号", "账号密码"
    );

    /**
     * 高风险主题正则规则（忽略大小写）。
     *
     * <p>词表只能命中连续字符串，而自然表述常在关键词中间插入限定语（如「重置<b>我的域账号</b>密码」），
     * 因此用正则兜住这类被打断的高风险意图，避免高风险问题漏进检索与下游生成。</p>
     */
    private List<String> highRiskPatterns = List.of(
            // 账号与凭据
            "(重置|修改|找回|忘记|变更|破解|初始化).{0,10}密码",
            "密码.{0,8}(重置|找回|修改|破解|初始化)",
            "管理员.{0,8}(密码|权限|账号)",
            "(申请|开通|提升|变更|授予|扩大|升级).{0,8}(权限|账号|配额)",
            "(权限|账号|配额).{0,8}(申请|开通|提升|变更|授予|扩大|升级)",
            // 数据安全与破坏性操作（两种语序都要覆盖）
            "(删除|清空|格式化|重建|drop|truncate).{0,12}(数据库|数据表|库表|数据|磁盘|分区|schema|table)",
            "(数据库|数据表|库表|数据|磁盘|分区|schema|table).{0,8}(清空|删除|格式化|重建)",
            "(数据|文件|硬盘|磁盘).{0,8}(丢失|损坏|恢复|还原)",
            // 安全事件与硬件拆修
            "(漏洞|入侵|勒索|木马|后门|提权|越权)",
            "(拆机|拆卸|拆下|打开机箱|开盖|拆硬盘)"
    );
}
