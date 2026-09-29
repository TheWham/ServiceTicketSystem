package com.itticket.user.service;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.common.api.BizException;
import com.itticket.user.entity.*;
import com.itticket.user.mapper.*;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.LoginRequest;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
class CanonicalUserTest {
 @Test void canonicalUserAndDraftMappingPreserveLegacyDisplay() throws Exception {
  assertEquals("user_account",User.class.getAnnotation(TableName.class).value());
  assertEquals("display_name",User.class.getDeclaredField("name").getAnnotation(TableField.class).value());
  assertEquals("creator_id",TicketDraft.class.getDeclaredField("userId").getAnnotation(TableField.class).value());
  User user=new User();user.setEnabled(true); assertEquals("ACTIVE",user.getStatus());
  user.setStatus("DISABLED");assertFalse(user.getEnabled());
 }
 @Test void knowledgeAdministratorCannotManageAccounts() {
  UserService service=new UserService(mock(UserMapper.class),mock(UserRoleMapper.class),mock(BCryptPasswordEncoder.class),new JwtProperties());
  assertThrows(BizException.class,()->service.listAllAccounts("KNOWLEDGE_ADMIN"));
  assertThrows(BizException.class,()->service.listAllAccounts("KB_ADMIN"));
 }
 @Test void unknownStoredRoleCannotAuthenticateAsEmployee() {
  UserMapper users=mock(UserMapper.class);UserRoleMapper roles=mock(UserRoleMapper.class);BCryptPasswordEncoder passwords=mock(BCryptPasswordEncoder.class);
  User user=new User();user.setUserId("U01");user.setEnabled(true);user.setPasswordHash("hash");
  UserRoleEntity role=new UserRoleEntity();role.setRoleCode("UNKNOWN");
  when(users.selectById("U01")).thenReturn(user);when(roles.selectOne(any())).thenReturn(role);when(passwords.matches("secret","hash")).thenReturn(true);
  LoginRequest request=new LoginRequest();request.setUserId("U01");request.setPassword("secret");
  UserService service=new UserService(users,roles,passwords,new JwtProperties());
  assertThrows(BizException.class,()->service.login(request));
 }
}
