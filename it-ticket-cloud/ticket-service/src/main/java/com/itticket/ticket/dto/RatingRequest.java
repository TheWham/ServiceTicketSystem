package com.itticket.ticket.dto;

import lombok.Data;

/** 满意度评价请求 */
@Data
public class RatingRequest {
    private Integer score;
    private String comment;
}
