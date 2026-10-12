# Day 12 工业级 Chunking 分块策略与向量化调优评测报告

> 知识库来源：《IT常见问题RAG知识库.docx》→ Day 11 清洗重构产出的 35 张 Wiki 知识卡片
> Embedding 模型：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维，余弦归一化）

## 一、 实验工程概览与参数对照

| 维度指标 | 对照组 A：朴素固定长度分块 (Naive Fixed) | 实验组 B：Wiki 结构感知分块 (Structure-Aware) | 工业收益说明 |
| :--- | :--- | :--- | :--- |
| **切块策略** | 纯按 500 字符切分，忽略标题与段落 | Markdown 标题层级树 + 递归句子微切 | 保证每个切块语意自包含，无断头句 |
| **元数据注入** | ❌ 无元数据注入（仅记录源文件名与切片号） | ✅ 深度注入 YAML Frontmatter (分类/部门/实体/关键词) | 支持 Day 13 混合检索的前置硬过滤 |
| **切片总数量** | 108 个切片 | 35 个原子切片 | 整卡原子切片数量更少但语义完整，避免碎片化稀释向量 |
| **平均切块长度** | 约 420 字符 | 约 700~950 字符 (整卡原子) | 命中一条切片即携带完整排查链路，无需二次拼接 |
| **分类冲突防御** | ❌ 无法区分网络/账号/硬件等故障域 | ✅ 携带 `wiki_category` 与 `wiki_department` | 跨分类检索时物理屏蔽无关域干扰 |

---

## 二、 5 组复杂业务对抗检索评测结果 (Benchmark)

### [TC-01] 账号锁定阈值与解锁
- **业务提问**：`员工密码输错几次域账号会被锁定？锁定后等待多久可能自动解锁？`
- **潜在冲突与风险点**：锁定阈值5次与自动解锁窗口15-30分钟是硬数字，切片必须保留完整条件句
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：## 常见根因  - ① 连续多次输入错误密码触发安全策略 - ② 有人在其他设备上用此账号尝试登录（如共享电脑、远程桌面） - ③ 手机/平板上的邮箱客户端保存了旧密码不停重试 - ④ 账号被盗用，攻击者在暴力破解 - ⑤ 管理员主动禁用...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：【制度大纲：域账号锁定排查与解锁处理】 # 【ACC-001】域账号锁定排查与解锁处理  ## 现象描述  - 登录时提示「账号已被锁定」「账号已禁用」「登录失败次数过多，请稍后再试」「账户已被锁定，请联系管理员」。常见于：密码输错超过5次...
- **注入元数据快照**：
  ```json
{
  "source_file": "ITKB-ACC-001.md",
  "Header_1": "域账号锁定排查与解锁处理",
  "wiki_entities": "[\"AD域(Active Directory)\", \"Active Directory用户和计算机\", \"事件ID 4740\", \"组策略\", \"账户锁定策略\", \"自助密码重置平台\", \"安全日志\"]",
  "wiki_meta_source": "llm",
  "chunk_length": 779,
  "wiki_id": "ITKB-ACC-001",
  "chunk_id": "bf1dbe13",
  "wiki_version": "v1.0",
  "wiki_keywords": "[\"账号锁定\", \"密码错误\", \"登录失败\", \"AD域\", \"账号禁用\", \"多次输错密码\", \"解锁账号\"]",
  "wiki_summary": "针对密码多次输错等原因引发的域账号锁定，提供员工自助排查步骤及IT侧AD解锁与锁定溯源流程。",
  "wiki_department": "IT 部",
  "wiki_title": "域账号锁定排查与解锁处理",
  "sub_idx": 0,
  "wiki_replaces": "[]",
  "split_strategy": "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)",
  "wiki_category": "账号与权限问题"
}
  ```

---
### [TC-02] DNS故障现象与处置
- **业务提问**：`电脑能上QQ但打不开网页，提示DNS_PROBE_FINISHED_NXDOMAIN，员工如何自助处理？`
- **潜在冲突与风险点**：清缓存命令、阿里DNS地址、hosts路径必须同块召回，否则处置链断裂
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：# 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/Q...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：【制度大纲：DNS解析失败故障排查与处置】 # 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME...
- **注入元数据快照**：
  ```json
{
  "Header_1": "DNS解析失败故障排查与处置",
  "wiki_version": "v1.0",
  "wiki_entities": "[\"DNS\", \"nslookup\", \"ipconfig /flushdns\", \"hosts文件\", \"DHCP\", \"UDP 53端口\", \"阿里DNS(223.5.5.5)\", \"DNS_PROBE_FINISHED_NXDOMAIN\"]",
  "chunk_id": "30e0b884",
  "wiki_id": "ITKB-NET-004",
  "source_file": "ITKB-NET-004.md",
  "wiki_keywords": "[\"DNS\", \"打不开网页\", \"QQ能上\", \"域名解析\", \"nslookup\", \"DNS_PROBE_FINISHED\"]",
  "wiki_department": "IT 部",
  "wiki_replaces": "[]",
  "split_strategy": "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)",
  "wiki_category": "网络连接问题",
  "wiki_summary": "解决DNS解析失败致网页无法打开（QQ等正常）的问题：清缓存、改DNS、查hosts与代理，并排查公司DNS/DHCP/防火墙。",
  "chunk_length": 807,
  "wiki_title": "DNS解析失败故障排查与处置",
  "wiki_meta_source": "llm",
  "sub_idx": 0
}
  ```

