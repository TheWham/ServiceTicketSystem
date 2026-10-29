package com.itticket.ticket.mapper;

import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

/**
 * 工单处理方案（{@code ticket_resolution.solution}）的只读投影。
 *
 * <p>只服务于分析链路的根因维度：根因**只从处理方案文本抽取**，不从工单描述推断
 * —— 从描述猜根因正是幻觉的主要来源。当前该表无写入方（0 行），读取路径提前就位，
 * 等工单开始沉淀方案记录后无需改代码即可产出根因占比。
 */
public interface TicketResolutionMapper {

    /**
     * 批量取工单的处理方案。整批一次查询而不是逐单查 —— 分析链路一次要扫几百上千行，
     * N+1 查询会把取数耗时从毫秒级推到秒级。
     */
    @Select("<script>"
            + "SELECT ticket_id AS ticketId, solution FROM ticket_resolution "
            + "WHERE ticket_id IN "
            + "<foreach item='id' collection='ids' open='(' separator=',' close=')'>#{id}</foreach>"
            + "</script>")
    List<Map<String, Object>> selectSolutions(@Param("ids") List<String> ids);
}