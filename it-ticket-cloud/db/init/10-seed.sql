-- Demo seed for a fresh database only; migrations never reseed existing installations.
USE it_ticket_system;
SET NAMES utf8mb4;
SET time_zone = '+00:00';
-- Existing BCrypt hash retained; no plaintext credential added.
INSERT INTO `user`
(user_id,employee_no,name,department_id,identity_source,status,version,password_hash,created_at,updated_at) VALUES
('U_EMP01','E1001','演示员工','D001','SSO','ACTIVE',0,'$2b$10$.PY6iuNnLau97uhjsYug0.OKl8uG66w1Wz/8pl0Sv4g0n.LBKpEn2',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_ENG01','E2001','演示工程师','D002','SSO','ACTIVE',0,'$2b$10$.PY6iuNnLau97uhjsYug0.OKl8uG66w1Wz/8pl0Sv4g0n.LBKpEn2',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_ADM01','E3001','平台管理员','D003','SSO','ACTIVE',0,'$2b$10$.PY6iuNnLau97uhjsYug0.OKl8uG66w1Wz/8pl0Sv4g0n.LBKpEn2',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_KBA01','E4001','知识库管理员','D003','SSO','ACTIVE',0,'$2b$10$.PY6iuNnLau97uhjsYug0.OKl8uG66w1Wz/8pl0Sv4g0n.LBKpEn2',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO user_role (user_id,role_code,granted_by,granted_at,created_at,updated_at) VALUES
('U_EMP01','EMPLOYEE','U_ADM01',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_ENG01','ENGINEER','U_ADM01',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_ADM01','PLATFORM_ADMIN','U_ADM01',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('U_KBA01','KNOWLEDGE_ADMIN','U_ADM01',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO category (category_id,parent_id,ticket_nature,name,level,definition_version,status,version,created_at,updated_at) VALUES
('C_HW',NULL,'INCIDENT','硬件',1,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_HW_PC','C_HW','INCIDENT','台式机/笔记本',2,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_HW_PR','C_HW','INCIDENT','打印机/外设',2,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_SW',NULL,'INCIDENT','软件',1,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_NET',NULL,'INCIDENT','网络',1,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_ACC',NULL,'INCIDENT','账号权限',1,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_OTH',NULL,'INCIDENT','其他',1,'v1','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO support_team (team_id,name,status,version,created_at,updated_at) VALUES
('T_HW','硬件支持组','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('T_SW','软件支持组','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('T_NET','网络支持组','ACTIVE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO team_member (team_id,engineer_id,joined_at,status,created_at,updated_at) VALUES
('T_HW','U_ENG01',UTC_TIMESTAMP(6),'ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('T_SW','U_ENG01',UTC_TIMESTAMP(6),'ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('T_NET','U_ENG01',UTC_TIMESTAMP(6),'ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO category_route (category_id,team_id,route_order,effective_at,created_at,updated_at) VALUES
('C_HW_PC','T_HW',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_HW_PR','T_HW',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_SW','T_SW',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_NET','T_NET',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_ACC','T_SW',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
('C_OTH','T_HW',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO engineer_runtime_state (engineer_id,presence,last_activity_at,version,created_at,updated_at) VALUES
('U_ENG01','AVAILABLE',UTC_TIMESTAMP(6),0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
INSERT INTO service_calendar (calendar_id,timezone,work_week_json,work_intervals_json,lunch_pauses,version,effective_from,created_at,updated_at) VALUES
('DEFAULT','Asia/Shanghai','[1,2,3,4,5]','[{"start":"09:00","end":"12:00"},{"start":"13:00","end":"18:00"}]',1,1,'2026-01-01 00:00:00',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
-- Holidays are administrator-owned configuration, not guessed public-calendar data.