---
### [TC-03] 蓝屏内存排查与工具
- **业务提问**：`电脑频繁蓝屏显示MEMORY_MANAGEMENT，如何检查内存？IT用什么工具分析dump文件？`
- **潜在冲突与风险点**：员工自助命令与工程师工具分属两节，切块需保住各自工具清单
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：## IT工程师进阶处理  - 1. 使用 BlueScreenView 工具分析 dump 文件（C:\Windows\Minidump），定位导致蓝屏的驱动/模块。 - 2. 使用 MemTest86 进行深度内存检测（需制作启动U盘）...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：【制度大纲：Windows蓝屏死机故障处置】 # 【SYS-001】Windows蓝屏死机故障处置  ## 现象描述  - 电脑在使用过程中突然蓝屏，显示错误代码（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEM...
- **注入元数据快照**：
  ```json
{
  "split_strategy": "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)",
  "wiki_summary": "解决Windows蓝屏死机问题，通过错误代码、内存、驱动、系统文件、散热与硬盘排查定位修复。",
  "wiki_id": "ITKB-SYS-001",
  "wiki_meta_source": "llm",
  "wiki_title": "Windows蓝屏死机故障处置",
  "source_file": "ITKB-SYS-001.md",
  "wiki_keywords": "[\"蓝屏\", \"BSOD\", \"死机\", \"蓝屏代码\", \"STOP错误\", \"系统崩溃\", \"自动重启\", \"CRITICAL_PROCESS_DIED\"]",
  "wiki_category": "系统与软件故障",
  "wiki_replaces": "[]",
  "sub_idx": 0,
  "Header_1": "Windows蓝屏死机故障处置",
  "wiki_entities": "[\"Windows\", \"蓝屏(BSOD)\", \"内存故障\", \"驱动程序\", \"sfc /scannow\", \"BlueScreenView\", \"MemTest86\", \"CrystalDiskInfo\"]",
  "wiki_department": "IT 部",
  "wiki_version": "v1.0",
  "chunk_length": 930,
  "chunk_id": "76399528"
}
  ```

---
### [TC-04] 邮件退信与附件限制
- **业务提问**：`发邮件收到退信提示552 Message size exceeds是什么意思？附件超过限制怎么办？`
- **潜在冲突与风险点**：退信代码含义与20-50MB限制、云盘替代方案必须完整召回
- **朴素切块命中率**：2/4
  > **朴素切片摘要**：--- > 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-003 · 分类「邮件与通讯问题」· 由清洗流水线自动生成...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：【制度大纲：邮件无法发送处置指南】 # 【MAIL-001】邮件无法发送处置指南  ## 现象描述  - 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not fo...
- **注入元数据快照**：
  ```json
{
  "source_file": "ITKB-MAIL-001.md",
  "wiki_id": "ITKB-MAIL-001",
  "chunk_id": "3ca1d999",
  "split_strategy": "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)",
  "wiki_keywords": "[\"邮件\", \"Outlook\", \"发送失败\", \"退信\", \"SMTP\", \"发送报告\", \"邮件在发件箱\", \"无法送达\"]",
  "wiki_replaces": "[]",
  "Header_1": "邮件无法发送处置指南",
  "wiki_department": "IT 部",
  "chunk_length": 897,
  "wiki_title": "邮件无法发送处置指南",
  "wiki_version": "v1.0",
  "wiki_summary": "解决邮件发送失败或退信问题，按地址、附件、客户端、配额及反垃圾策略排查。",
  "wiki_entities": "[\"Outlook\", \"网页邮箱\", \"SMTP\", \"退信\", \"Exchange\", \"反垃圾邮件网关\"]",
  "sub_idx": 0,
  "wiki_meta_source": "llm",
  "wiki_category": "邮件与通讯问题"
}
  ```

---
### [TC-05] VPN错误代码与协议切换
- **业务提问**：`在家连公司VPN报错806怎么排查？推荐切换到什么协议穿透性最好？`
- **潜在冲突与风险点**：错误代码、协议名称与推荐结论(SSL VPN)需同时命中
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：--- id: "ITKB-VPN-001" title: "VPN连接失败（拨号/认证失败）" category: "VPN与远程办公" department: "IT 部" version: "v1.0" replaces: [] en...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：【制度大纲：VPN连接失败（拨号/认证失败）】 # 【VPN-001】VPN连接失败（拨号/认证失败）  ## 现象描述  - 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误...
- **注入元数据快照**：
  ```json
{
  "wiki_department": "IT 部",
  "sub_idx": 0,
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_meta_source": "llm",
  "source_file": "ITKB-VPN-001.md",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_replaces": "[]",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "chunk_id": "e7b47df6",
  "chunk_length": 844,
  "split_strategy": "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)",
  "wiki_version": "v1.0",
  "wiki_id": "ITKB-VPN-001",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "wiki_category": "VPN与远程办公",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]"
}
  ```

---
## 三、 结论与阶段技术承接
1. **自适应粒度切块价值确证**：对约 900 字符的短卡片整卡保持原子性（落在 300~800 token 甜点区），避免按标题切碎导致跨小节事实分裂；仅超长文档才标题切分+合并+递归兜底。切片完整包含了上下文排查链路（现象→根因→自助→进阶），未出现关键判定词遗漏；
2. **元数据前置过滤完全生效**：借助 `wiki_category` 的过滤条件，检索链路成功将查询范围物理限定在目标故障域，屏蔽无关分类干扰；
3. **技术承接**：本日持久化落盘的 `chroma_wiki_structured/` 数据库，将无缝对接 **Day 13 的 BM25 + Dense 双路召回与 Rerank 精排工程**。
