package com.itticket.ticket.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.entity.Attachment;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.AttachmentMapper;
import com.itticket.ticket.mapper.TicketMapper;
import com.itticket.ticket.vo.AttachmentUploadVO;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * 工单照片附件 —— SPEC 01 Attachment 模型的本地实现。
 *
 * 上传两段式：先 POST /tickets/attachments/upload 落盘并登记 attachment 行
 * （biz_type=TICKET，biz_id=上传人 userId 作为“草稿命名空间”，scan_status 直接 PASSED），
 * 创建工单时 TicketService.bindAttachments 把 biz_id 改为正式 ticket_id 完成绑定。
 *
 * 已知降级（RD 类）：本部署无病毒扫描组件，类型/大小本地校验通过即标记 PASSED；
 * 存储为本地磁盘（SPEC 的对象存储 objectKey 以目录路径实现）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AttachmentService {

    /** 图片白名单（SPEC AttachmentBizType=TICKET 场景仅收照片） */
    private static final Set<String> ALLOWED_EXT = Set.of("jpg", "jpeg", "png", "gif", "webp", "bmp");
    /** 单张上限 20MB（与 attachment 表注释 ≤20MB 对齐） */
    public static final long MAX_SIZE_BYTES = 20L * 1024 * 1024;

    private final AttachmentMapper attachmentMapper;
    private final TicketMapper ticketMapper;

    /** 本地存储根目录，可用 itticket.attachment.storage-dir 覆盖 */
    @Value("${itticket.attachment.storage-dir:./data/attachments}")
    private String storageDir;

    public record AttachmentContent(String fileName, String contentType, byte[] bytes) {}

    /** 上传照片：校验类型/大小 → 计算 SHA-256 → 落盘 → 登记草稿态附件行 */
    public AttachmentUploadVO upload(UserContext.CurrentUser user, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请选择要上传的照片");
        }
        String original = file.getOriginalFilename() == null ? "photo" : file.getOriginalFilename();
        String ext = extOf(original);
        String contentType = file.getContentType();
        if (ext == null || !ALLOWED_EXT.contains(ext) || contentType == null || !contentType.startsWith("image/")) {
            throw new BizException(ErrorCode.PARAM_INVALID, "仅支持图片格式（jpg/png/gif/webp/bmp）");
        }
        if (file.getSize() > MAX_SIZE_BYTES) {
            throw new BizException(ErrorCode.PARAM_INVALID, "单张照片不能超过 20MB");
        }
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "读取上传文件失败");
        }
        String sha256 = sha256Hex(bytes);
        String attachmentId = "ATT" + UUID.randomUUID().toString().replace("-", "").toUpperCase();
        String objectKey = "ticket/" + LocalDateTime.now(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern("yyyyMM"))
                + "/" + attachmentId + "." + ext;
        try {
            Path target = Path.of(storageDir).resolve(objectKey).normalize();
            Files.createDirectories(target.getParent());
            Files.write(target, bytes);
        } catch (IOException e) {
            log.error("附件落盘失败: {}", objectKey, e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "附件保存失败");
        }

        Attachment att = new Attachment();
        att.setAttachmentId(attachmentId);
        att.setBizType("TICKET");
        // 草稿命名空间：绑定前 biz_id = 上传人 id，绑定后改为工单 id
        att.setBizId(user.getUserId());
        att.setUploaderId(user.getUserId());
        att.setObjectKey(objectKey);
        att.setFileName(original.length() > 255 ? original.substring(original.length() - 255) : original);
        att.setSize(file.getSize());
        att.setHash(sha256);
        att.setContentType(contentType);
        att.setScanStatus("PASSED"); // 无扫描组件（RD 降级），本地校验通过即放行
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        att.setUploadedAt(now);
        att.setCreatedAt(now);
        att.setUpdatedAt(now);
        try {
            attachmentMapper.insert(att);
        } catch (org.springframework.dao.DuplicateKeyException e) {
            // uk(biz_type,biz_id,sha256)：同一人重复上传同一照片 → 去重，直接复用已有附件
            Attachment existing = attachmentMapper.selectOne(new QueryWrapper<Attachment>()
                    .eq("biz_type", "TICKET").eq("biz_id", user.getUserId()).eq("hash", sha256)
                    .isNull("withdrawn_at"));
            if (existing != null) {
                log.info("照片内容重复，复用已有附件: {}", existing.getAttachmentId());
                return new AttachmentUploadVO(existing.getAttachmentId(), existing.getFileName(), existing.getSize());
            }
            throw new BizException(ErrorCode.PARAM_INVALID, "该照片已绑定到其他工单，请勿重复使用");
        }
        return new AttachmentUploadVO(attachmentId, att.getFileName(), att.getSize());
    }

    /** 撤回草稿态附件（绑定到工单后不可再撤回） */
    public void withdraw(UserContext.CurrentUser user, String attachmentId) {
        Attachment att = requireAttachment(attachmentId);
        if (!att.getUploaderId().equals(user.getUserId())) {
            throw new BizException(ErrorCode.FORBIDDEN, "只能删除自己上传的附件");
        }
        if (!att.getBizId().equals(user.getUserId())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "附件已绑定工单，不可撤回");
        }
        att.setWithdrawnAt(LocalDateTime.now(ZoneOffset.UTC));
        att.setUpdatedAt(att.getWithdrawnAt());
        attachmentMapper.updateById(att);
    }

    /** 读取照片内容：草稿态仅上传人；绑定后仅提单人/处理人/PLATFORM_ADMIN */
    public AttachmentContent readContent(UserContext.CurrentUser user, String attachmentId) {
        Attachment att = requireAttachment(attachmentId);
        boolean draft = att.getBizId().equals(att.getUploaderId());
        if (draft) {
            if (!att.getUploaderId().equals(user.getUserId())) {
                throw new BizException(ErrorCode.FORBIDDEN, "无权访问该附件");
            }
        } else {
            Ticket ticket = ticketMapper.selectById(att.getBizId());
            TicketVisibility.checkRead(user, ticket);
            boolean allowed = ticket != null && (ticket.getCreatorId().equals(user.getUserId())
                    || user.getUserId().equals(ticket.getAssigneeId())
                    || "PLATFORM_ADMIN".equals(user.getRole()));
            if (!allowed) {
                throw new BizException(ErrorCode.FORBIDDEN, "无权访问该附件");
            }
        }
        try {
            byte[] bytes = Files.readAllBytes(Path.of(storageDir).resolve(att.getObjectKey()).normalize());
            return new AttachmentContent(att.getFileName(), att.getContentType(), bytes);
        } catch (IOException e) {
            log.error("附件读取失败: {}", att.getObjectKey(), e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "附件读取失败");
        }
    }

    private Attachment requireAttachment(String attachmentId) {
        Attachment att = attachmentMapper.selectById(attachmentId);
        if (att == null || att.getWithdrawnAt() != null) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND, "附件不存在或已撤回");
        }
        return att;
    }

    private static String extOf(String name) {
        int dot = name.lastIndexOf('.');
        return dot < 0 ? null : name.substring(dot + 1).toLowerCase();
    }

    private static String sha256Hex(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
