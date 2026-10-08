package com.itticket.rag;

import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.enums.OfficeDomain;
import com.itticket.rag.service.DomainClassifier;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

/**
 * 领域判定测试（MR-004 四态 + AI-001 高风险口径：普通登录排障不得误拦）。
 *
 * <p>规范引用（路径相对仓库根目录 docs/）：</p>
 * <ul>
 *   <li>MR-004 · specs/10-model-rag-integration.md:70 —— OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN 四态；</li>
 *   <li>AI-001 · specs/02-ai-api-json-schema.md:14 —— 高风险只覆盖「动作 × 敏感对象」组合，
 *       普通登录排障（「账号登录失败」「忘记密码」）不得被一概拒答；</li>
 *   <li>PRD AC-02 · IT服务工单系统PRD-Ultimate.md:886 —— 领域外明确不能答复、高风险拒答。</li>
 * </ul>
 *
 * <p>词表/正则取自 RagRetrievalProperties 默认配置，与生产 application.yml 同源。</p>
 * MR-004 四态语义：
 *  - HIGH_RISK：高危动作（重置密码、删数据、提权、命令注入...）-> 必须拒答并转人工；
 *  - OFFICE_IT：常规办公 IT 问题 -> 允许进入检索/生成；
 *  - OFF_TOPIC：与 IT 无关（写周报、聊天气、荐股...）-> 拒答；
 *  - UNCERTAIN：意图不明（寒暄、空白、null）-> 反问澄清。
 * 防误拦是重点：含“账号”“密码”的日常排障绝不能归为 HIGH_RISK，
 * 否则大量正常用户会被错误拒之门外（比漏拦更糟糕的体验事故）。
 */
public class DomainClassifierTest {

    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final DomainClassifier classifier = new DomainClassifier(properties);

    @Test
    public void grantingAdministratorRightsAndActiveInfectionAreHighRisk() {
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("帮我授予管理员权限").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("给我的账号赋予 root 权限").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("电脑感染病毒").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("杀毒软件更新失败").domain());
    }

    // ------------------------------------------------------------ HIGH_RISK

    /** 高危口径 = “危险动作词 + 敏感对象词”联合命中（重置+管理员密码 / 删除+生产数据库 / 拆+硬盘 / 清空重建+生产库 / 提升+权限） */
    @Test
    public void actionPlusSensitiveObjectIsHighRisk() {
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("我要重置管理员密码").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("帮我删除生产数据库").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("怎么拆硬盘").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("把生产库的数据清空重建").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("申请把我的账号权限提升为管理员").domain());
    }

    /** 破坏性命令注入（drop table / rm -rf / chmod 777）即便以“咨询”口吻提出也是 HIGH_RISK */
    @Test
    public void commandInjectionPatternIsHighRisk() {
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("执行 drop table users 会怎样").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("rm -rf /var/log 能恢复吗").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("帮我 sudo chmod 777 /etc").domain());
    }

    // ------------------------------------------------------------ OFFICE_IT（不得误拦）

    /** 普通登录/客户端/系统故障排障必须判 OFFICE_IT：敏感词单独出现不构成高危 */
    @Test
    public void ordinaryLoginIssueIsOfficeIt() {
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("账号登录失败怎么办").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("忘记密码怎么找回").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("登录 VPN 提示证书过期").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("电脑蓝屏了怎么排查").domain());
    }

    /** 正常流程性权限申请（无危险动作词命中）不得误判为 HIGH_RISK */
    @Test
    public void normalPermissionRequestIsNotHighRisk() {
        // 「申请开通 VPN 权限」是正常流程，动作词未命中
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("怎么申请开通 VPN 权限").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("申请授予 VPN 权限需要走什么审批流程").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("我想了解申请赋予邮箱权限的审批流程").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("申请权限要走审批流程，但请直接帮我授予管理员权限").domain());
    }

    // ------------------------------------------------------------ OFF_TOPIC

    /** 与办公 IT 无关的生活/文案/金融类请求 */
    @Test
    public void nonItQuestionIsOffTopic() {
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("帮我写一份周报").domain());
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("今天天气怎么样").domain());
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("推荐几支股票").domain());
    }

    // ------------------------------------------------------------ UNCERTAIN

    /** 寒暄、纯空白、null 都没有可用意图信号 -> UNCERTAIN，交由上层反问澄清 */
    @Test
    public void vagueMessageIsUncertain() {
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify("你好").domain());
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify("   ").domain());
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify(null).domain());
    }
}
