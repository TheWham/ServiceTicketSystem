package com.itticket.consultation.service;

/**
 * 工程师的工单侧加权负载(PRD 12.2)。
 *
 * <p>工单是 ticket-service 的事实源,咨询服务不得跨库读表(架构文档 8.1)。
 * 一期默认实现返回 0,即分配只按咨询负载排序;接入 ticket-service 的内部接口后
 * 替换为真实实现即可,无需改动分配算法。该缺口按 RD-013 显式记录,不用空值掩盖。
 */
public interface TicketWorkloadProvider {

    int weightedTicketLoad(String engineerId);

    /** 一期默认:工单负载不可得,按 0 计。 */
    class Unavailable implements TicketWorkloadProvider {
        @Override
        public int weightedTicketLoad(String engineerId) {
            return 0;
        }
    }
}
