package com.itticket.consultation.service;

import com.itticket.consultation.api.*;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.AttachmentProjection;
import com.itticket.consultation.dto.ContentRequest;
import com.itticket.consultation.dto.MessageProjection;
import com.itticket.consultation.entity.*;
import com.itticket.consultation.enums.*;
import com.itticket.consultation.mapper.*;
import com.itticket.consultation.statemachine.Actor;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.*;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConsultationAttachmentServiceTest {
    @TempDir Path root;
    final ConsultationAttachmentMapper mapper = mock(ConsultationAttachmentMapper.class);
    final ConsultationMessageMapper messages = mock(ConsultationMessageMapper.class);
    final ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
    final Map<String, ConsultationAttachment> rows = new LinkedHashMap<>();
    final CurrentUser creator = new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
    final CurrentUser engineer = new CurrentUser("E1", RoleCode.ENGINEER, Actor.ENGINEER);
    Consultation session;
    ConsultationAttachmentService service;

    @BeforeEach void setup() {
        session = new Consultation();
        session.setSessionId("S1"); session.setCreatorId("U1"); session.setCurrentEngineerId("E1");
        session.setStatus(ConsultationStatus.HUMAN_ACTIVE);
        when(transitions.loadForUpdate("S1")).thenReturn(session);
        when(transitions.load("S1")).thenReturn(session);
        service = new ConsultationAttachmentService(mapper, messages, transitions,
                new AuthzService(new ConsultationProperties()), root.toString());
        when(mapper.selectById(anyString())).thenAnswer(c -> rows.get(c.getArgument(0)));
        when(mapper.findDraft(anyString(), anyString())).thenAnswer(c -> rows.values().stream()
                .filter(a -> a.getBizType().equals("CONSULTATION") && a.getBizId().equals(c.getArgument(0))
                        && a.getHash().equals(c.getArgument(1))).findFirst().orElse(null));
        when(mapper.insert(any(ConsultationAttachment.class))).thenAnswer(c -> {
            ConsultationAttachment a = c.getArgument(0);
            assertTrue(rows.values().stream().noneMatch(b -> a.getBizType().equals(b.getBizType())
                    && a.getBizId().equals(b.getBizId()) && a.getHash().equals(b.getHash())), "DB hash uniqueness");
            rows.put(a.getAttachmentId(), a); return 1;
        });
        when(mapper.bindDraft(anyString(), anyString(), anyString(), anyString(), any())).thenAnswer(c -> {
            ConsultationAttachment a = rows.get(c.getArgument(0));
            if (a == null || !a.getBizType().equals("CONSULTATION") || !a.getBizId().equals(c.getArgument(1))
                    || !a.getUploaderId().equals(c.getArgument(2)) || a.getWithdrawnAt() != null) return 0;
            a.setBizType("MESSAGE"); a.setBizId(c.getArgument(3)); return 1;
        });
        when(mapper.withdrawDraft(anyString(), anyString(), anyString(), anyString(), any())).thenAnswer(c -> {
            ConsultationAttachment a = rows.get(c.getArgument(0));
            if (a == null || !a.getBizType().equals("CONSULTATION") || !a.getBizId().equals(c.getArgument(1))
                    || !a.getUploaderId().equals(c.getArgument(2)) || a.getWithdrawnAt() != null) return 0;
            a.setBizId(c.getArgument(3)); a.setWithdrawnAt(c.getArgument(4)); return 1;
        });
    }

    @ParameterizedTest @EnumSource(RoleCode.class)
    void initiator_of_any_role_and_current_engineer_upload_separate_drafts(RoleCode role) {
        CurrentUser owner = new CurrentUser("U1", role, Actor.of(role));
        AttachmentProjection a = service.upload(owner, "S1", file());
        AttachmentProjection b = service.upload(engineer, "S1", file());
        assertNotEquals(a.attachmentId(), b.attachmentId());
        assertEquals(2, rows.size());
        assertEquals(64, rows.get(a.attachmentId()).getBizId().length());
        assertArrayEquals(new byte[]{1,2,3}, service.readContent(owner,"S1",a.attachmentId()).bytes());
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(engineer,"S1",a.attachmentId()));
    }

    @ParameterizedTest @EnumSource(value=ConsultationStatus.class, names={"WAITING_ENGINEER","HUMAN_ACTIVE","PENDING_CONFIRMATION"})
    void all_human_states_allow_upload(ConsultationStatus status) {
        session.setStatus(status);
        assertNotNull(service.upload(creator,"S1",file()).attachmentId());
    }

    @Test void same_hash_deduplicates_and_reupload_survives_repeated_old_withdrawal() {
        String id = service.upload(creator,"S1",file()).attachmentId();
        assertEquals(id, service.upload(creator,"S1",file()).attachmentId());
        service.withdraw(creator,"S1",id);
        service.withdraw(creator,"S1",id);
        String replacement = service.upload(creator,"S1",file()).attachmentId();
        assertNotEquals(id,replacement);
        service.withdraw(creator,"S1",id);
        assertArrayEquals(new byte[]{1,2,3}, service.readContent(creator,"S1",replacement).bytes());
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(creator,"S1",id));
    }

    @Test void inaccessible_session_is_hidden_for_all_operations() {
        String id = service.upload(creator,"S1",file()).attachmentId();
        for (String uid : List.of("stranger", "former-engineer")) {
            CurrentUser outsider = new CurrentUser(uid,RoleCode.PLATFORM_ADMIN,null);
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.upload(outsider,"S1",file()));
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(outsider,"S1",id));
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.withdraw(outsider,"S1",id));
        }
    }

    @Test void binding_checks_whole_batch_before_mutation_and_rejects_other_user_or_session() {
        String own = service.upload(creator,"S1",file()).attachmentId();
        String other = service.upload(engineer,"S1",file()).attachmentId();
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.bind(creator,session,"M1",List.of(own,other)));
        assertEquals("CONSULTATION",rows.get(own).getBizType());
        session.setSessionId("S2");
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.bind(creator,session,"M1",List.of(own)));
        session.setSessionId("S1");
        assertEquals(1,service.bind(creator,session,"M1",List.of(own)).size());
        assertEquals("MESSAGE",rows.get(own).getBizType());
        assertEquals("M1",rows.get(own).getBizId());
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.bind(creator,session,"M2",List.of(own)));
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.withdraw(creator,"S1",own));
    }

    @ParameterizedTest @EnumSource(value=ConsultationStatus.class, names={"RESOLVED","CLOSED","CONVERTED_TO_TICKET"})
    void terminal_sessions_only_allow_reading_sent_attachments(ConsultationStatus status) {
        String sent = service.upload(creator,"S1",file()).attachmentId();
        service.bind(creator,session,"M1",List.of(sent));
        ConsultationMessage m = new ConsultationMessage(); m.setSessionId("S1");
        when(messages.selectById("M1")).thenReturn(m);
        String draft = service.upload(creator,"S1",file()).attachmentId();
        session.setStatus(status);
        assertArrayEquals(new byte[]{1,2,3}, service.readContent(engineer,"S1",sent).bytes());
        assertError(ApiCode.ILLEGAL_STATE_TRANSITION, () -> service.upload(creator,"S1",file()));
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(creator,"S1",draft));
        assertDoesNotThrow(() -> service.withdraw(creator,"S1",draft));
        m.setSessionId("S2");
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(creator,"S1",sent));
        m.setSessionId("S1"); m.setWithdrawnAt(LocalDateTime.now());
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(creator,"S1",sent));
    }

    @Test void ai_upload_is_rejected() {
        session.setStatus(ConsultationStatus.AI_ACTIVE);
        assertError(ApiCode.ILLEGAL_STATE_TRANSITION, () -> service.upload(creator,"S1",file()));
        assertTrue(rows.isEmpty());
    }

    @ParameterizedTest
    @EnumSource(value=ConsultationStatus.class, names={"AI_ACTIVE","RESOLVED","CLOSED","CONVERTED_TO_TICKET"})
    void inactive_sessions_allow_only_current_participants_to_clean_their_own_unsent_drafts(ConsultationStatus status) {
        var tx = new LocalTransactions(rows,new ArrayList<>(),new HashMap<>());
        var proxied = transactional(service,tx);
        String sent = proxied.upload(creator,"S1",file()).attachmentId();
        service.bind(creator,session,"M1",List.of(sent));
        Path sentBlob = root.resolve(rows.get(sent).getObjectKey());
        String creatorDraft = proxied.upload(creator,"S1",file()).attachmentId();
        String engineerDraft = proxied.upload(engineer,"S1",file()).attachmentId();
        session.setStatus(status);
        Consultation otherSession = new Consultation();
        otherSession.setSessionId("S2"); otherSession.setCreatorId("U1");
        otherSession.setCurrentEngineerId("E1"); otherSession.setStatus(status);
        when(transitions.loadForUpdate("S2")).thenReturn(otherSession);

        for (CurrentUser user : List.of(creator,engineer)) {
            String draft = user == creator ? creatorDraft : engineerDraft;
            CurrentUser other = user == creator ? engineer : creator;
            Path blob = root.resolve(rows.get(draft).getObjectKey());
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(user,"S1",draft));
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> proxied.withdraw(other,"S1",draft));
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> proxied.withdraw(user,"S2",draft));
            assertError(ApiCode.OBJECT_NOT_FOUND, () -> proxied.withdraw(
                    new CurrentUser("former-engineer",RoleCode.ENGINEER,Actor.ENGINEER),"S1",draft));
            assertTrue(Files.exists(blob));
            assertDoesNotThrow(() -> proxied.withdraw(user,"S1",draft));
            assertDoesNotThrow(() -> proxied.withdraw(user,"S1",draft));
            assertNotNull(rows.get(draft).getWithdrawnAt());
            assertFalse(Files.exists(blob), "committed cleanup must remove the local file");
            assertError(ApiCode.ILLEGAL_STATE_TRANSITION, () -> proxied.upload(user,"S1",file()));
            assertError(ApiCode.ILLEGAL_STATE_TRANSITION, () -> chatService(service).send(user,session,
                    new ContentRequest(null,"after-close",List.of(draft))));
        }
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> proxied.withdraw(creator,"S1",sent));
        assertEquals("MESSAGE",rows.get(sent).getBizType());
        assertTrue(Files.exists(sentBlob));
    }

    @Test void rejects_missing_empty_oversize_and_unreadable_files() throws Exception {
        assertError(ApiCode.VALIDATION_ERROR, () -> service.upload(creator,"S1",null));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.upload(creator,"S1",new MockMultipartFile("file",new byte[0])));
        MockMultipartFile big = new MockMultipartFile("file","big.bin",null,new byte[20*1024*1024+1]);
        assertError(ApiCode.VALIDATION_ERROR, () -> service.upload(creator,"S1",big));
        org.springframework.web.multipart.MultipartFile broken = mock(org.springframework.web.multipart.MultipartFile.class);
        when(broken.getSize()).thenReturn(1L);
        when(broken.getInputStream()).thenThrow(new java.io.IOException("unreadable"));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.upload(creator,"S1",broken));
        assertTrue(rows.isEmpty());
    }

    @Test void html_svg_and_spoofed_images_are_downloads_but_real_png_is_previewable() throws Exception {
        for(String type:List.of("image/svg+xml","image/png","text/html")) {
            var a=service.upload(creator,"S1",new MockMultipartFile("file","../../fake.png",type,
                    ("<html>"+type+"</html>").getBytes(java.nio.charset.StandardCharsets.UTF_8)));
            assertFalse(a.isImage());
            assertEquals("fake.png",a.fileName());
            assertFalse(service.readContent(creator,"S1",a.attachmentId()).isImage());
            assertTrue(rows.get(a.attachmentId()).getObjectKey().matches("consultation/[a-f0-9-]+"));
        }
        java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();
        javax.imageio.ImageIO.write(new java.awt.image.BufferedImage(1,1,java.awt.image.BufferedImage.TYPE_INT_RGB),"png",out);
        var png=service.upload(creator,"S1",new MockMultipartFile("file","image.bin","application/octet-stream",out.toByteArray()));
        assertTrue(png.isImage()); assertEquals("image/png",png.contentType());
        assertTrue(service.readContent(creator,"S1",png.attachmentId()).isImage());
    }

    @Test void rejects_stored_path_traversal_and_bad_attachment_batches() {
        String id=service.upload(creator,"S1",file()).attachmentId();
        rows.get(id).setObjectKey("../outside");
        assertError(ApiCode.OBJECT_NOT_FOUND, () -> service.readContent(creator,"S1",id));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.bind(creator,session,"M1",Collections.nCopies(11,id)));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.bind(creator,session,"M1",List.of(id,id)));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.bind(creator,session,"M1",Arrays.asList((String)null)));
    }

    @Test void both_sides_send_attachment_only_messages_and_refresh_history_then_retry_without_rebinding() {
        List<ConsultationMessage> stored = messageStore();
        ConsultationMessageService chat = chatService(service);
        for (CurrentUser user : List.of(creator, engineer)) {
            String id = service.upload(user,"S1",file()).attachmentId();
            ContentRequest request = new ContentRequest(null,"client-"+user.userId(),List.of(id));
            MessageProjection sent = chat.send(user,session,request);
            assertEquals("",sent.content());
            assertEquals(id,sent.attachments().get(0).attachmentId());
            assertEquals(user == creator ? "EMPLOYEE" : "ENGINEER",sent.senderType());
            assertEquals(sent,chat.send(user,session,request));
            assertEquals(sent.messageId(), rows.get(id).getBizId());
            assertArrayEquals(new byte[]{1,2,3},service.readContent(user == creator ? engineer : creator,"S1",id).bytes());
        }
        assertEquals(2,stored.size());
        var history = chat.list(creator,session,1,20);
        assertEquals(2,history.items().size());
        assertEquals(MessageProjection.of(stored.get(0)), history.items().get(0));
        assertError(ApiCode.IDEMPOTENCY_CONFLICT, () -> chat.send(engineer,session,
                new ContentRequest("collision","client-U1",null)));
    }

    @ParameterizedTest @EnumSource(RoleCode.class)
    void attachment_only_requester_reply_preserves_pending_confirmation_transition_for_any_role(RoleCode role) {
        messageStore();
        session.setStatus(ConsultationStatus.PENDING_CONFIRMATION);
        CurrentUser requester = new CurrentUser("U1",role,Actor.of(role));
        String id=service.upload(requester,"S1",file()).attachmentId();
        when(transitions.apply(eq(session),any())).thenAnswer(c -> {
            TransitionSpec spec=c.getArgument(1);
            var decision=com.itticket.consultation.statemachine.ConsultationStateMachine.evaluate(
                    session.getStatus(),spec.getEvent(),spec.getActor().actor());
            assertTrue(decision.allowed());
            assertEquals("U1",spec.getActor().userId());
            session.setStatus(decision.to());
            return session;
        });
        chatService(service).send(requester,session,new ContentRequest(null,"reply",List.of(id)));
        assertEquals(ConsultationStatus.HUMAN_ACTIVE,session.getStatus());
    }

    @Test void engineer_attachment_only_first_response_transitions_waiting_to_active() {
        messageStore();
        session.setStatus(ConsultationStatus.WAITING_ENGINEER);
        String id=service.upload(engineer,"S1",file()).attachmentId();
        when(transitions.apply(eq(session),any())).thenAnswer(c -> {
            TransitionSpec spec=c.getArgument(1);
            var decision=com.itticket.consultation.statemachine.ConsultationStateMachine.evaluate(
                    session.getStatus(),spec.getEvent(),spec.getActor().actor());
            assertTrue(decision.allowed()); session.setStatus(decision.to()); return session;
        });
        chatService(service).send(engineer,session,new ContentRequest(null,"reply",List.of(id)));
        assertEquals(ConsultationStatus.HUMAN_ACTIVE,session.getStatus());
    }

    @Test void exact_20mb_is_accepted_and_dishonest_size_cannot_bypass_stream_limit() throws Exception {
        var accepted=service.upload(creator,"S1",new MockMultipartFile("file","big.bin",null,new byte[20*1024*1024]));
        assertEquals(20*1024*1024,accepted.size());
        org.springframework.web.multipart.MultipartFile dishonest=mock(org.springframework.web.multipart.MultipartFile.class);
        when(dishonest.getSize()).thenReturn(1L);
        when(dishonest.getInputStream()).thenReturn(new java.io.ByteArrayInputStream(new byte[20*1024*1024+1]));
        assertError(ApiCode.VALIDATION_ERROR, () -> service.upload(creator,"S1",dishonest));
    }

    @Test void existing_idempotency_transaction_rolls_back_binding_and_replays_success_without_new_message() {
        List<ConsultationMessage> stored = messageStore();
        var records = mock(IdempotencyRecordMapper.class);
        Map<String,IdempotencyRecord> saved = new LinkedHashMap<>();
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new com.baomidou.mybatisplus.core.MybatisConfiguration(),"idempotency"),
                IdempotencyRecord.class);
        when(records.selectOne(any())).thenAnswer(c -> {
            var query=(com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<IdempotencyRecord>)c.getArgument(0);
            query.getSqlSegment();
            var params=query.getParamNameValuePairs();
            return saved.values().stream().filter(r -> r.getOwnerId().equals(params.get("MPGENVAL1"))
                    && r.getOperation().equals(params.get("MPGENVAL2"))
                    && r.getIdempotencyKey().equals(params.get("MPGENVAL3"))).findFirst().orElse(null);
        });
        when(records.insert(any(IdempotencyRecord.class))).thenAnswer(c -> {
            IdempotencyRecord r=c.getArgument(0); saved.put(r.getRecordId(),r); return 1;
        });
        var tx = new LocalTransactions(rows, stored, saved);
        ConsultationAttachmentService transactionalAttachments = transactional(service, tx);
        ConsultationMessageService chat = transactional(chatService(transactionalAttachments),tx);
        var idempotency = new IdempotencyService(records,new org.springframework.transaction.support.TransactionTemplate(tx),
                new ConsultationProperties());
        var consultations = new ConsultationService(mock(ConsultationMapper.class),transitions,chat,
                mock(AssignmentService.class),mock(ConsultationSlaService.class),new AuthzService(new ConsultationProperties()),
                idempotency,mock(OutboxService.class),new ConsultationProperties());
        String id=transactionalAttachments.upload(creator,"S1",file()).attachmentId();
        ContentRequest request=new ContentRequest(null,"retry-client",List.of(id));
        when(messages.insert(any(ConsultationMessage.class))).thenThrow(new IllegalStateException("message write failed"));
        assertThrows(IllegalStateException.class, () -> consultations.sendMessage(creator,"S1",request,"send-key"));
        assertEquals("CONSULTATION",rows.get(id).getBizType());
        assertTrue(stored.isEmpty()); assertTrue(saved.isEmpty());
        doAnswer(c -> { stored.add(c.getArgument(0)); return 1; }).when(messages).insert(any(ConsultationMessage.class));
        MessageProjection first=consultations.sendMessage(creator,"S1",request,"send-key");
        assertEquals(first,consultations.sendMessage(creator,"S1",request,"send-key"));
        assertEquals(first,consultations.sendMessage(creator,"S1",request,"different-key-same-client"));
        assertEquals(1,stored.size()); assertEquals(2,saved.size());
        assertEquals(first.messageId(),rows.get(id).getBizId());
        assertError(ApiCode.IDEMPOTENCY_CONFLICT, () -> consultations.sendMessage(creator,"S1",
                new ContentRequest("different payload","retry-client",List.of(id)),"send-key"));
    }

    @Test void filesystem_lifecycle_follows_transaction_commit_and_rollback() throws Exception {
        var tx=new LocalTransactions(rows,new ArrayList<>(),new HashMap<>());
        var proxied=transactional(service,tx);
        var template=new org.springframework.transaction.support.TransactionTemplate(tx);
        template.executeWithoutResult(status -> {
            proxied.upload(creator,"S1",file());
            status.setRollbackOnly();
        });
        assertTrue(rows.isEmpty());
        try(var files=Files.list(root.resolve("consultation"))) { assertEquals(0,files.count()); }
        String id=proxied.upload(creator,"S1",file()).attachmentId();
        Path blob=root.resolve(rows.get(id).getObjectKey());
        template.executeWithoutResult(status -> {
            proxied.withdraw(creator,"S1",id);
            assertTrue(Files.exists(blob));
            status.setRollbackOnly();
        });
        assertNull(rows.get(id).getWithdrawnAt()); assertTrue(Files.exists(blob));
        proxied.withdraw(creator,"S1",id);
        assertFalse(Files.exists(blob));
    }

    @SuppressWarnings("unchecked")
    private static <T> T transactional(T target, LocalTransactions tx) {
        var factory = new org.springframework.aop.framework.ProxyFactory(target);
        factory.setProxyTargetClass(true);
        factory.addAdvice(new org.springframework.transaction.interceptor.TransactionInterceptor(tx,
                new org.springframework.transaction.annotation.AnnotationTransactionAttributeSource()));
        return (T)factory.getProxy();
    }

    /** In-memory persistence snapshots; exercises real Spring transaction boundaries without a DB connection. */
    private static class LocalTransactions extends org.springframework.transaction.support.AbstractPlatformTransactionManager {
        final Map<String,ConsultationAttachment> rows;
        final List<ConsultationMessage> messages;
        final Map<String,IdempotencyRecord> records;
        final ThreadLocal<State> current=ThreadLocal.withInitial(State::new);
        LocalTransactions(Map<String,ConsultationAttachment> rows,List<ConsultationMessage> messages,Map<String,IdempotencyRecord> records) {
            this.rows=rows; this.messages=messages; this.records=records;
        }
        static class State { boolean active; Map<String,ConsultationAttachment> rows; List<ConsultationMessage> messages; Map<String,IdempotencyRecord> records; }
        @Override protected Object doGetTransaction() { return current.get(); }
        @Override protected boolean isExistingTransaction(Object transaction) { return ((State)transaction).active; }
        @Override protected void doBegin(Object transaction, org.springframework.transaction.TransactionDefinition definition) {
            State state=(State)transaction; state.active=true;
            state.rows=new LinkedHashMap<>();
            rows.forEach((id,row) -> { var copy=new ConsultationAttachment(); org.springframework.beans.BeanUtils.copyProperties(row,copy); state.rows.put(id,copy); });
            state.messages=new ArrayList<>(messages); state.records=new LinkedHashMap<>(records);
        }
        @Override protected void doCommit(org.springframework.transaction.support.DefaultTransactionStatus status) { }
        @Override protected void doRollback(org.springframework.transaction.support.DefaultTransactionStatus status) {
            State state=(State)status.getTransaction();
            rows.clear(); rows.putAll(state.rows); messages.clear(); messages.addAll(state.messages);
            records.clear(); records.putAll(state.records);
        }
        @Override protected void doSetRollbackOnly(org.springframework.transaction.support.DefaultTransactionStatus status) { }
        @Override protected void doCleanupAfterCompletion(Object transaction) { current.remove(); }
    }

    private ConsultationMessageService chatService(ConsultationAttachmentService attachments) {
        return new ConsultationMessageService(messages, transitions, mock(AssignmentService.class),
                mock(ConsultationSlaService.class),new AuthzService(new ConsultationProperties()), attachments);
    }

    private List<ConsultationMessage> messageStore() {
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new com.baomidou.mybatisplus.core.MybatisConfiguration(),"test"),
                ConsultationMessage.class);
        List<ConsultationMessage> stored=new ArrayList<>();
        when(messages.insert(any(ConsultationMessage.class))).thenAnswer(c -> { stored.add(c.getArgument(0)); return 1; });
        when(messages.selectOne(any())).thenAnswer(c -> {
            var query=(com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ConsultationMessage>)c.getArgument(0);
            query.getSqlSegment();
            var args=query.getParamNameValuePairs();
            return stored.stream().filter(m -> m.getSessionId().equals(args.get("MPGENVAL1"))
                    && m.getClientMessageId().equals(args.get("MPGENVAL2"))).findFirst().orElse(null);
        });
        when(messages.selectById(anyString())).thenAnswer(c -> stored.stream()
                .filter(m -> m.getMessageId().equals(c.getArgument(0))).findFirst().orElse(null));
        when(messages.selectPage(any(),any())).thenAnswer(c -> {
            com.baomidou.mybatisplus.core.metadata.IPage<ConsultationMessage> page=c.getArgument(0);
            page.setRecords(List.copyOf(stored)); page.setTotal(stored.size()); return page;
        });
        return stored;
    }

    MockMultipartFile file() { return new MockMultipartFile("file","report.pdf","application/pdf",new byte[]{1,2,3}); }
    static void assertError(ApiCode code, org.junit.jupiter.api.function.Executable action) {
        assertEquals(code,assertThrows(ApiException.class,action).getCode());
    }
}
