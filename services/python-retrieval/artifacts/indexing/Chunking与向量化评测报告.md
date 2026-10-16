# Chunking 分块策略与向量化评测报告

> 知识库来源：《IT常见问题RAG知识库.docx》→ 清洗重构产出的 38 张 Wiki 知识卡片
> Embedding 模型：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维，余弦归一化）

## 一、 实验工程概览与参数对照

| 维度指标 | 对照组 A：朴素固定长度分块 (Naive Fixed) | 实验组 B：父子切片 (Parent-Child / Small-to-Big) | 工业收益说明 |
| :--- | :--- | :--- | :--- |
| **切块策略** | 纯按 500 字符切分，忽略标题与段落 | H2 语义边界分节 + 512 字符行累加子块 + 差异化上下文头 | 保证每个切块语意自包含，无断头句、不断裂跨节事实 |
| **元数据注入** | ❌ 无元数据注入（仅记录源文件名与切片号） | ✅ 深度注入 YAML Frontmatter (`wiki_category`/`wiki_status`/`Header_2`) | 支持混合检索的前置硬过滤与废止卡屏蔽 |
| **切片总数量** | 115 个切片 | 144 个匹配子块（对应 38 张完整父卡） | 匹配用细粒度子块保障向量聚焦，生成用完整父卡保障上下文 |
| **平均切块长度** | 约 370 字符 | 子块平均 232 字符（命中后回溯父卡全文 ~750 字符） | 命中子块后经 `expand_to_parents` 零成本回溯完整排查链路 |
| **分类冲突防御** | ❌ 无法区分网络/账号/硬件等故障域 | ✅ 携带 `wiki_category`、`wiki_department` 与 `wiki_status` | 跨分类检索时物理屏蔽无关域与废止卡干扰 |

---

## 二、 5 组复杂业务对抗检索评测结果 (Benchmark)

### [TC-01] 账号锁定阈值与解锁
- **业务提问**：`员工密码输错几次域账号会被锁定？锁定后等待多久可能自动解锁？`
- **潜在冲突与风险点**：锁定阈值5次与自动解锁窗口15-30分钟是硬数字，切片必须保留完整条件句
- **朴素切块命中率**：3/4
  > **朴素切片摘要**：## 现象描述  - 登录时提示「账号已被锁定」「登录失败次数过多」。  ## 常见根因  - ① 连续多次输入错误密码触发旧版安全策略 - ② 恶意软件暴力破解尝试  ## 员工自助排查（已废止）  - 步骤1：连续输错 3 次密码即触发...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【LEG-ACC-001】域账号锁定处理（旧版·宽松策略，已废止）  > ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留。  ...
- **注入元数据快照**：
  ```json
{
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "wiki_version": "v0.9",
  "wiki_keywords": "[\"账号锁定\", \"密码错误\", \"登录失败\", \"AD域\", \"账号禁用\", \"多次输错密码\", \"解锁账号\", \"4740\"]",
  "child_id": "ITKB-LEG-ACC-001#c2",
  "parent_content": "# 【LEG-ACC-001】域账号锁定处理（旧版·宽松策略，已废止）\n\n> ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留。\n\n## 现象描述\n\n- 登录时提示「账号已被锁定」「登录失败次数过多」。\n\n## 常见根因\n\n- ① 连续多次输入错误密码触发旧版安全策略\n- ② 恶意软件暴力破解尝试\n\n## 员工自助排查（已废止）\n\n- 步骤1：连续输错 3 次密码即触发锁定（现行标准已调整为 5 次）。\n- 步骤2：锁定后不会自动解锁，必须人工联系IT解锁（现行标准已调整为等待 15-30 分钟自动解锁）。\n- 步骤3：员工无需等待，立即电话IT支持。\n\n## IT工程师进阶处理（已废止）\n\n- 1. 在安全日志中筛选旧版锁定事件进行溯源。\n- 2. 记录发生锁定的来源设备。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 旧版条目 · 分类「账号与权限问题」· v0.9 已废止，保留仅供版本冲突溯源\n",
  "Header_2": "员工自助排查（已废止）",
  "wiki_summary": "（已废止，v1.0 版 ITKB-ACC-001 为准）旧版宽松锁定策略：3 次锁定、不自动解锁，与现行 5 次/15-30分钟策略冲突。",
  "child_idx": 2,
  "source_file": "ITKB-LEG-ACC-001.md",
  "wiki_category": "账号与权限问题",
  "parent_id": "ITKB-LEG-ACC-001",
  "wiki_title": "域账号锁定处理（旧版·宽松策略，已废止）",
  "Header_1": "域账号锁定处理（旧版·宽松策略，已废止）",
  "chunk_role": "child",
  "wiki_department": "IT 部",
  "wiki_status": "已废止",
  "wiki_replaces": "[]",
  "wiki_entities": "[\"AD域\", \"账号锁定\", \"密码错误\", \"解锁账号\", \"安全日志\", \"4740\"]",
  "wiki_id": "ITKB-LEG-ACC-001",
  "wiki_meta_source": "rule",
  "chunk_length": 170
}
  ```

