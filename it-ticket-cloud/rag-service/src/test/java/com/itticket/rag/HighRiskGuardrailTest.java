package com.itticket.rag;

import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.service.HighRiskGuardrail;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

/**
 * 高风险主题拦截器测试（AI-001：账号权限/安全事件/数据丢失/高风险命令/硬件拆修必须拒答）。
 */
public class HighRiskGuardrailTest {

    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final HighRiskGuardrail guardrail = new HighRiskGuardrail(properties);

    @Test
    public void blocksAccountPermissionQuestion() {
        HighRiskGuardrail.HighRiskVerdict verdict = guardrail.inspect("我想申请管理员账号权限");

        Assertions.assertTrue(verdict.blocked());
        Assertions.assertNotNull(verdict.matchedKeyword());
    }

    @Test
    public void blocksPasswordResetQuestion() {
        HighRiskGuardrail.HighRiskVerdict verdict = guardrail.inspect("怎么重置我的域账号密码");

        Assertions.assertTrue(verdict.blocked());
    }

    @Test
    public void blocksHighRiskCommandCaseInsensitively() {
        HighRiskGuardrail.HighRiskVerdict verdict = guardrail.inspect("执行 DROP TABLE users 会有什么后果");

        Assertions.assertTrue(verdict.blocked());
        Assertions.assertEquals("drop table", verdict.matchedKeyword());
    }

    @Test
    public void blocksDataLossAndSecurityTopics() {
        Assertions.assertTrue(guardrail.inspect("服务器数据丢失怎么恢复").blocked());
        Assertions.assertTrue(guardrail.inspect("发现系统有安全漏洞").blocked());
        Assertions.assertTrue(guardrail.inspect("打印机怎么拆硬盘").blocked());
    }

    @Test
    public void allowsOrdinaryItQuestion() {
        HighRiskGuardrail.HighRiskVerdict verdict = guardrail.inspect("VPN 连接失败，提示证书过期怎么办");

        Assertions.assertFalse(verdict.blocked());
        Assertions.assertNull(verdict.matchedKeyword());
    }

    @Test
    public void blocksInterruptedHighRiskPhrasingViaPatterns() {
        // 关键词被限定语打断时，靠正则兜底（词表只能命中连续字符串）
        Assertions.assertTrue(guardrail.inspect("我要重置管理员密码").blocked());
        Assertions.assertTrue(guardrail.inspect("帮我把域账号权限提升一下").blocked());
        Assertions.assertTrue(guardrail.inspect("怎么把生产库的数据清空重建").blocked());
    }

    @Test
    public void blankMessagePassesThrough() {
        Assertions.assertFalse(guardrail.inspect(null).blocked());
        Assertions.assertFalse(guardrail.inspect("   ").blocked());
    }
}
