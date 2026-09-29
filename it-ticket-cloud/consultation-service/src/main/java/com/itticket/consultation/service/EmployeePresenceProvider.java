package com.itticket.consultation.service;

/**
 * 员工会话是否已断开。
 *
 * <p>PRD 8.3 对自动解决给出的是合取条件:工程师已提交解决结论、<b>员工会话已断开</b>、
 * 员工 10 分钟内未回复,三者同时满足才允许自动判定已解决;并且明确写了
 * "不得仅因普通对话连续 10 分钟无消息而自动判定解决"。
 *
 * <p>DM-004 目前没有承载"员工会话断开"这一事实的字段或表,一期也没有相应的在线状态来源
 * (engineer_runtime_state 只覆盖工程师)。因此默认实现返回"未知",
 * 自动解决调度器据此永不触发 —— 宁可不自动关单,也不能用超时沉默冒充断开(RD-013)。
 */
public interface EmployeePresenceProvider {

    /** 返回 true 仅当有确切证据表明该员工的会话已断开。 */
    boolean isDisconnected(String employeeId, String sessionId);

    /** 一期默认:断开事实不可得,一律按未断开处理。 */
    class Unknown implements EmployeePresenceProvider {
        @Override
        public boolean isDisconnected(String employeeId, String sessionId) {
            return false;
        }
    }
}
