# 父子切块演示——真实切块结果

> 演示卡片：`ITKB-VPN-001.md`　生成时间：2026-10-28 17:47
> 配置：child_size=512｜section_header_level=H2｜merge_preamble=True｜boost_injection=first｜breadcrumb_header=True｜strip_trace_tail=True

## 0. 输入：原始 Wiki 卡片

```markdown
---
id: "ITKB-VPN-001"
title: "VPN连接失败（拨号/认证失败）"
category: "VPN与远程办公"
department: "IT 部"
effective_date: "2024-03-01"
effective_date_source: "demo-constructed"
version: "v1.0"
replaces: ["ITKB-LEG-VPN-001"]
entities: ["VPN", "SSL VPN", "L2TP", "IPSec", "PPTP", "IKEv2", "AD账号", "预共享密钥"]
keywords: ["VPN", "远程办公", "拨号", "连接失败", "认证失败", "L2TP", "SSL VPN", "在家办公"]
summary: "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。"
meta_source: "llm"
---

# 【VPN-001】VPN连接失败（拨号/认证失败）

## 现象描述

- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、691。

## 常见根因

- ① 家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）
- ② VPN客户端配置错误（服务器地址、预共享密钥）
- ③ 用户名密码错误或AD账号被锁定
- ④ 运营商网络NAT穿透问题
- ⑤ VPN服务器端故障或并发连接数已满
- ⑥ 证书过期（SSL VPN）

## 员工自助排查

- 步骤1：检查本地网络是否能正常上网（浏览器打开百度测试）。
- 步骤2：尝试手机热点连接——如果热点可以但家庭宽带不行，说明是家庭路由器/宽带问题。
- 步骤3：重启家用路由器和电脑。
- 步骤4：确认VPN服务器地址和密钥配置正确（对照公司VPN配置文档）。
- 步骤5：尝试切换VPN协议（如从L2TP切换到SSL VPN，或从SSL VPN切换到IKEv2）。
- 步骤6：关闭Windows防火墙和第三方杀毒软件临时测试。

## IT工程师进阶处理

- 1. 检查VPN服务器状态：CPU、内存、并发连接数、带宽占用。
- 2. 检查防火墙策略：确保VPN协议端口（UDP 500/4500、TCP 443等）在边界防火墙上放行。
- 3. 检查用户AD账号状态（是否锁定、密码是否过期）。
- 4. 查看VPN服务器日志，定位具体拒绝原因。
- 5. 为用户切换VPN协议或更新客户端配置。
- 6. 推荐使用SSL VPN（基于HTTPS，穿透性最好，不易被酒店/咖啡厅WiFi阻断）。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-001 · 分类「VPN与远程办公」· 由清洗流水线自动生成
```

---

## 1. 父块（整卡正文，最终交给 LLM 的上下文）

- `parent_id`：`ITKB-VPN-001`
- `chunk_role`：`parent`
- 正文长度：820 字符（= 剥离 frontmatter 后的全文，含溯源尾）

```markdown
# 【VPN-001】VPN连接失败（拨号/认证失败）

## 现象描述

- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、691。

## 常见根因

- ① 家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）
- ② VPN客户端配置错误（服务器地址、预共享密钥）
- ③ 用户名密码错误或AD账号被锁定
- ④ 运营商网络NAT穿透问题
- ⑤ VPN服务器端故障或并发连接数已满
- ⑥ 证书过期（SSL VPN）

## 员工自助排查

- 步骤1：检查本地网络是否能正常上网（浏览器打开百度测试）。
- 步骤2：尝试手机热点连接——如果热点可以但家庭宽带不行，说明是家庭路由器/宽带问题。
- 步骤3：重启家用路由器和电脑。
- 步骤4：确认VPN服务器地址和密钥配置正确（对照公司VPN配置文档）。
- 步骤5：尝试切换VPN协议（如从L2TP切换到SSL VPN，或从SSL VPN切换到IKEv2）。
- 步骤6：关闭Windows防火墙和第三方杀毒软件临时测试。

## IT工程师进阶处理

- 1. 检查VPN服务器状态：CPU、内存、并发连接数、带宽占用。
- 2. 检查防火墙策略：确保VPN协议端口（UDP 500/4500、TCP 443等）在边界防火墙上放行。
- 3. 检查用户AD账号状态（是否锁定、密码是否过期）。
- 4. 查看VPN服务器日志，定位具体拒绝原因。
- 5. 为用户切换VPN协议或更新客户端配置。
- 6. 推荐使用SSL VPN（基于HTTPS，穿透性最好，不易被酒店/咖啡厅WiFi阻断）。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-001 · 分类「VPN与远程办公」· 由清洗流水线自动生成
```

