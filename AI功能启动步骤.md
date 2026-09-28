# AI 智能受理功能 · 启动新增步骤

> 在原有启动流程（docker compose 起 MySQL/Nacos → 启动 gateway、user-service、ticket-service → 前端 dev）基础上，
> 增加 AI 问答功能后**需要手动多做的事情**，按顺序执行。

---

## 步骤 1：执行两个新数据库脚本（必做，一次性）

原有 MySQL 容器的 volume 已初始化，**不会自动重跑** `db/init/` 下的新脚本，需手动执行：

```bash
cd it-ticket-cloud

# ① 建 it_ai 库 + 3 张表(ai_knowledge / ai_chat_session / ai_chat_message)
docker exec -i it-ticket-mysql mysql -uroot -proot123 < db/init/30-ai-db.sql

# ② 新增客服角色种子账号 U007 周客服(密码同其他种子账号:123456)
docker exec -i it-ticket-mysql mysql -uroot -proot123 < db/init/12-user-add-customer-service.sql
```

验证：

```bash
docker exec -it it-ticket-mysql mysql -uroot -proot123 -e "SHOW TABLES IN it_ai; SELECT user_id,name,role FROM it_user.user WHERE role='customer_service';"
```

应看到 3 张表和 U007 一行数据。

> 注意：如果之后删 volume 重建容器，两个脚本会随初始化自动执行，无需手动。
> 另外 `11-user-seed.sql` 是 TRUNCATE 重灌的，重跑它之后必须重跑 12 号脚本补 U007。

---

## 步骤 2：配置大模型密钥（可选，不配也能跑）

不配密钥时系统降级运行：AI 回复固定提示语、跳过知识库检索，**但转人工、实时聊天、转工单全流程不受影响**，可先跑通再配。

| 环境变量 | 说明 | 获取 |
|---|---|---|
| `AI_CHAT_API_KEY` | 对话模型密钥（默认 DeepSeek `deepseek-chat`） | platform.deepseek.com |
| `AI_EMBEDDING_API_KEY` | 向量模型密钥（默认硅基流动 `BAAI/bge-m3`，有免费额度） | cloud.siliconflow.cn |

Windows（CMD，启动 ai-service 前设置）：

```cmd
set AI_CHAT_API_KEY=sk-你的key
set AI_EMBEDDING_API_KEY=sk-你的key
```

> 想换供应商/模型：改 `ai-service/src/main/resources/application.yml` 中 `ai.chat.url/model`、`ai.embedding.url/model` 即可（均为 OpenAI 兼容接口）。
> ⚠️ embedding 模型正式使用后**不要中途更换**，否则库内向量需全部重算。

---

## 步骤 3：重新构建后端（多了 ai-service 模块）

父工程已加入 `ai-service` 模块，全量构建一次：

```bash
cd it-ticket-cloud
mvn -DskipTests clean package
```

---

## 步骤 4：多启动一个服务 ai-service（端口 8202）

启动顺序在原有基础上追加 ai-service：

```
gateway(8080) → user-service(8101) → ticket-service(8201) → ai-service(8202)
```

验证：

- Nacos 控制台（http://localhost:8848/nacos）服务列表能看到 `ai-service`
- 网关路由已生效：`http://localhost:8080/api/v1/ai/sessions/mine`（带 token 访问，40100 说明路由通、未登录）

---

## 步骤 5：前端（无需装新依赖）

WebSocket 用的是浏览器原生 API，**没有新增 npm 依赖**，`vite.config.js` 已加好 `/ws` 代理，照常启动即可：

```bash
cd frontend
npm run dev
```

---

## 验收清单（5 分钟走完闭环）

| # | 操作 | 预期 |
|---|---|---|
| 1 | U001 张小明登录 → 「AI 助手」tab 提问 | AI 回复（未配 key 时回复降级提示语） |
| 2 | 点「❌ 未解决，转人工」 | 状态变为"排队等待客服" |
| 3 | 另开浏览器 U007 周客服登录 → 自动进客服工作台 | 队列实时出现该会话（无需刷新） |
| 4 | 客服「接入会话」→ 双方互发消息 | WebSocket 实时收发，无延迟刷新 |
| 5 | 客服点「转工单」→ 选分类生成 | 张小明「我的工单」出现新工单 |
| 6 | 赵工处理完该工单 → 等 ≤10 分钟 | 知识自动回流，再问同类问题 AI 命中并显示 📄 参考资料 |

---

## 常见问题

1. **ai-service 启动报数据库连接失败** → 步骤 1 的 30 号脚本没执行，`it_ai` 库不存在。
2. **登录页没有周客服 / login-options 接口 500 报 NPE** → 老库的 `user.role` 是 ENUM 且不含 `customer_service`，12 号脚本的插入被 MySQL 静默写成空串（INSERT IGNORE 不报错）。执行以下 SQL 修复（新环境重建无此问题，10-user-db.sql 已同步修正）：
   ```sql
   ALTER TABLE it_user.`user`
     MODIFY COLUMN `role` ENUM('employee','engineer','supervisor','customer_service') NOT NULL COMMENT '角色';
   UPDATE it_user.`user` SET role = 'customer_service' WHERE user_id = 'U007';
   ```
3. **AI 回复"暂未配置大模型密钥"** → 正常降级行为，配置步骤 2 的环境变量后重启 ai-service。
4. **转人工后客服队列不实时刷新** → 检查浏览器 DevTools 里 `/ws/ai/chat` 连接是否 101 握手成功；失败多为 gateway 未重启（新路由未加载）。
5. **AI 回答从不引用知识库** → 只有配置了 `AI_EMBEDDING_API_KEY` 才会检索；且知识库需先录入知识或有工单回流。
