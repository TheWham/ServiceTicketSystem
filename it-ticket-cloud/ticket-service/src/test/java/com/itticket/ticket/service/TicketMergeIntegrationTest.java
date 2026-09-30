package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.TicketProjection;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.*;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 建单链路的整体回归（TicketService.create，含事务提交后的副作用编排）：
 *  - 咨询转工单：分类快照/性质/优先级/幂等键/表单快照全部固化，提交后才触发派单/SLA/会话回执；
 *  - 幂等重试：同一 idempotency_key 重放只补发“咨询会话已转工单”回执，不重复建单/派单；
 *  - Header 与 Body 幂等键冲突必须 400，防止双通道语义不一致；
 *  - 附件查询只返“杀毒通过且未撤回”的文件；
 *  - 性质字段双契约（ticket_nature / nature 历史名）兼容 + 投影大写枚举值不被改写。
 *
 * 注意：本类用 TransactionSynchronizationManager 手工模拟“事务提交”，
 * 验证 afterCommit 回调（派单/通知/会话回执）只在提交成功后触发 —— 回滚时不许可见副作用。
 */
class TicketMergeIntegrationTest {
    private final TicketMapper tickets = mock(TicketMapper.class);
    private final CategoryMapper categories = mock(CategoryMapper.class);
    private final AttachmentMapper attachments = mock(AttachmentMapper.class);
    private final TicketFlowLogMapper flows = mock(TicketFlowLogMapper.class);
    private final TicketNoGenerator numbers = mock(TicketNoGenerator.class);
    private final NotificationService notifications = mock(NotificationService.class);
    private final ConsultationConvertNotifier conversions = mock(ConsultationConvertNotifier.class);
    private final SlaService sla = mock(SlaService.class);
    private final RoutingService routing = mock(RoutingService.class);
    private final UserContext.CurrentUser employee = new UserContext.CurrentUser("U_EMP01", "Employee", "EMPLOYEE", "IT");
    private final ObjectMapper json = new ObjectMapper();
    private TicketService service;

