package com.itticket.ticket.service;

/**
 * 优先级计算矩阵（PRD §11.4）。
 * 工程师接单时确认「影响范围 × 紧急程度」，系统按矩阵得出正式优先级；
 * 工程师不能绕过矩阵直接指定结果，平台管理员可填原因后调整。
 *
 * 影响范围：SINGLE 单个员工 / DEPARTMENT 多人或单部门 / CROSS_DEPT 跨部门或核心系统
 * 紧急程度：LOW 有替代方案 / MEDIUM 工作明显受阻 / HIGH 业务中断、安全或数据风险
 *
 * 矩阵：
 *              紧急 LOW    紧急 MEDIUM   紧急 HIGH
 * SINGLE         低          低           中
 * DEPARTMENT     低          中           高
 * CROSS_DEPT     中          高           高
 */
public final class PriorityMatrix {

    public static final String HIGH = "HIGH";
    public static final String MEDIUM = "MEDIUM";
    public static final String LOW = "LOW";

    // 影响范围
    public static final String SCOPE_SINGLE = "SINGLE";
    public static final String SCOPE_DEPARTMENT = "DEPARTMENT";
    public static final String SCOPE_CROSS_DEPT = "CROSS_DEPT";

    // 紧急程度
    public static final String URGENCY_LOW = "LOW";
    public static final String URGENCY_MEDIUM = "MEDIUM";
    public static final String URGENCY_HIGH = "HIGH";

    private PriorityMatrix() {}

    /** 按矩阵计算优先级，非法输入返回 null */
    public static String compute(String impactScope, String urgencyLevel) {
        if (impactScope == null || urgencyLevel == null) return null;
        int scope = switch (impactScope) {
            case SCOPE_SINGLE -> 0;
            case SCOPE_DEPARTMENT -> 1;
            case SCOPE_CROSS_DEPT -> 2;
            default -> -1;
        };
        int urg = switch (urgencyLevel) {
            case URGENCY_LOW -> 0;
            case URGENCY_MEDIUM -> 1;
            case URGENCY_HIGH -> 2;
            default -> -1;
        };
        if (scope < 0 || urg < 0) return null;
        // 矩阵[scope][urgency]，值：0=LOW 1=MEDIUM 2=HIGH
        int[][] matrix = {
                {0, 0, 1},  // SINGLE:      低 低 中
                {0, 1, 2},  // DEPARTMENT:  低 中 高
                {1, 2, 2}   // CROSS_DEPT:  中 高 高
        };
        return switch (matrix[scope][urg]) {
            case 2 -> HIGH;
            case 1 -> MEDIUM;
            default -> LOW;
        };
    }

    public static boolean isValidPriority(String p) {
        return HIGH.equals(p) || MEDIUM.equals(p) || LOW.equals(p);
    }
}
