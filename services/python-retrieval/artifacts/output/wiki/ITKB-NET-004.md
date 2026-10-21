---
id: "ITKB-NET-004"
title: "DNS解析失败故障排查与处置"
category: "网络连接问题"
department: "IT 部"
effective_date: "2024-03-01"
effective_date_source: "demo-constructed"
version: "v1.0"
replaces: ["ITKB-LEG-NET-004"]
entities: ["DNS", "nslookup", "ipconfig /flushdns", "hosts文件", "DHCP", "UDP 53端口", "阿里DNS(223.5.5.5)", "DNS_PROBE_FINISHED_NXDOMAIN"]
keywords: ["DNS", "打不开网页", "QQ能上", "域名解析", "nslookup", "DNS_PROBE_FINISHED"]
summary: "解决DNS解析失败致网页无法打开（QQ等正常）的问题：清缓存、改DNS、查hosts与代理，并排查公司DNS/DHCP/防火墙。"
meta_source: "llm"
---

# 【NET-004】DNS解析失败故障排查与处置

## 现象描述

- 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/QQ等即时通讯软件可以正常收发消息。ping IP地址通，ping域名不通。

## 常见根因

- ① DNS服务器地址配置错误或被篡改
- ② 公司DNS服务器故障或过载
- ③ DNS缓存污染
- ④ hosts文件被恶意修改
- ⑤ 代理/VPN软件残留的DNS配置

## 员工自助排查

- 步骤1：Win+R → cmd → 输入 nslookup www.baidu.com，观察能否返回IP地址。
- 步骤2：ipconfig /flushdns 清除DNS缓存。
- 步骤3：Win+R → ncpa.cpl → 右键网卡 → 属性 → Internet协议版本4 → DNS改为223.5.5.5（阿里DNS）或公司内部DNS。
- 步骤4：检查 C:\Windows\System32\drivers\etc\hosts 文件，删除可疑条目。
- 步骤5：关闭VPN/代理软件后重试。
- 步骤6：重启电脑。

## IT工程师进阶处理

- 1. 检查公司DNS服务器是否正常运行（nslookup 使用公司 DNS 测试）。
- 2. 检查DHCP下发的DNS地址是否正确。
- 3. 查防火墙是否拦截了DNS（UDP 53端口）。
- 4. 如近期做过DNS迁移，检查旧DNS是否已从所有DHCP作用域中移除。
- 5. 检查是否存在DNS劫持或中间人攻击。

---
> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-004 · 分类「网络连接问题」· 由清洗流水线自动生成
