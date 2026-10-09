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
 * <p>本模块只负责检索与知识策略判定，不承担大模型生成（对话与生成由 AI 客服服务负责）。
 * 阈值、词表均可配置，便于评测调参。</p>
 *
 * <p>契约对齐（路径相对仓库根目录 docs/）：</p>
 * <ul>
 *   <li>MR-001 · specs/10-model-rag-integration.md:13（similarityThreshold 默认 0.70 见 :34；topK 默认 5）。</li>
 *   <li>MR-004 · specs/10-model-rag-integration.md:70：领域判定四态 OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN；
 *       单个 IT 关键词或检索命中不构成领域许可。</li>
 *   <li>AI-001 · specs/02-ai-api-json-schema.md:14：本地词表用于检索侧兼容判定，
 *       AI 最终领域/风险判定依据完整语义，合法自助操作不能仅因含「重置」「密码」等词被拒答；
 *       相似度只决定引用质量，无命中/弱命中不强制拒答；lowConfidenceThreshold 仅保留配置兼容。</li>
 * </ul>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.retrieval")
public class RagRetrievalProperties {

    /** 默认返回的 Top-K 切片数（MR-001 · specs/10-model-rag-integration.md:34 默认 5） */
    private Integer topK = 5;

    /** 单次检索允许的最大 Top-K，防止调用方拉取过量数据（上限 20 为本模块实现值） */
    private Integer maxTopK = 20;

    /** 引用质量阈值：相似度 ≥ 该值才视为可靠知识依据；不限制通用回答（MR-001，默认 0.70） */
    private BigDecimal confidenceThreshold = new BigDecimal("0.70");

    /** 旧下限配置，仅保留属性绑定兼容；不再参与可靠性或拒答判定（AI-001）。 */
    private BigDecimal lowConfidenceThreshold = new BigDecimal("0.45");

    /** 引用片段长度上限（契约 citation.snippet.maxLength=1000，AI-004.3 · specs/02-ai-api-json-schema.md:134） */
    private Integer snippetLength = 1000;

    // ---------------- 领域判定词表（MR-004，全部可配置） ----------------

    /**
     * 高风险动作词：必须命中其一才可能判 HIGH_RISK。
     * 「忘记/登录失败/无法登录」这类普通排障求助不在此列。
     */
    private List<String> highRiskActions = List.of(
            "重置", "修改密码", "修改管理员密码", "提权", "权限提升", "授予权限", "开通权限",
            "删除数据库", "清空数据", "清空表", "格式化", "拆机", "拆硬盘", "拆下", "刷机",
            "执行命令", "运行命令", "恢复数据", "恢复被删", "找回删除"
    );

    /** 高风险正则：命令注入与权限升级的复合表述（兜底，忽略大小写） */
    private List<String> highRiskPatterns = List.of(
            "rm\\s+-rf",
            "drop\\s+(table|database)",
            "truncate\\s+(table)?",
            "(sudo|su\\s+-)\\s",
            "administrator?\\s+password",
            "(重置|修改|破解|初始化).{0,10}(管理员|admin|root).{0,6}密码",
            "管理员.{0,6}密码.{0,6}(重置|破解)",
            "(权限|配额).{0,8}(提升|提权|扩大|授予|开通)",
            "(?:^|帮我|替我|给.{0,8}账号|直接|(?<!申)请|我要|我想)(授予|赋予).{0,12}(权限|管理员|admin|root)",
            "(感染|中了|发现|检测到).{0,8}(病毒|木马|勒索)",
            "(病毒|木马).{0,8}(感染|入侵)",
            "(删除|清空|格式化|重建).{0,10}(数据库|数据表|库表|磁盘|分区)",
            // 反向语序：「把生产库的数据清空重建」（对象在前、动作在后）
            "(数据库|数据表|库表|数据|磁盘|分区).{0,8}(清空|删除|格式化|重建)",
            // 数据恢复/找回：覆盖「数据丢失怎么恢复」「误删的文件找回」
            "(数据|文件|硬盘|磁盘).{0,8}(丢失|误删|损坏|恢复|还原)",
            "(恢复|找回|还原).{0,6}(数据|文件|备份)",
            "(拆机|拆下|拆开).{0,8}(硬盘|机箱|主机|内存)",
            "(漏洞|入侵|勒索|木马|后门|提权|越权)"
    );

    /** 领域外（非办公 IT）词表：命中即 OFF_TOPIC，直接拒答 */
    private List<String> offTopicKeywords = List.of(
            "周报", "日报", "月报", "周报模板", "工作总结", "翻译", "写邮件", "订餐",
            "外卖", "报销", "旅游", "机票", "酒店", "股票", "基金", "理财",
            "作业", "论文", "简历", "情感", "天气", "新闻", "食谱", "菜谱", "购物",
            "小说", "笑话", "写诗", "作文", "数学题"
    );

    /** 高风险敏感对象：与动作词同时命中才判 HIGH_RISK（防止「账号登录失败」被误拦） */
    private List<String> highRiskObjects = List.of(
            "密码", "口令", "权限", "账号", "管理员", "admin", "root",
            "数据库", "数据表", "库表", "磁盘", "硬盘", "数据"
    );

    /** 办公 IT 关键词（用于排除 UNCERTAIN）：命中其一即视为办公 IT 范围 */
    private List<String> officeItKeywords = List.of(
            "电脑", "打印机", "网络", "wifi", "vpn", "邮件", "邮箱", "打印机", "显示器",
            "系统", "软件", "安装", "升级", "登录", "登不上去", "密码", "账号", "报错",
            "蓝屏", "死机", "卡", "慢", "断网", "驱动", "客户端", "服务器", "数据库",
            "文件", "共享", "权限", "接入", "开机", "重启", "故障", "异常", "无法", "打不开",
            "连接", "无法连接", "超时", "提示", "证书", "编码", "弹窗", "闪退", "崩溃"
    );
}