---
### [TC-02] DNS故障现象与处置
- **业务提问**：`电脑能上QQ但打不开网页，提示DNS_PROBE_FINISHED_NXDOMAIN，员工如何自助处理？`
- **潜在冲突与风险点**：清缓存命令、阿里DNS地址、hosts路径必须同块召回，否则处置链断裂
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：# 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/Q...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/Q...
- **注入元数据快照**：
  ```json
{
  "Header_1": "DNS解析失败故障排查与处置",
  "chunk_length": 347,
  "wiki_category": "网络连接问题",
  "wiki_entities": "[\"DNS\", \"nslookup\", \"ipconfig /flushdns\", \"hosts文件\", \"DHCP\", \"UDP 53端口\", \"阿里DNS(223.5.5.5)\", \"DNS_PROBE_FINISHED_NXDOMAIN\"]",
  "child_idx": 0,
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "Header_2": "现象描述",
  "wiki_summary": "解决DNS解析失败致网页无法打开（QQ等正常）的问题：清缓存、改DNS、查hosts与代理，并排查公司DNS/DHCP/防火墙。",
  "wiki_version": "v1.0",
  "child_id": "ITKB-NET-004#c0",
  "source_file": "ITKB-NET-004.md",
  "wiki_replaces": "[]",
  "wiki_keywords": "[\"DNS\", \"打不开网页\", \"QQ能上\", \"域名解析\", \"nslookup\", \"DNS_PROBE_FINISHED\"]",
  "parent_id": "ITKB-NET-004",
  "parent_content": "# 【NET-004】DNS解析失败故障排查与处置\n\n## 现象描述\n\n- 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/QQ等即时通讯软件可以正常收发消息。ping IP地址通，ping域名不通。\n\n## 常见根因\n\n- ① DNS服务器地址配置错误或被篡改\n- ② 公司DNS服务器故障或过载\n- ③ DNS缓存污染\n- ④ hosts文件被恶意修改\n- ⑤ 代理/VPN软件残留的DNS配置\n\n## 员工自助排查\n\n- 步骤1：Win+R → cmd → 输入 nslookup www.baidu.com，观察能否返回IP地址。\n- 步骤2：ipconfig /flushdns 清除DNS缓存。\n- 步骤3：Win+R → ncpa.cpl → 右键网卡 → 属性 → Internet协议版本4 → DNS改为223.5.5.5（阿里DNS）或公司内部DNS。\n- 步骤4：检查 C:\\Windows\\System32\\drivers\\etc\\hosts 文件，删除可疑条目。\n- 步骤5：关闭VPN/代理软件后重试。\n- 步骤6：重启电脑。\n\n## IT工程师进阶处理\n\n- 1. 检查公司DNS服务器是否正常运行（nslookup 使用公司 DNS 测试）。\n- 2. 检查DHCP下发的DNS地址是否正确。\n- 3. 查防火墙是否拦截了DNS（UDP 53端口）。\n- 4. 如近期做过DNS迁移，检查旧DNS是否已从所有DHCP作用域中移除。\n- 5. 检查是否存在DNS劫持或中间人攻击。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-004 · 分类「网络连接问题」· 由清洗流水线自动生成\n",
  "wiki_meta_source": "llm",
  "wiki_title": "DNS解析失败故障排查与处置",
  "chunk_role": "child",
  "wiki_department": "IT 部",
  "wiki_status": "现行",
  "wiki_id": "ITKB-NET-004"
}
  ```