---

## 2. 子块（共 4 个，向量匹配单元）

| # | child_id | 所属小节 Header_2 | 长度 | 含检索增强行 | 开头预览 |
|---|---|---|---|---|---|
| 0 | `ITKB-VPN-001#c0` | 现象描述 | 253 | 否 | 【卡片：VPN连接失败（拨号/认证失败） > 现象描述】 【检索增强：关键词 V… |
| 1 | `ITKB-VPN-001#c1` | 常见根因 | 186 | 否 | 【卡片：VPN连接失败（拨号/认证失败） > 常见根因】 ## 常见根因 - ①… |
| 2 | `ITKB-VPN-001#c2` | 员工自助排查 | 261 | 否 | 【卡片：VPN连接失败（拨号/认证失败） > 员工自助排查】 ## 员工自助排查… |
| 3 | `ITKB-VPN-001#c3` | IT工程师进阶处理 | 269 | 否 | 【卡片：VPN连接失败（拨号/认证失败） > IT工程师进阶处理】 ## IT工… |

### 每个子块的完整内容与 metadata

#### 子块 0：`ITKB-VPN-001#c0`

**完整 metadata（与 chroma.sqlite3 中存储的逐字段一致，已解耦剥离 parent_content，轻量化入库）：**

```json
{
  "wiki_id": "ITKB-VPN-001",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_category": "VPN与远程办公",
  "wiki_department": "IT 部",
  "wiki_effective_date": "2024-03-01",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_version": "v1.0",
  "wiki_replaces": "[\"ITKB-LEG-VPN-001\"]",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]",
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "wiki_meta_source": "llm",
  "wiki_status": "现行",
  "source_file": "ITKB-VPN-001.md",
  "parent_id": "ITKB-VPN-001",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "Header_2": "现象描述",
  "chunk_role": "child",
  "child_idx": 0,
  "child_id": "ITKB-VPN-001#c0",
  "chunk_length": 253,
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)"
}
```

- 要点：`parent_id` 作为外键指向 MySQL Docstore（`rag_parent_docstore` 表），向量库不存父块全文；`wiki_status` 等字段供检索时元数据硬过滤（剔除已废止卡）

**实际参与向量化的文本（含上下文头）：**

```markdown
【卡片：VPN连接失败（拨号/认证失败） > 现象描述】
【检索增强：关键词 VPN、远程办公、拨号、连接失败、认证失败、L2TP、SSL VPN、在家办公｜实体 VPN、SSL VPN、L2TP、IPSec、PPTP、IKEv2、AD账号、预共享密钥】
# 【VPN-001】VPN连接失败（拨号/认证失败）

## 现象描述

- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、691。
```

#### 子块 1：`ITKB-VPN-001#c1`

**完整 metadata（与 chroma.sqlite3 中存储的逐字段一致，已解耦剥离 parent_content，轻量化入库）：**

```json
{
  "wiki_id": "ITKB-VPN-001",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_category": "VPN与远程办公",
  "wiki_department": "IT 部",
  "wiki_effective_date": "2024-03-01",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_version": "v1.0",
  "wiki_replaces": "[\"ITKB-LEG-VPN-001\"]",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]",
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "wiki_meta_source": "llm",
  "wiki_status": "现行",
  "source_file": "ITKB-VPN-001.md",
  "parent_id": "ITKB-VPN-001",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "Header_2": "常见根因",
  "chunk_role": "child",
  "child_idx": 1,
  "child_id": "ITKB-VPN-001#c1",
  "chunk_length": 186,
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)"
}
```

- 要点：`parent_id` 作为外键指向 MySQL Docstore（`rag_parent_docstore` 表），向量库不存父块全文；`wiki_status` 等字段供检索时元数据硬过滤（剔除已废止卡）

