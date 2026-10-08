package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiExceptionHandler;
import com.itticket.consultation.dto.AttachmentProjection;
import com.itticket.consultation.service.*;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.hamcrest.Matchers.startsWith;

class ConsultationAttachmentControllerTest {
    final ConsultationAttachmentService attachments=mock(ConsultationAttachmentService.class);
    final AuthzService authz=mock(AuthzService.class);
    final MockMvc mvc=MockMvcBuilders.standaloneSetup(new ConsultationAttachmentController(attachments,authz))
            .setControllerAdvice(new ApiExceptionHandler()).build();

    @Test void multipart_returns_fixed_envelope_and_delete_accepts_repeated_draft_removal() throws Exception {
        when(attachments.upload(any(),eq("S1"),any())).thenReturn(new AttachmentProjection("A1","a.pdf","application/pdf",3,false));
        mvc.perform(multipart("/api/v1/consultations/S1/attachments")
                .file(new MockMultipartFile("file","a.pdf","application/pdf",new byte[]{1,2,3})))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.attachment_id").value("A1"))
                .andExpect(jsonPath("$.data.file_name").value("a.pdf"))
                .andExpect(jsonPath("$.data.content_type").value("application/pdf"))
                .andExpect(jsonPath("$.data.size").value(3)).andExpect(jsonPath("$.data.is_image").value(false));
        for(int i=0;i<2;i++) mvc.perform(delete("/api/v1/consultations/S1/attachments/A1")).andExpect(status().isOk());
    }

    @Test void downloads_are_binary_with_nosniff_and_only_verified_images_inline() throws Exception {
        for(boolean image:new boolean[]{false,true}) {
            String type=image?"image/png":"text/html";
            when(attachments.readContent(any(),eq("S1"),eq("A1"))).thenReturn(
                    new ConsultationAttachmentService.AttachmentContent("附件.txt",type,new byte[]{1,2,3},image));
            mvc.perform(get("/api/v1/consultations/S1/attachments/A1/content"))
                    .andExpect(status().isOk()).andExpect(content().bytes(new byte[]{1,2,3}))
                    .andExpect(content().contentType(MediaType.parseMediaType(type)))
                    .andExpect(header().string("Content-Disposition",startsWith(image?"inline;":"attachment;")))
                    .andExpect(header().string("X-Content-Type-Options","nosniff"))
                    .andExpect(header().string("Cache-Control","no-store"));
        }
    }

    @Test void missing_file_uses_validation_envelope() throws Exception {
        mvc.perform(multipart("/api/v1/consultations/S1/attachments"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
    }

    @Test void multipart_framework_limit_returns_readable_validation_instead_of_500() throws Exception {
        when(attachments.upload(any(),eq("S1"),any())).thenThrow(
                new org.springframework.web.multipart.MaxUploadSizeExceededException(21L*1024*1024));
        mvc.perform(multipart("/api/v1/consultations/S1/attachments")
                .file(new MockMultipartFile("file",new byte[]{1})))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
                .andExpect(jsonPath("$.errors[0].field").value("file"));
    }
}