---
### [TC-03] 蓝屏内存排查与工具
- **业务提问**：`电脑频繁蓝屏显示MEMORY_MANAGEMENT，如何检查内存？IT用什么工具分析dump文件？`
- **潜在冲突与风险点**：员工自助命令与工程师工具分属两节，切块需保住各自工具清单
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：## IT工程师进阶处理  - 1. 使用 BlueScreenView 工具分析 dump 文件（C:\Windows\Minidump），定位导致蓝屏的驱动/模块。 - 2. 使用 MemTest86 进行深度内存检测（需制作启动U盘）...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【SYS-001】Windows蓝屏死机故障处置  ## 现象描述  - 电脑在使用过程中突然蓝屏，显示错误代码（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEMENT、DRIVER_IRQL_NOT_LES...
- **注入元数据快照**：
  ```json
{
  "wiki_version": "v1.0",
  "child_id": "ITKB-SYS-001#c0",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "wiki_department": "IT 部",
  "wiki_meta_source": "llm",
  "source_file": "ITKB-SYS-001.md",
  "wiki_replaces": "[]",
  "chunk_role": "child",
  "chunk_length": 349,
  "wiki_summary": "解决Windows蓝屏死机问题，通过错误代码、内存、驱动、系统文件、散热与硬盘排查定位修复。",
  "wiki_id": "ITKB-SYS-001",
  "parent_id": "ITKB-SYS-001",
  "wiki_category": "系统与软件故障",
  "child_idx": 0,
  "Header_1": "Windows蓝屏死机故障处置",
  "wiki_entities": "[\"Windows\", \"蓝屏(BSOD)\", \"内存故障\", \"驱动程序\", \"sfc /scannow\", \"BlueScreenView\", \"MemTest86\", \"CrystalDiskInfo\"]",
  "wiki_keywords": "[\"蓝屏\", \"BSOD\", \"死机\", \"蓝屏代码\", \"STOP错误\", \"系统崩溃\", \"自动重启\", \"CRITICAL_PROCESS_DIED\"]",
  "wiki_title": "Windows蓝屏死机故障处置",
  "Header_2": "现象描述",
  "parent_content": "# 【SYS-001】Windows蓝屏死机故障处置\n\n## 现象描述\n\n- 电脑在使用过程中突然蓝屏，显示错误代码（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEMENT、DRIVER_IRQL_NOT_LESS_OR_EQUAL 等），随后自动重启。或电脑完全卡死，鼠标键盘无响应，只能长按电源键强制关机。\n\n## 常见根因\n\n- ① 内存故障（接触不良、金手指氧化、内存条损坏）\n- ② 驱动程序不兼容（特别是显卡驱动、网卡驱动）\n- ③ 系统文件损坏（非正常关机导致）\n- ④ 散热不良导致CPU/显卡过热保护\n- ⑤ 硬盘坏道或SSD固件问题\n- ⑥ 软件冲突（杀毒软件、系统优化工具）\n\n## 员工自助排查\n\n- 步骤1：重启电脑。如果频繁蓝屏，记录下蓝屏错误代码（拍照保存）。\n- 步骤2：Win+R → 输入 mdsched.exe → 选择「立即重新启动并检查内存问题」进行内存诊断。\n- 步骤3：检查电脑散热口是否被遮挡，风扇是否正常运转。\n- 步骤4：Win+I → Windows更新 → 检查并安装所有待处理的更新。\n- 步骤5：如果有最近安装的软件/驱动，尝试卸载后观察。\n- 步骤6：Win+R → cmd（管理员） → sfc /scannow 扫描修复系统文件。\n\n## IT工程师进阶处理\n\n- 1. 使用 BlueScreenView 工具分析 dump 文件（C:\\Windows\\Minidump），定位导致蓝屏的驱动/模块。\n- 2. 使用 MemTest86 进行深度内存检测（需制作启动U盘）。\n- 3. 使用 CrystalDiskInfo 检查硬盘健康状态（SMART数据）。\n- 4. 进入安全模式卸载可疑驱动/软件。\n- 5. 检查系统事件查看器（eventvwr.msc）→ Windows日志 → 系统，筛选关键错误。\n- 6. 如确认为硬件故障，协调更换内存/硬盘，或整机返修。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 SYS-001 · 分类「系统与软件故障」· 由清洗流水线自动生成\n",
  "wiki_status": "现行"
}
  ```

