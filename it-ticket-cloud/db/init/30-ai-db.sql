-- 防止容器初始化时连接字符集为 latin1 导致中文乱码
SET NAMES utf8mb4;
-- ============================================================
-- ai-service 建库建表脚本:AI 智能受理(问答 + 人工客服 + 知识库)
-- 说明:本脚本自带 CREATE DATABASE,新环境随 docker compose 初始化自动执行;
--      已初始化的环境(volume 已存在)请手动执行本脚本。
-- ============================================================

CREATE DATABASE IF NOT EXISTS it_ai
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE it_ai;

-- ------------------------------------------------------------
-- AI 知识库:内部历史工单回流 + 外部文档/手工录入,统一切片存储
-- embedding 存 JSON 数组字符串,数据量小时用 Java 内存算余弦相似度,
-- 后续数据量大可平移到 Milvus/PgVector(只需改 KnowledgeService 一处)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_knowledge (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    title        VARCHAR(255) NOT NULL COMMENT '标题(工单标题或文档名)',
    content      TEXT NOT NULL COMMENT '知识切片文本(问题+解决方案 或 文档片段)',
    source_type  VARCHAR(20) NOT NULL COMMENT '来源:TICKET=历史工单 DOC=外部文档 MANUAL=手工录入',
    source_id    VARCHAR(64) DEFAULT NULL COMMENT '来源标识(工单号或文档名),防重复入库',
    category     VARCHAR(64) DEFAULT NULL COMMENT '分类(硬件/软件/网络/账号/其他)',
    embedding    MEDIUMTEXT COMMENT '向量,JSON数组字符串',
    create_time  DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source_type, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI知识库';

-- ------------------------------------------------------------
-- 咨询会话:AI 解答与人工客服共用一个会话载体,状态机驱动
-- AI_HANDLING → RESOLVED / CLOSED / WAITING_HUMAN
-- WAITING_HUMAN → HUMAN_HANDLING → RESOLVED / TO_TICKET / REJECTED
-- REJECTED 允许员工再次发起(新建会话)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_chat_session (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id       VARCHAR(32) NOT NULL COMMENT '发起员工',
    status        VARCHAR(20) NOT NULL DEFAULT 'AI_HANDLING' COMMENT 'AI_HANDLING/WAITING_HUMAN/HUMAN_HANDLING/RESOLVED/TO_TICKET/REJECTED/CLOSED',
    agent_id      VARCHAR(32) DEFAULT NULL COMMENT '接入的客服ID',
    summary       VARCHAR(500) DEFAULT NULL COMMENT '问题摘要(转人工时生成,供客服快速了解)',
    reject_reason VARCHAR(500) DEFAULT NULL COMMENT '客服驳回原因',
    ticket_id     VARCHAR(32) DEFAULT NULL COMMENT '转工单后的工单号',
    resolved      TINYINT DEFAULT 0 COMMENT '1=员工确认已解决',
    create_time   DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI咨询会话';

-- ------------------------------------------------------------
-- 会话消息:员工提问、AI 回复、人工发言都进这张表,按会话串联
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_chat_message (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id  BIGINT NOT NULL,
    sender_type VARCHAR(10) NOT NULL COMMENT 'USER=员工 AI=机器人 AGENT=人工客服 SYSTEM=系统提示',
    sender_id   VARCHAR(32) DEFAULT NULL COMMENT '发送人ID(AI/SYSTEM 为空)',
    content     TEXT NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话消息';
