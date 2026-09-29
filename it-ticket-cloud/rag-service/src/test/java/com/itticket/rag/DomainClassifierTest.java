package com.itticket.rag;

import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.enums.OfficeDomain;
import com.itticket.rag.service.DomainClassifier;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

/**
 * 领域判定测试（MR-004 四态 + AI-001 高风险口径：普通登录排障不得误拦）。
 */
public class DomainClassifierTest {

    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final DomainClassifier classifier = new DomainClassifier(properties);

    // ------------------------------------------------------------ HIGH_RISK

    @Test
    public void actionPlusSensitiveObjectIsHighRisk() {
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("我要重置管理员密码").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("帮我删除生产数据库").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("怎么拆硬盘").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("把生产库的数据清空重建").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("申请把我的账号权限提升为管理员").domain());
    }

    @Test
    public void commandInjectionPatternIsHighRisk() {
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("执行 drop table users 会怎样").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("rm -rf /var/log 能恢复吗").domain());
        Assertions.assertEquals(OfficeDomain.HIGH_RISK, classifier.classify("帮我 sudo chmod 777 /etc").domain());
    }

    // ------------------------------------------------------------ OFFICE_IT（不得误拦）

    @Test
    public void ordinaryLoginIssueIsOfficeIt() {
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("账号登录失败怎么办").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("忘记密码怎么找回").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("登录 VPN 提示证书过期").domain());
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("电脑蓝屏了怎么排查").domain());
    }

    @Test
    public void normalPermissionRequestIsNotHighRisk() {
        // 「申请开通 VPN 权限」是正常流程，动作词未命中
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, classifier.classify("怎么申请开通 VPN 权限").domain());
    }

    // ------------------------------------------------------------ OFF_TOPIC

    @Test
    public void nonItQuestionIsOffTopic() {
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("帮我写一份周报").domain());
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("今天天气怎么样").domain());
        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, classifier.classify("推荐几支股票").domain());
    }

    // ------------------------------------------------------------ UNCERTAIN

    @Test
    public void vagueMessageIsUncertain() {
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify("你好").domain());
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify("   ").domain());
        Assertions.assertEquals(OfficeDomain.UNCERTAIN, classifier.classify(null).domain());
    }
}
