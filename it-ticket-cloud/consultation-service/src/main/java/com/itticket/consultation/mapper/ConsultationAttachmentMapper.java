package com.itticket.consultation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.consultation.entity.ConsultationAttachment;
import org.apache.ibatis.annotations.*;
import java.time.LocalDateTime;

@Mapper
public interface ConsultationAttachmentMapper extends BaseMapper<ConsultationAttachment> {
    // Locking read avoids a stale repeatable-read snapshot after waiting for the session lock.
    @Select("SELECT * FROM attachment WHERE biz_type='CONSULTATION' AND biz_id=#{namespace} AND hash=#{hash} FOR UPDATE")
    ConsultationAttachment findDraft(@Param("namespace") String namespace, @Param("hash") String hash);

    @Update("""
            UPDATE attachment SET biz_type='MESSAGE', biz_id=#{messageId}, updated_at=#{now}
            WHERE attachment_id=#{id} AND biz_type='CONSULTATION' AND biz_id=#{namespace}
              AND uploader_id=#{uploader} AND withdrawn_at IS NULL AND scan_status='PASSED'
            """)
    int bindDraft(@Param("id") String id, @Param("namespace") String namespace,
                  @Param("uploader") String uploader, @Param("messageId") String messageId,
                  @Param("now") LocalDateTime now);

    @Update("""
            UPDATE attachment SET biz_id=#{tombstone}, withdrawn_at=#{now}, updated_at=#{now}
            WHERE attachment_id=#{id} AND biz_type='CONSULTATION' AND biz_id=#{namespace}
              AND uploader_id=#{uploader} AND withdrawn_at IS NULL
            """)
    int withdrawDraft(@Param("id") String id, @Param("namespace") String namespace,
                      @Param("uploader") String uploader, @Param("tombstone") String tombstone,
                      @Param("now") LocalDateTime now);
}