**实际参与向量化的文本（含上下文头）：**

```markdown
【卡片：VPN连接失败（拨号/认证失败） > 常见根因】
## 常见根因

- ① 家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）
- ② VPN客户端配置错误（服务器地址、预共享密钥）
- ③ 用户名密码错误或AD账号被锁定
- ④ 运营商网络NAT穿透问题
- ⑤ VPN服务器端故障或并发连接数已满
- ⑥ 证书过期（SSL VPN）
```

#### 子块 2：`ITKB-VPN-001#c2`

**完整 metadata（与 chroma.sqlite3 中存储的逐字段一致，已解耦剥离 parent_content，轻量化入库）：**

```json
{
  "wiki_id": "ITKB-VPN-001",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_category": "VPN与远程办公",
  "wiki_department": "IT 部",
  "wiki_effective_date": "2024-03-01",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_version": "v1.0",
  "wiki_replaces": "[\"ITKB-LEG-VPN-001\"]",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]",
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "wiki_meta_source": "llm",
  "wiki_status": "现行",
  "source_file": "ITKB-VPN-001.md",
  "parent_id": "ITKB-VPN-001",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "Header_2": "员工自助排查",
  "chunk_role": "child",
  "child_idx": 2,
  "child_id": "ITKB-VPN-001#c2",
  "chunk_length": 261,
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)"
}
```

- 要点：`parent_id` 作为外键指向 MySQL Docstore（`rag_parent_docstore` 表），向量库不存父块全文；`wiki_status` 等字段供检索时元数据硬过滤（剔除已废止卡）

**实际参与向量化的文本（含上下文头）：**

```markdown
【卡片：VPN连接失败（拨号/认证失败） > 员工自助排查】
## 员工自助排查

- 步骤1：检查本地网络是否能正常上网（浏览器打开百度测试）。
- 步骤2：尝试手机热点连接——如果热点可以但家庭宽带不行，说明是家庭路由器/宽带问题。
- 步骤3：重启家用路由器和电脑。
- 步骤4：确认VPN服务器地址和密钥配置正确（对照公司VPN配置文档）。
- 步骤5：尝试切换VPN协议（如从L2TP切换到SSL VPN，或从SSL VPN切换到IKEv2）。
- 步骤6：关闭Windows防火墙和第三方杀毒软件临时测试。
```

#### 子块 3：`ITKB-VPN-001#c3`

**完整 metadata（与 chroma.sqlite3 中存储的逐字段一致，已解耦剥离 parent_content，轻量化入库）：**

```json
{
  "wiki_id": "ITKB-VPN-001",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_category": "VPN与远程办公",
  "wiki_department": "IT 部",
  "wiki_effective_date": "2024-03-01",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_version": "v1.0",
  "wiki_replaces": "[\"ITKB-LEG-VPN-001\"]",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]",
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "wiki_meta_source": "llm",
  "wiki_status": "现行",
  "source_file": "ITKB-VPN-001.md",
  "parent_id": "ITKB-VPN-001",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "Header_2": "IT工程师进阶处理",
  "chunk_role": "child",
  "child_idx": 3,
  "child_id": "ITKB-VPN-001#c3",
  "chunk_length": 269,
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)"
}
```

- 要点：`parent_id` 作为外键指向 MySQL Docstore（`rag_parent_docstore` 表），向量库不存父块全文；`wiki_status` 等字段供检索时元数据硬过滤（剔除已废止卡）

**实际参与向量化的文本（含上下文头）：**

```markdown
【卡片：VPN连接失败（拨号/认证失败） > IT工程师进阶处理】
## IT工程师进阶处理

- 1. 检查VPN服务器状态：CPU、内存、并发连接数、带宽占用。
- 2. 检查防火墙策略：确保VPN协议端口（UDP 500/4500、TCP 443等）在边界防火墙上放行。
- 3. 检查用户AD账号状态（是否锁定、密码是否过期）。
- 4. 查看VPN服务器日志，定位具体拒绝原因。
- 5. 为用户切换VPN协议或更新客户端配置。
- 6. 推荐使用SSL VPN（基于HTTPS，穿透性最好，不易被酒店/咖啡厅WiFi阻断）。
```