    @BeforeEach
    void setUp() {
        // LambdaUpdateWrapper 依赖 MyBatis-Plus 实体元数据，纯单测需手动初始化
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new com.baomidou.mybatisplus.core.MybatisConfiguration(), ""), Ticket.class);
        service = new TicketService(tickets, categories, attachments, flows, mock(com.itticket.ticket.mapper.TicketPurgeMapper.class), numbers,
                notifications, mock(UserClient.class), sla, routing, mock(ExceptionQueueService.class), conversions, json);
        // 分类桩：叶子分类 C_NET 存在且 ACTIVE；无同名冲突（selectCount=0）
        Category leaf = new Category();
        leaf.setCategoryId("C_NET");
        leaf.setName("Network");
        leaf.setStatus("ACTIVE");
        when(categories.selectById("C_NET")).thenReturn(leaf);
        when(categories.selectCount(any())).thenReturn(0L);
        when(numbers.generate()).thenReturn("TK001");
        TransactionSynchronizationManager.initSynchronization();
    }

    @AfterEach
    void cleanUp() {
        TransactionSynchronizationManager.clearSynchronization();
    }

    /** 一条由 AI 咨询会话转入的完整建单请求（带会话来源与字段值） */
    private CreateTicketRequest request() {
        CreateTicketRequest req = new CreateTicketRequest();
        req.setNature("INCIDENT");
        req.setCategoryId("C_NET");
        req.setTitle("Network unavailable");
        req.setDescription("The office network is unavailable.");
        req.setImpactDescription("Office network");
        req.setUrgencyDescription("Cannot work");
        req.setSourceSessionId("CS001");
        req.setFieldValues(Map.of("ai_summary", "Connection failed"));
        return req;
    }

    /**
     * 主流程全链路断言：
     *  1) 落库工单字段逐项固化（状态 NEW、默认 MEDIUM、INCIDENT 性质、会话来源、幂等键、
     *     分类名称快照、字段定义快照含 ai_summary、未接婚前无 first_response_at）；
     *  2) 提交前：派单/会话回执均未触发（尚在事务内）；
     *  3) 手工触发 afterCommit 后：会话回执 + 自动派单执行；
     *  4) 流转日志两条依次是 TICKET_CREATE、TICKET_ASSIGN。
     */
    @Test
    void consultationCreateRetainsMainRoutingAndSlaAndContext() throws Exception {
        var outcome = service.create(employee, request(), "key-1");
        var captor = ArgumentCaptor.forClass(Ticket.class);
        verify(tickets).insert(captor.capture());
        Ticket saved = captor.getValue();
        assertEquals(TicketStatus.NEW, saved.getStatus());
        assertEquals("MEDIUM", saved.getPriority());
        assertEquals("INCIDENT", saved.getNature());
        assertEquals("CS001", saved.getSourceSessionId());
        assertEquals("key-1", saved.getIdempotencyKey());
        assertEquals("Network", saved.getCategorySnapshot());
        // 自定义字段值固化进表单定义快照，后续分类改版不影响已建单
        assertEquals("Connection failed", json.readTree(saved.getFieldDefinitionSnapshot()).get("ai_summary").asText());
        assertNull(saved.getFirstResponseAt());
        assertFalse(outcome.duplicated());
        when(tickets.selectById("TK001")).thenReturn(saved);
        when(routing.route(saved)).thenReturn("ENG01");
        // 事务未提交：派单与咨询回执不可见（防回滚后脏副作用）
        verifyNoInteractions(conversions, routing);
        verify(sla).startCompletionSla(eq("TK001"), eq("MEDIUM"), any());
        // 模拟事务提交 -> afterCommit 副作用依次执行
        TransactionSynchronizationManager.getSynchronizations().forEach(s -> s.afterCommit());
        verify(conversions).notifyConverted("CS001", "TK001", employee);
        verify(routing).route(saved);
        var flowCaptor = ArgumentCaptor.forClass(com.itticket.ticket.entity.TicketFlowLog.class);
        verify(flows, times(2)).insert(flowCaptor.capture());
        assertEquals("TICKET_CREATE", flowCaptor.getAllValues().get(0).getEvent());
        assertEquals("TICKET_ASSIGN", flowCaptor.getAllValues().get(1).getEvent());
    }

    /**
     * 幂等重试：同一 idempotency_key 命中既有工单 ->
     * 标记 duplicated、不再 insert、不产生任何业务副作用；
     * 但提交后仍须补发“会话转工单”回执（前端/咨询侧重试场景依赖它收敛状态）。
     */
    @Test
    void idempotentRetryReplaysConversionWithoutNewTicketOrRouting() {
        Ticket existing = new Ticket();
        existing.setTicketId("TK001");
        existing.setSourceSessionId("CS001");
        when(tickets.selectOne(any(QueryWrapper.class))).thenReturn(existing);
        assertTrue(service.create(employee, request(), "key-1").duplicated());
        verify(tickets, never()).insert(any(Ticket.class));
        verifyNoInteractions(flows, notifications, sla, routing);
        TransactionSynchronizationManager.getSynchronizations().forEach(s -> s.afterCommit());
        verify(conversions).notifyConverted("CS001", "TK001", employee);
    }

    /** Header 键与 Body 键同时出现且不一致：语义冲突，必须 400 拒绝而不是任选其一 */
    @Test
    void conflictingHeaderAndBodyKeysAreRejected() {
        CreateTicketRequest req = request();
        req.setIdempotencyKey("body-key");
        assertThrows(BizException.class, () -> service.create(employee, req, "header-key"));
        verify(tickets, never()).insert(any(Ticket.class));
    }

    /** 工单详情附件列表只含“杀毒通过(PASSED)且未撤回”的附件；旧状态值 CLEAN 不得回潮 */
    @Test
    void attachmentQueryUsesPassedScanAndExcludesWithdrawnFiles() {
        Ticket ticket = new Ticket();
        ticket.setTicketId("TK001");
        ticket.setCreatorId("U_EMP01");
        ticket.setStatus(TicketStatus.NEW);
        when(tickets.selectById("TK001")).thenReturn(ticket);
        service.get("TK001");
        var query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(attachments).selectList(query.capture());
        var sql = query.getValue().getSqlSegment();
        var values = query.getValue().getParamNameValuePairs().values();
        assertTrue(sql.contains("scan_status ="));
        assertTrue(sql.contains("withdrawn_at IS NULL"));
        assertTrue(values.contains("PASSED"));
        assertFalse(values.contains("CLEAN"));
        assertTrue(values.contains("TICKET"));
        assertTrue(values.contains("TK001"));
    }

    /**
     * 性质字段双契约兼容：
     * 入参 ticket_nature（规范）与 nature（历史前端）都可反序列化进同一字段；
     * TicketProjection 状态与优先级保持大写枚举值（前端按大写匹配）。
     */
    @Test
    void acceptsBothNatureContractsAndPreservesUppercaseProjection() throws Exception {
        assertEquals("INCIDENT", json.readValue("{\"ticket_nature\":\"INCIDENT\"}", CreateTicketRequest.class).getNature());
        assertEquals("SERVICE_REQUEST", json.readValue("{\"nature\":\"SERVICE_REQUEST\"}", CreateTicketRequest.class).getNature());
        Ticket ticket = new Ticket();
        ticket.setStatus(TicketStatus.ASSIGNED);
        ticket.setPriority("HIGH");
        assertEquals("HIGH", TicketProjection.of(ticket).priority());
        assertEquals("ASSIGNED", TicketProjection.of(ticket).status());
    }
}