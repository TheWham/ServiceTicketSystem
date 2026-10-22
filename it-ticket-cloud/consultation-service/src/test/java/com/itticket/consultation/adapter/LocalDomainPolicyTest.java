package com.itticket.consultation.adapter;
import com.itticket.consultation.adapter.policy.*;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class LocalDomainPolicyTest {
    private final KeywordRequestClassifier classifier = new KeywordRequestClassifier();
    @Test void destructiveActionWithSensitiveObjectIsHighRisk() {
        assertThat(classify("电脑格式化硬盘怎么做").domain()).isEqualTo(OfficeDomain.HIGH_RISK);
        assertThat(classify("删除数据库怎么操作").domain()).isEqualTo(OfficeDomain.HIGH_RISK);
    }
    @Test void technicalWordAloneDoesNotLicenseGeneralGeneration() {
        assertThat(classify("电脑").domain()).isEqualTo(OfficeDomain.UNCERTAIN);
        assertThat(classify("用电脑写情书").domain()).isEqualTo(OfficeDomain.OFF_TOPIC);
    }
    @Test void normalPasswordTroubleshootingIsOfficeIt() {
        assertThat(classify("密码没改过却登录不上了").domain()).isEqualTo(OfficeDomain.OFFICE_IT);
    }
    @Test void clearTechnicalSymptomsHaveExplicitLocalRules() {
        assertThat(classify("开会别人听不到我").domain()).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(classify("打印机连不上").domain()).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(classify("又不行了").domain()).isEqualTo(OfficeDomain.UNCERTAIN);
    }
    @Test void toolIntentFallbackMapsActionVerbsFirst() {
        // 动作动词优先于对象：提交/报修/建单 → 建单草稿
        assertThat(classify("打印机坏了帮我提交报修").tool()).isEqualTo("prepare_ticket");
        assertThat(classify("帮我提个单").tool()).isEqualTo("prepare_ticket");
        // 「工单」默认取查询义
        assertThat(classify("我上周报的那个工单怎么样了").tool()).isEqualTo("query_my_tickets");
        assertThat(classify("会议室投影仪怎么连").tool()).isEqualTo(RequestVerdict.NO_TOOL);
    }
    private RequestVerdict classify(String question) {
        return classifier.classify(new RagQuery("S", question, null, null, 5, new RagCaller("U", "EMPLOYEE")),
                new RagCallContext("req", System.nanoTime() + 1_000_000_000, new RagExecutionAudit()));
    }
}