---
### [TC-04] 邮件退信与附件限制
- **业务提问**：`发邮件收到退信提示552 Message size exceeds是什么意思？附件超过限制怎么办？`
- **潜在冲突与风险点**：退信代码含义与20-50MB限制、云盘替代方案必须完整召回
- **朴素切块命中率**：2/4
  > **朴素切片摘要**：--- > 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-003 · 分类「邮件与通讯问题」· 由清洗流水线自动生成...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【MAIL-001】邮件无法发送处置指南  ## 现象描述  - 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message s...
- **注入元数据快照**：
  ```json
{
  "wiki_entities": "[\"Outlook\", \"网页邮箱\", \"SMTP\", \"退信\", \"Exchange\", \"反垃圾邮件网关\"]",
  "wiki_version": "v1.0",
  "Header_1": "邮件无法发送处置指南",
  "wiki_id": "ITKB-MAIL-001",
  "child_id": "ITKB-MAIL-001#c0",
  "wiki_department": "IT 部",
  "wiki_title": "邮件无法发送处置指南",
  "wiki_status": "现行",
  "wiki_replaces": "[]",
  "wiki_summary": "解决邮件发送失败或退信问题，按地址、附件、客户端、配额及反垃圾策略排查。",
  "wiki_category": "邮件与通讯问题",
  "wiki_meta_source": "llm",
  "parent_content": "# 【MAIL-001】邮件无法发送处置指南\n\n## 现象描述\n\n- 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message size exceeds」「554 Rejected」。\n\n## 常见根因\n\n- ① 收件人邮箱地址写错（拼写错误、用户不存在）\n- ② 附件超过大小限制（公司邮箱通常限制20-50MB）\n- ③ SMTP服务器无响应或被防火墙拦截\n- ④ 邮箱已满（达到存储配额上限）\n- ⑤ 邮件被反垃圾邮件策略拦截（内容含敏感词或可疑链接）\n- ⑥ Outlook离线模式误开启\n\n## 员工自助排查\n\n- 步骤1：检查收件人地址拼写，确认无误后重发。\n- 步骤2：检查附件大小，超过限制的用云盘链接替代（如 OneDrive / 公司内部云盘）。\n- 步骤3：Outlook → 发送/接收 → 确认「脱机工作」未被选中。\n- 步骤4：登录网页版邮箱测试发送是否正常——如果网页版正常，说明是Outlook客户端问题。\n- 步骤5：清理邮箱，删除不需要的旧邮件，清空已删除邮件和垃圾邮件文件夹。\n- 步骤6：暂时关闭杀毒软件邮件扫描功能测试。\n\n## IT工程师进阶处理\n\n- 1. 检查邮件服务器SMTP日志，定位拒绝原因。\n- 2. 检查用户邮箱配额：Exchange管理后台 → 邮箱使用情况 → 提高配额或归档旧邮件。\n- 3. 反垃圾邮件网关：检查该邮件是否被误判为垃圾邮件，添加到白名单。\n- 4. 检查DNS的SPF/DKIM/DMARC记录配置是否正确（影响外发邮件到达率）。\n- 5. Outlook配置修复：控制面板 → 邮件 → 配置文件 → 重建Outlook配置文件。\n- 6. 检查公网IP是否在黑名单中（MXToolbox查询），如被列入需申请移出。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-001 · 分类「邮件与通讯问题」· 由清洗流水线自动生成\n",
  "Header_2": "现象描述",
  "child_idx": 0,
  "wiki_keywords": "[\"邮件\", \"Outlook\", \"发送失败\", \"退信\", \"SMTP\", \"发送报告\", \"邮件在发件箱\", \"无法送达\"]",
  "source_file": "ITKB-MAIL-001.md",
  "chunk_role": "child",
  "chunk_length": 265,
  "parent_id": "ITKB-MAIL-001",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)"
}
  ```

