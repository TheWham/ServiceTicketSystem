package com.itticket.ticket.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.entity.Attachment;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.AttachmentMapper;
import com.itticket.ticket.mapper.TicketMapper;
import com.itticket.ticket.vo.AttachmentUploadVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 工单照片附件 AttachmentService 单元测试。
 *
 * 被测对象的两段式设计：
 *  1) 上传阶段：校验类型/大小 → SHA-256 → 落盘到临时目录 → attachment 表登记草稿态
 *     （biz_type=TICKET、biz_id=上传人 id 作为“草稿命名空间”、scan_status=PASSED）；
 *  2) 绑定阶段：创建工单时 TicketService.bindAttachments 把 biz_id 改为工单号（此处不测，
 *     由工单创建链路承担；本类聚焦上传/撤回/读取的访问控制）。
 *
 * 访问控制矩阵（readContent / withdraw）：
 *  - 草稿态（biz_id == 上传人）：只有上传人本人可见/可撤回；
 *  - 已绑定工单：提单人、处理人（assignee）、PLATFORM_ADMIN 可见，其他人 403。
 *
 * 存储根目录通过 ReflectionTestUtils 指向 @TempDir，避免污染工作目录。
 */
class AttachmentServiceTest {

    @TempDir
    Path tempDir; // JUnit 临时目录：每个用例独立、跑完自动清理

    private AttachmentMapper attachmentMapper;
    private TicketMapper ticketMapper;
    private AttachmentService service;

    /** 上传人（员工）与无关路人，用于权限断言 */
    private static final UserContext.CurrentUser EMP01 =
            new UserContext.CurrentUser("U_EMP01", "员工一", "EMPLOYEE", "IT");
    private static final UserContext.CurrentUser STRANGER =
            new UserContext.CurrentUser("U_EMP99", "路人", "EMPLOYEE", "IT");
    private static final UserContext.CurrentUser ADMIN =
            new UserContext.CurrentUser("U_ADM01", "主管", "PLATFORM_ADMIN", "IT");
    private static final UserContext.CurrentUser ENG02 =
            new UserContext.CurrentUser("U_ENG02", "工程师二", "ENGINEER", "IT");

    @BeforeEach
    void setUp() {
        attachmentMapper = mock(AttachmentMapper.class);
        ticketMapper = mock(TicketMapper.class);
        service = new AttachmentService(attachmentMapper, ticketMapper);
        ReflectionTestUtils.setField(service, "storageDir", tempDir.toString());
    }

    /** 造一张 1x1 PNG 的假照片（内容无所谓，类型/扩展名才是校验对象） */
    private static MockMultipartFile photo(String name, String contentType, int bytes) {
        return new MockMultipartFile("file", name, contentType, new byte[bytes]);
    }

    // ---------------- 上传 ----------------

