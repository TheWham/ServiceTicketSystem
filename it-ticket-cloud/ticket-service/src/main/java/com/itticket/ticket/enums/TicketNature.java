package com.itticket.ticket.enums;

/** 工单性质 §10.2：INCIDENT 故障 / SERVICE_REQUEST 服务请求 */
public enum TicketNature {
    INCIDENT,
    SERVICE_REQUEST;

    public static boolean isValid(String v) {
        if (v == null) return false;
        for (TicketNature n : values()) {
            if (n.name().equals(v)) return true;
        }
        return false;
    }
}
