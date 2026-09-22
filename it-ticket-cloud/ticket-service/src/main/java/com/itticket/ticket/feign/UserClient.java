package com.itticket.ticket.feign;

import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.List;

/** 调用 user-service 的内部接口(经 Nacos 服务发现直连,不经网关) */
@FeignClient(name = "user-service", contextId = "userClient")
public interface UserClient {

    @GetMapping("/api/internal/users/{userId}")
    Result<UserInfo> getUser(@PathVariable("userId") String userId);

    @PostMapping("/api/internal/users/batch")
    Result<List<UserInfo>> batch(@RequestBody IdsRequest request);
}