    /** 正常上传：落盘成功 + attachment 行登记为草稿态，且返回的 attachment_id 可用于后续绑定 */
    @Test
    void upload_ok_writesFileAndDraftRow() {
        AttachmentUploadVO vo = service.upload(EMP01, photo("现场故障.png", "image/png", 128));

        assertNotNull(vo.getAttachmentId());
        assertEquals("现场故障.png", vo.getFileName());
        assertEquals(128L, vo.getSize());
        // 文件确实写到了临时目录（objectKey 以 attachmentId 结尾）
        try {
            boolean written = Files.walk(tempDir).anyMatch(p -> p.toString().contains(vo.getAttachmentId()));
            assertTrue(written, "照片字节应已落盘");
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
        // 登记行为草稿态：biz_id=上传人、PASSED、时间戳齐全
        ArgumentCaptor<Attachment> captor = ArgumentCaptor.forClass(Attachment.class);
        verify(attachmentMapper).insert(captor.capture());
        Attachment row = captor.getValue();
        assertEquals("TICKET", row.getBizType());
        assertEquals("U_EMP01", row.getBizId());
        assertEquals("U_EMP01", row.getUploaderId());
        assertEquals("PASSED", row.getScanStatus());
        assertEquals(64, row.getHash().length()); // SHA-256 hex 固定 64 字符
        assertNotNull(row.getUploadedAt());
    }

    /** 非图片扩展名 → 拒绝（防上传脚本/可执行文件） */
    @Test
    void upload_rejectsNonImageExtension() {
        BizException e = assertThrows(BizException.class,
                () -> service.upload(EMP01, photo("木马.exe", "image/png", 10)));
        assertEquals(ErrorCode.PARAM_INVALID, e.getErrorCode());
        verify(attachmentMapper, never()).insert(any(Attachment.class));
    }

    /** 扩展名伪装成 png 但 Content-Type 非 image/* → 拒绝（双重校验缺一不可） */
    @Test
    void upload_rejectsForgedContentType() {
        assertThrows(BizException.class,
                () -> service.upload(EMP01, photo("伪装.png", "application/x-msdownload", 10)));
        verify(attachmentMapper, never()).insert(any(Attachment.class));
    }

    /** 超过 20MB → 拒绝（SPEC attachment 表约束：≤20MB） */
    @Test
    void upload_rejectsOversize() {
        byte[] big = new byte[(int) AttachmentService.MAX_SIZE_BYTES + 1];
        assertThrows(BizException.class,
                () -> service.upload(EMP01, new MockMultipartFile("file", "大图.png", "image/png", big)));
        verify(attachmentMapper, never()).insert(any(Attachment.class));
    }

    /** 空文件 → 拒绝 */
    @Test
    void upload_rejectsEmptyFile() {
        assertThrows(BizException.class,
                () -> service.upload(EMP01, photo("空.png", "image/png", 0)));
    }

    // ---------------- 撤回 ----------------

    /** 草稿态由上传人本人撤回 → withdrawn_at 落库 */
    @Test
    void withdraw_ok_byUploader() {
        Attachment att = draftAttachment("ATT1", "U_EMP01");
        when(attachmentMapper.selectById("ATT1")).thenReturn(att);

        service.withdraw(EMP01, "ATT1");
        assertNotNull(att.getWithdrawnAt());
        verify(attachmentMapper).updateById(att);
    }

    /** 他人撤回我的草稿照片 → 403 */
    @Test
    void withdraw_forbidden_forStranger() {
        when(attachmentMapper.selectById("ATT1")).thenReturn(draftAttachment("ATT1", "U_EMP01"));

        BizException e = assertThrows(BizException.class, () -> service.withdraw(STRANGER, "ATT1"));
        assertEquals(ErrorCode.FORBIDDEN, e.getErrorCode());
    }

    /** 已绑定工单的附件不可再撤回 */
    @Test
    void withdraw_rejectsBoundAttachment() {
        Attachment att = draftAttachment("ATT1", "U_EMP01");
        att.setBizId("TK202609300001"); // 已绑定工单
        when(attachmentMapper.selectById("ATT1")).thenReturn(att);

        assertThrows(BizException.class, () -> service.withdraw(EMP01, "ATT1"));
    }

    // ---------------- 读取内容 ----------------

    /** 草稿态：上传人本人可读回（提单页回显场景） */
    @Test
    void readContent_draftReadableByUploader() throws Exception {
        Attachment att = draftAttachment("ATT1", "U_EMP01");
        writePhotoBytes(att, new byte[]{1, 2, 3});
        when(attachmentMapper.selectById("ATT1")).thenReturn(att);

        AttachmentService.AttachmentContent c = service.readContent(EMP01, "ATT1");
        assertEquals(3, c.bytes().length);
        assertEquals("image/png", c.contentType());
    }

    /** 草稿态：他人不可读（403） */
    @Test
    void readContent_draftInvisibleToStranger() {
        Attachment att = draftAttachment("ATT1", "U_EMP01");
        when(attachmentMapper.selectById("ATT1")).thenReturn(att);

        assertThrows(BizException.class, () -> service.readContent(STRANGER, "ATT1"));
    }

    /** 已绑定工单：提单人 / 处理人 / 主管可读，无关员工 403 —— 访问控制矩阵全量断言 */
    @Test
    void readContent_boundAccessMatrix() throws Exception {
        Attachment att = draftAttachment("ATT1", "U_EMP01");
        att.setBizId("TK202609300001");
        writePhotoBytes(att, new byte[]{9});
        when(attachmentMapper.selectById("ATT1")).thenReturn(att);

        Ticket ticket = new Ticket();
        ticket.setTicketId("TK202609300001");
        ticket.setCreatorId("U_EMP01");
        ticket.setAssigneeId("U_ENG02");
        when(ticketMapper.selectById("TK202609300001")).thenReturn(ticket);

        assertEquals(1, service.readContent(EMP01, "ATT1").bytes().length);   // 提单人
        assertEquals(1, service.readContent(ENG02, "ATT1").bytes().length);   // 处理人
        assertEquals(1, service.readContent(ADMIN, "ATT1").bytes().length);   // 主管
        assertThrows(BizException.class, () -> service.readContent(STRANGER, "ATT1")); // 路人
    }

    /** 已撤回 / 不存在的附件 → 404 语义 */
    @Test
    void readContent_notFoundOrWithdrawn() {
        when(attachmentMapper.selectById("GONE")).thenReturn(null);
        assertThrows(BizException.class, () -> service.readContent(EMP01, "GONE"));

        Attachment att = draftAttachment("ATT2", "U_EMP01");
        att.setWithdrawnAt(LocalDateTime.now());
        when(attachmentMapper.selectById("ATT2")).thenReturn(att);
        assertThrows(BizException.class, () -> service.readContent(EMP01, "ATT2"));
    }

    // ---------------- 辅助 ----------------

    /** 造一条草稿态附件行（biz_id=上传人，未撤回） */
    private static Attachment draftAttachment(String id, String uploader) {
        Attachment att = new Attachment();
        att.setAttachmentId(id);
        att.setBizType("TICKET");
        att.setBizId(uploader);
        att.setUploaderId(uploader);
        att.setObjectKey("ticket/202609/" + id + ".png");
        att.setFileName("photo.png");
        att.setSize(3L);
        att.setHash("a".repeat(64));
        att.setContentType("image/png");
        att.setScanStatus("PASSED");
        att.setUploadedAt(LocalDateTime.now());
        return att;
    }

    /** 按附件 objectKey 在临时目录写入照片字节，模拟磁盘上的真实文件 */
    private void writePhotoBytes(Attachment att, byte[] bytes) throws Exception {
        Path p = tempDir.resolve(att.getObjectKey());
        Files.createDirectories(p.getParent());
        Files.write(p, bytes);
    }
}
