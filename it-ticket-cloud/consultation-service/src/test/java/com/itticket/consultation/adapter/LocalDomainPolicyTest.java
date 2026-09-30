package com.itticket.consultation.adapter;
import com.itticket.consultation.adapter.policy.*;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class LocalDomainPolicyTest {
    private final LocalOfficeDomainClassifier classifier = new LocalOfficeDomainClassifier();
    @Test void destructiveActionWithSensitiveObjectIsHighRisk() {
        assertThat(classify("电脑格式化硬盘怎么做")).isEqualTo(OfficeDomain.HIGH_RISK);
        assertThat(classify("删除数据库怎么操作")).isEqualTo(OfficeDomain.HIGH_RISK);
    }
    @Test void technicalWordAloneDoesNotLicenseGeneralGeneration() {
        assertThat(classify("电脑")).isEqualTo(OfficeDomain.UNCERTAIN);
        assertThat(classify("用电脑写情书")).isEqualTo(OfficeDomain.OFF_TOPIC);
    }
    @Test void normalPasswordTroubleshootingIsOfficeIt() {
        assertThat(classify("密码没改过却登录不上了")).isEqualTo(OfficeDomain.OFFICE_IT);
    }
    @Test void clearTechnicalSymptomsHaveExplicitLocalRules() {
        assertThat(classify("开会别人听不到我")).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(classify("打印机连不上")).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(classify("又不行了")).isEqualTo(OfficeDomain.UNCERTAIN);
    }
    private OfficeDomain classify(String question) {
        return classifier.classify(new RagQuery("S", question, null, null, 5, new RagCaller("U", "EMPLOYEE")),
                new RagCallContext("req", System.nanoTime() + 1_000_000_000, new RagExecutionAudit()));
    }
}
