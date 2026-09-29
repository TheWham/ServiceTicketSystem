package com.itticket.consultation.config;

import com.itticket.consultation.service.DomainEventPublisher;
import com.itticket.consultation.service.EmployeePresenceProvider;
import com.itticket.consultation.service.TicketWorkloadProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 一期缺省实现的接线点。
 *
 * <p>这三个 Bean 都是跨域协作的缺口占位:各自的真实事实源分别在队列基础设施、
 * ticket-service 和员工在线状态来源。用 {@code @ConditionalOnMissingBean} 声明,
 * 真实实现进来时直接覆盖,业务代码无需改动。缺口本身按 RD-013 显式记录,不用空值掩盖。
 */
@Configuration
public class ConsultationBeansConfig {

    @Bean
    @ConditionalOnMissingBean(DomainEventPublisher.class)
    public DomainEventPublisher domainEventPublisher() {
        return new DomainEventPublisher.Logging();
    }

    @Bean
    @ConditionalOnMissingBean(TicketWorkloadProvider.class)
    public TicketWorkloadProvider ticketWorkloadProvider() {
        return new TicketWorkloadProvider.Unavailable();
    }

    @Bean
    @ConditionalOnMissingBean(EmployeePresenceProvider.class)
    public EmployeePresenceProvider employeePresenceProvider() {
        return new EmployeePresenceProvider.Unknown();
    }
}
