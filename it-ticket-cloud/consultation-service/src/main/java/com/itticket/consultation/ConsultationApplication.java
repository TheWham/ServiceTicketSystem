package com.itticket.consultation;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * 咨询服务:智能客服(AI 咨询)与转人工。
 *
 * <p>契约边界:
 * <ul>
 *   <li>接口目录 AI-005(AI-API-001~005)与 OpenAPI 05 的 /consultations/**;</li>
 *   <li>状态合法性 SM-CONSULT-001,本服务是咨询状态的唯一写入方;</li>
 *   <li>AI 不得创建、修改或关闭工单(AI-001),转工单只在咨询侧打标并发事件。</li>
 * </ul>
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableScheduling
@ConfigurationPropertiesScan
@MapperScan("com.itticket.consultation.mapper")
public class ConsultationApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConsultationApplication.class, args);
    }
}