---
### [TC-05] VPN错误代码与协议切换
- **业务提问**：`在家连公司VPN报错806怎么排查？推荐切换到什么协议穿透性最好？`
- **潜在冲突与风险点**：错误代码、协议名称与推荐结论(SSL VPN)需同时命中
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：# 【LEG-VPN-001】VPN连接失败处理（旧版·PPTP，已废止）  > ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-VPN-001 VPN连接失败（拨号/认证失败）》为准，仅作历史溯...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【VPN-001】VPN连接失败（拨号/认证失败）  ## 现象描述  - 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、6...
- **注入元数据快照**：
  ```json
{
  "Header_2": "现象描述",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "parent_content": "# 【VPN-001】VPN连接失败（拨号/认证失败）\n\n## 现象描述\n\n- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、691。\n\n## 常见根因\n\n- ① 家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）\n- ② VPN客户端配置错误（服务器地址、预共享密钥）\n- ③ 用户名密码错误或AD账号被锁定\n- ④ 运营商网络NAT穿透问题\n- ⑤ VPN服务器端故障或并发连接数已满\n- ⑥ 证书过期（SSL VPN）\n\n## 员工自助排查\n\n- 步骤1：检查本地网络是否能正常上网（浏览器打开百度测试）。\n- 步骤2：尝试手机热点连接——如果热点可以但家庭宽带不行，说明是家庭路由器/宽带问题。\n- 步骤3：重启家用路由器和电脑。\n- 步骤4：确认VPN服务器地址和密钥配置正确（对照公司VPN配置文档）。\n- 步骤5：尝试切换VPN协议（如从L2TP切换到SSL VPN，或从SSL VPN切换到IKEv2）。\n- 步骤6：关闭Windows防火墙和第三方杀毒软件临时测试。\n\n## IT工程师进阶处理\n\n- 1. 检查VPN服务器状态：CPU、内存、并发连接数、带宽占用。\n- 2. 检查防火墙策略：确保VPN协议端口（UDP 500/4500、TCP 443等）在边界防火墙上放行。\n- 3. 检查用户AD账号状态（是否锁定、密码是否过期）。\n- 4. 查看VPN服务器日志，定位具体拒绝原因。\n- 5. 为用户切换VPN协议或更新客户端配置。\n- 6. 推荐使用SSL VPN（基于HTTPS，穿透性最好，不易被酒店/咖啡厅WiFi阻断）。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-001 · 分类「VPN与远程办公」· 由清洗流水线自动生成\n",
  "wiki_category": "VPN与远程办公",
  "chunk_length": 253,
  "wiki_version": "v1.0",
  "wiki_status": "现行",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "chunk_role": "child",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "wiki_replaces": "[]",
  "wiki_meta_source": "llm",
  "child_id": "ITKB-VPN-001#c0",
  "wiki_department": "IT 部",
  "child_idx": 0,
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "wiki_id": "ITKB-VPN-001",
  "parent_id": "ITKB-VPN-001",
  "wiki_entities": "[\"VPN\", \"SSL VPN\", \"L2TP\", \"IPSec\", \"PPTP\", \"IKEv2\", \"AD账号\", \"预共享密钥\"]",
  "source_file": "ITKB-VPN-001.md"
}
  ```

---
## 三、 结论与阶段技术承接
1. **父子切块（Small-to-Big）价值确证**：以 H2 小节为语义边界生成子块做高精度向量与关键词匹配，仅在首块注入检索增强词以避免稀释步骤块特征，命中后回溯整卡父块，兼顾匹配聚焦度与上下文完整性；
2. **元数据前置过滤完全生效**：借助 `wiki_category` 与 `wiki_status` 的过滤条件，检索链路成功将查询范围物理限定在目标故障域并定位到具体 `Header_2` 小节；
3. **技术承接**：本日持久化落盘的 `chroma_wiki_structured/` 数据库，将无缝对接 **BM25 + Dense 双路召回与 Rerank 精排工程**。
