# Chunking 分块策略与向量化评测报告

> 知识库来源：《IT常见问题RAG知识库.docx》→ 清洗重构产出的 38 张 Wiki 知识卡片
> Embedding 模型：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维，余弦归一化）

## 一、 实验工程概览与参数对照

| 维度指标 | 对照组 A：朴素固定长度分块 (Naive Fixed) | 实验组 B：父子切片 (Parent-Child / Small-to-Big) | 工业收益说明 |
| :--- | :--- | :--- | :--- |
| **切块策略** | 纯按 500 字符切分，忽略标题与段落 | H2 语义边界分节 + 512 字符行累加子块 + 差异化上下文头 | 保证每个切块语意自包含，无断头句、不断裂跨节事实 |
| **元数据注入** | ❌ 无元数据注入（仅记录源文件名与切片号） | ✅ 深度注入 YAML Frontmatter (`wiki_category`/`wiki_status`/`Header_2`) | 支持混合检索的前置硬过滤与废止卡屏蔽 |
| **切片总数量** | 263 个切片 | 144 个匹配子块（对应 38 张完整父卡） | 匹配用细粒度子块保障向量聚焦，生成用完整父卡保障上下文 |
| **平均切块长度** | 约 397 字符 | 子块平均 244 字符（命中后回溯父卡全文 ~750 字符） | 命中子块后经 `expand_to_parents` 零成本回溯完整排查链路 |
| **分类冲突防御** | ❌ 无法区分网络/账号/硬件等故障域 | ✅ 携带 `wiki_category`、`wiki_department` 与 `wiki_status` | 跨分类检索时物理屏蔽无关域与废止卡干扰 |

---

## 二、 5 组复杂业务对抗检索评测结果 (Benchmark)

### [TC-01] 账号锁定阈值与解锁
- **业务提问**：`员工密码输错几次域账号会被锁定？锁定后等待多久可能自动解锁？`
- **潜在冲突与风险点**：锁定阈值5次与自动解锁窗口15-30分钟是硬数字，切片必须保留完整条件句
- **朴素切块命中率**：3/4
  > **朴素切片摘要**：# 【LEG-ACC-001】域账号锁定处理（旧版·宽松策略，已废止）  > ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留。  ...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【LEG-ACC-001】域账号锁定处理（旧版·宽松策略，已废止）  > ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留。  ...
- **注入元数据快照**：
  ```json
{
  "child_idx": 2,
  "Header_2": "员工自助排查（已废止）",
  "parent_id": "ITKB-LEG-ACC-001",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_id": "ITKB-LEG-ACC-001",
  "wiki_category": "账号与权限问题",
  "Header_1": "域账号锁定处理（旧版·宽松策略，已废止）",
  "child_id": "ITKB-LEG-ACC-001#c2",
  "parent_content": "# 【LEG-ACC-001】域账号锁定处理（旧版·宽松策略，已废止）\n\n> ⚠️ 本卡为 v0.9 旧版规约，**已于 v1.0 全面废止**。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留。\n\n## 现象描述\n\n- 登录时提示「账号已被锁定」「登录失败次数过多」。\n\n## 常见根因\n\n- ① 连续多次输入错误密码触发旧版安全策略\n- ② 恶意软件暴力破解尝试\n\n## 员工自助排查（已废止）\n\n- 步骤1：连续输错 3 次密码即触发锁定（现行标准已调整为 5 次）。\n- 步骤2：锁定后不会自动解锁，必须人工联系IT解锁（现行标准已调整为等待 15-30 分钟自动解锁）。\n- 步骤3：员工无需等待，立即电话IT支持。\n\n## IT工程师进阶处理（已废止）\n\n- 1. 在安全日志中筛选旧版锁定事件进行溯源。\n- 2. 记录发生锁定的来源设备。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 旧版条目 · 分类「账号与权限问题」· v0.9 已废止，保留仅供版本冲突溯源\n",
  "wiki_status": "已废止",
  "wiki_graph_nodes": "[{\"kind\": \"symptom\", \"name\": \"账号已被锁定\"}, {\"kind\": \"symptom\", \"name\": \"登录失败次数过多\"}, {\"kind\": \"root_cause\", \"name\": \"连续多次输入错误密码触发旧版安全策略\"}, {\"kind\": \"root_cause\", \"name\": \"恶意软件暴力破解尝试\"}, {\"kind\": \"tool\", \"name\": \"安全日志\"}]",
  "wiki_version": "v0.9",
  "wiki_title": "域账号锁定处理（旧版·宽松策略，已废止）",
  "wiki_effective_date": "2022-01-01",
  "source_file": "ITKB-LEG-ACC-001.md",
  "wiki_entities": "[{\"name\": \"账号锁定\", \"type\": \"故障现象\"}, {\"name\": \"安全日志\", \"type\": \"系统\"}]",
  "chunk_role": "child",
  "wiki_meta_source": "rule",
  "wiki_keywords": "[\"账号锁定\", \"密码错误\", \"登录失败\", \"AD域\", \"账号禁用\", \"多次输错密码\", \"解锁账号\", \"4740\"]",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "wiki_replaces": "[]",
  "wiki_summary": "（已废止，v1.0 版 ITKB-ACC-001 为准）旧版宽松锁定策略：3 次锁定、不自动解锁，与现行 5 次/15-30分钟策略冲突。",
  "wiki_graph_meta_source": "llm",
  "chunk_length": 170,
  "wiki_department": "IT 部",
  "wiki_relations": "[{\"target\": \"ITKB-ACC-001\", \"type\": \"replaces\", \"note\": \"本卡为 v0.9 旧版规约已全面废止，现行标准由 ITKB-ACC-001（5 次锁定/15-30 分钟自动解锁）替代，本卡仅作历史溯源保留\", \"evidence\": \"已于 v1.0 全面废止。现行标准请以《ITKB-ACC-001 域账号锁定排查与解锁处理》为准，仅作历史溯源保留\"}]"
}
  ```

---
### [TC-02] DNS故障现象与处置
- **业务提问**：`电脑能上QQ但打不开网页，提示DNS_PROBE_FINISHED_NXDOMAIN，员工如何自助处理？`
- **潜在冲突与风险点**：清缓存命令、阿里DNS地址、hosts路径必须同块召回，否则处置链断裂
- **朴素切块命中率**：2/4
  > **朴素切片摘要**：# 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/Q...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【NET-004】DNS解析失败故障排查与处置  ## 现象描述  - 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/Q...
- **注入元数据快照**：
  ```json
{
  "parent_id": "ITKB-NET-004",
  "wiki_graph_meta_source": "llm",
  "wiki_department": "IT 部",
  "wiki_effective_date_source": "demo-constructed",
  "Header_2": "现象描述",
  "Header_1": "DNS解析失败故障排查与处置",
  "wiki_relations": "[{\"target\": \"ITKB-LEG-NET-004\", \"type\": \"replaces\", \"note\": \"本卡为现行版DNS解析故障处置规范，替代已废止的旧版强制内网DNS方案\", \"evidence\": \"（已废止，v1.0 版 ITKB-NET-004 为准）旧版强制统一使用内网 10.0.0.1 并禁用公共 DNS 的处置方法。\"}, {\"target\": \"ITKB-APPENDIX-1\", \"type\": \"process_applies\", \"note\": \"员工IT故障自助排查五步法适用于本卡的员工自助排查环节\", \"evidence\": \"提供员工IT故障自助排查五步法：重启、确认影响范围、收集错误信息、搜索知识库、提交IT工单。\"}, {\"target\": \"ITKB-APPENDIX-2\", \"type\": \"process_applies\", \"note\": \"IT故障排查七步通用流程（含OSI分层排查）适用于本卡DNS故障的分层排查处置\", \"evidence\": \"规范IT故障排查七步流程：信息收集、复现测试、按OSI模型分层排查、日志分析、交叉验证、修复回归与知识沉淀。\"}, {\"target\": \"ITKB-APPENDIX-3\", \"type\": \"related\", \"note\": \"本卡使用的nslookup、ipconfig /flushdns等排查命令可由常用命令速查表支撑\", \"evidence\": \"为IT故障排查提供常用命令速查，支撑按通用流程快速定位与处置。\"}, {\"target\": \"ITKB-NET-003\", \"type\": \"related\", \"note\": \"DNS异常也是网络断连与网速慢故障的分层排查因素之一，两卡排查面存在交叉\", \"evidence\": \"按带宽占用、ARP攻击、线路质量、DNS、端口协商、无线干扰分层排查处置\"}, {\"target\": \"ITKB-VPN-002\", \"type\": \"related\", \"note\": \"VPN/代理软件残留的DNS配置可致解析失败，VPN后无法访问内网资源的排查同样涉及DNS环节\", \"evidence\": \"⑤ 代理/VPN软件残留的DNS配置\"}, {\"target\": \"ITKB-STO-002\", \"type\": \"related\", \"note\": \"共享盘无法访问的排查链路中包含DNS环节，与本卡根因存在交叉\", \"evidence\": \"按网络、凭据、DNS、SMB和服务器状态排查并重映射\"}, {\"target\": \"ITKB-SYS-005\", \"type\": \"related\", \"note\": \"浏览器页面加载失败与本卡网页打不开现象相似，且两卡均涉及代理因素，需相互鉴别\", \"evidence\": \"解决浏览器白屏、错乱或加载失败，按缓存、扩展、时间、代理与杀毒扫描排查\"}, {\"target\": \"ITKB-LEG-NET-004\", \"type\": \"replaces\", \"note\": \"frontmatter replaces 规则迁移\", \"evidence\": \"frontmatter:replaces\"}]",
  "source_file": "ITKB-NET-004.md",
  "wiki_replaces": "[\"ITKB-LEG-NET-004\"]",
  "chunk_length": 406,
  "wiki_graph_nodes": "[{\"kind\": \"symptom\", \"name\": \"无法访问此网站\"}, {\"kind\": \"symptom\", \"name\": \"DNS_PROBE_FINISHED_NXDOMAIN\"}, {\"kind\": \"symptom\", \"name\": \"ping IP地址通，ping域名不通\"}, {\"kind\": \"root_cause\", \"name\": \"DNS服务器地址配置错误或被篡改\"}, {\"kind\": \"root_cause\", \"name\": \"公司DNS服务器故障或过载\"}, {\"kind\": \"root_cause\", \"name\": \"DNS缓存污染\"}, {\"kind\": \"root_cause\", \"name\": \"hosts文件被恶意修改\"}, {\"kind\": \"root_cause\", \"name\": \"代理/VPN软件残留的DNS配置\"}, {\"kind\": \"tool\", \"name\": \"nslookup www.baidu.com\"}, {\"kind\": \"tool\", \"name\": \"ipconfig /flushdns\"}]",
  "child_id": "ITKB-NET-004#c0",
  "wiki_id": "ITKB-NET-004",
  "wiki_summary": "解决DNS解析失败致网页无法打开（QQ等正常）的问题：清缓存、改DNS、查hosts与代理，并排查公司DNS/DHCP/防火墙。",
  "wiki_status": "现行",
  "child_idx": 0,
  "wiki_title": "DNS解析失败故障排查与处置",
  "wiki_category": "网络连接问题",
  "wiki_version": "v1.0",
  "wiki_keywords": "[\"DNS\", \"打不开网页\", \"QQ能上\", \"域名解析\", \"nslookup\", \"DNS_PROBE_FINISHED\"]",
  "wiki_effective_date": "2024-03-01",
  "wiki_meta_source": "llm",
  "wiki_entities": "[{\"name\": \"DNS\", \"type\": \"协议\"}, {\"name\": \"DHCP\", \"type\": \"协议\"}, {\"name\": \"UDP 53端口\", \"type\": \"概念\"}, {\"name\": \"阿里DNS\", \"type\": \"系统\"}, {\"name\": \"DNS服务器\", \"type\": \"系统\"}, {\"name\": \"防火墙\", \"type\": \"系统\"}, {\"name\": \"VPN/代理软件\", \"type\": \"软件\"}, {\"name\": \"nslookup\", \"type\": \"命令工具\"}, {\"name\": \"ipconfig /flushdns\", \"type\": \"命令工具\"}, {\"name\": \"ping\", \"type\": \"命令工具\"}, {\"name\": \"ncpa.cpl\", \"type\": \"命令工具\"}, {\"name\": \"hosts文件\", \"type\": \"配置项\"}, {\"name\": \"Internet协议版本4\", \"type\": \"配置项\"}, {\"name\": \"DNS_PROBE_FINISHED_NXDOMAIN\", \"type\": \"故障现象\"}, {\"name\": \"ERR_NAME_NOT_RESOLVED\", \"type\": \"故障现象\"}]",
  "chunk_role": "child",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "parent_content": "# 【NET-004】DNS解析失败故障排查与处置\n\n## 现象描述\n\n- 浏览器访问任何网页均提示「无法访问此网站」「DNS_PROBE_FINISHED_NXDOMAIN」或「ERR_NAME_NOT_RESOLVED」。但企业微信/QQ等即时通讯软件可以正常收发消息。ping IP地址通，ping域名不通。\n\n## 常见根因\n\n- ① DNS服务器地址配置错误或被篡改\n- ② 公司DNS服务器故障或过载\n- ③ DNS缓存污染\n- ④ hosts文件被恶意修改\n- ⑤ 代理/VPN软件残留的DNS配置\n\n## 员工自助排查\n\n- 步骤1：Win+R → cmd → 输入 nslookup www.baidu.com，观察能否返回IP地址。\n- 步骤2：ipconfig /flushdns 清除DNS缓存。\n- 步骤3：Win+R → ncpa.cpl → 右键网卡 → 属性 → Internet协议版本4 → DNS改为223.5.5.5（阿里DNS）或公司内部DNS。\n- 步骤4：检查 C:\\Windows\\System32\\drivers\\etc\\hosts 文件，删除可疑条目。\n- 步骤5：关闭VPN/代理软件后重试。\n- 步骤6：重启电脑。\n\n## IT工程师进阶处理\n\n- 1. 检查公司DNS服务器是否正常运行（nslookup 使用公司 DNS 测试）。\n- 2. 检查DHCP下发的DNS地址是否正确。\n- 3. 查防火墙是否拦截了DNS（UDP 53端口）。\n- 4. 如近期做过DNS迁移，检查旧DNS是否已从所有DHCP作用域中移除。\n- 5. 检查是否存在DNS劫持或中间人攻击。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 NET-004 · 分类「网络连接问题」· 由清洗流水线自动生成\n"
}
  ```

---
### [TC-03] 蓝屏内存排查与工具
- **业务提问**：`电脑频繁蓝屏显示MEMORY_MANAGEMENT，如何检查内存？IT用什么工具分析dump文件？`
- **潜在冲突与风险点**：员工自助命令与工程师工具分属两节，切块需保住各自工具清单
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：note: "IT故障排查通用流程适用于本卡IT工程师进阶处理（dump日志分析、定位根因）"   evidence: "使用 BlueScreenView 工具分析 dump 文件（C:\\Windows\\Minidump），定位导致蓝...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【SYS-001】Windows蓝屏死机故障处置  ## 现象描述  - 电脑在使用过程中突然蓝屏，显示错误代码（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEMENT、DRIVER_IRQL_NOT_LES...
- **注入元数据快照**：
  ```json
{
  "child_id": "ITKB-SYS-001#c0",
  "wiki_meta_source": "llm",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "wiki_title": "Windows蓝屏死机故障处置",
  "wiki_summary": "解决Windows蓝屏死机问题，通过错误代码、内存、驱动、系统文件、散热与硬盘排查定位修复。",
  "wiki_category": "系统与软件故障",
  "wiki_graph_meta_source": "llm",
  "wiki_id": "ITKB-SYS-001",
  "wiki_keywords": "[\"蓝屏\", \"BSOD\", \"死机\", \"蓝屏代码\", \"STOP错误\", \"系统崩溃\", \"自动重启\", \"CRITICAL_PROCESS_DIED\"]",
  "wiki_status": "现行",
  "child_idx": 0,
  "wiki_entities": "[{\"name\": \"Windows\", \"type\": \"系统\"}, {\"name\": \"蓝屏\", \"type\": \"故障现象\"}, {\"name\": \"CRITICAL_PROCESS_DIED\", \"type\": \"故障现象\"}, {\"name\": \"MEMORY_MANAGEMENT\", \"type\": \"故障现象\"}, {\"name\": \"DRIVER_IRQL_NOT_LESS_OR_EQUAL\", \"type\": \"故障现象\"}, {\"name\": \"内存故障\", \"type\": \"故障现象\"}, {\"name\": \"驱动程序\", \"type\": \"软件\"}, {\"name\": \"sfc /scannow\", \"type\": \"命令工具\"}, {\"name\": \"mdsched.exe\", \"type\": \"命令工具\"}, {\"name\": \"BlueScreenView\", \"type\": \"软件\"}, {\"name\": \"MemTest86\", \"type\": \"软件\"}, {\"name\": \"CrystalDiskInfo\", \"type\": \"软件\"}, {\"name\": \"事件查看器\", \"type\": \"软件\"}, {\"name\": \"安全模式\", \"type\": \"概念\"}, {\"name\": \"dump 文件\", \"type\": \"概念\"}]",
  "parent_content": "# 【SYS-001】Windows蓝屏死机故障处置\n\n## 现象描述\n\n- 电脑在使用过程中突然蓝屏，显示错误代码（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEMENT、DRIVER_IRQL_NOT_LESS_OR_EQUAL 等），随后自动重启。或电脑完全卡死，鼠标键盘无响应，只能长按电源键强制关机。\n\n## 常见根因\n\n- ① 内存故障（接触不良、金手指氧化、内存条损坏）\n- ② 驱动程序不兼容（特别是显卡驱动、网卡驱动）\n- ③ 系统文件损坏（非正常关机导致）\n- ④ 散热不良导致CPU/显卡过热保护\n- ⑤ 硬盘坏道或SSD固件问题\n- ⑥ 软件冲突（杀毒软件、系统优化工具）\n\n## 员工自助排查\n\n- 步骤1：重启电脑。如果频繁蓝屏，记录下蓝屏错误代码（拍照保存）。\n- 步骤2：Win+R → 输入 mdsched.exe → 选择「立即重新启动并检查内存问题」进行内存诊断。\n- 步骤3：检查电脑散热口是否被遮挡，风扇是否正常运转。\n- 步骤4：Win+I → Windows更新 → 检查并安装所有待处理的更新。\n- 步骤5：如果有最近安装的软件/驱动，尝试卸载后观察。\n- 步骤6：Win+R → cmd（管理员） → sfc /scannow 扫描修复系统文件。\n\n## IT工程师进阶处理\n\n- 1. 使用 BlueScreenView 工具分析 dump 文件（C:\\Windows\\Minidump），定位导致蓝屏的驱动/模块。\n- 2. 使用 MemTest86 进行深度内存检测（需制作启动U盘）。\n- 3. 使用 CrystalDiskInfo 检查硬盘健康状态（SMART数据）。\n- 4. 进入安全模式卸载可疑驱动/软件。\n- 5. 检查系统事件查看器（eventvwr.msc）→ Windows日志 → 系统，筛选关键错误。\n- 6. 如确认为硬件故障，协调更换内存/硬盘，或整机返修。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 SYS-001 · 分类「系统与软件故障」· 由清洗流水线自动生成\n",
  "wiki_relations": "[{\"target\": \"ITKB-SYS-002\", \"type\": \"related\", \"note\": \"均为崩溃类故障，均需借助事件查看器分析日志定位\", \"evidence\": \"检查系统事件查看器（eventvwr.msc）→ Windows日志 → 系统，筛选关键错误\"}, {\"target\": \"ITKB-SYS-003\", \"type\": \"related\", \"note\": \"蓝屏自助排查包含检查并安装Windows更新步骤，与更新失败处置衔接\", \"evidence\": \"Win+I → Windows更新 → 检查并安装所有待处理的更新\"}, {\"target\": \"ITKB-APPENDIX-1\", \"type\": \"process_applies\", \"note\": \"员工IT故障自助排查五步法适用于本卡员工自助排查章节（先重启、记录错误信息）\", \"evidence\": \"步骤1：重启电脑。如果频繁蓝屏，记录下蓝屏错误代码（拍照保存）\"}, {\"target\": \"ITKB-APPENDIX-2\", \"type\": \"process_applies\", \"note\": \"IT故障排查通用流程适用于本卡IT工程师进阶处理（dump日志分析、定位根因）\", \"evidence\": \"使用 BlueScreenView 工具分析 dump 文件（C:\\\\Windows\\\\Minidump），定位导致蓝屏的驱动/模块\"}, {\"target\": \"ITKB-APPENDIX-3\", \"type\": \"process_applies\", \"note\": \"本卡使用mdsched.exe、sfc /scannow、eventvwr.msc等命令，由命令速查表支撑\", \"evidence\": \"Win+R → cmd（管理员） → sfc /scannow 扫描修复系统文件\"}, {\"target\": \"ITKB-HW-001\", \"type\": \"related\", \"note\": \"内存等硬件故障既是蓝屏根因也是无法开机黑屏的排查对象\", \"evidence\": \"① 内存故障（接触不良、金手指氧化、内存条损坏）\"}, {\"target\": \"ITKB-HW-005\", \"type\": \"related\", \"note\": \"蓝屏卡死时伴随鼠标键盘无响应现象，与键鼠失灵卡相关\", \"evidence\": \"或电脑完全卡死，鼠标键盘无响应，只能长按电源键强制关机\"}, {\"target\": \"ITKB-OFF-002\", \"type\": \"related\", \"note\": \"均采用进入安全模式隔离软件冲突/可疑组件的排查手段\", \"evidence\": \"进入安全模式卸载可疑驱动/软件\"}]",
  "chunk_length": 444,
  "Header_2": "现象描述",
  "Header_1": "Windows蓝屏死机故障处置",
  "wiki_department": "IT 部",
  "wiki_replaces": "[]",
  "parent_id": "ITKB-SYS-001",
  "source_file": "ITKB-SYS-001.md",
  "chunk_role": "child",
  "wiki_graph_nodes": "[{\"kind\": \"symptom\", \"name\": \"蓝屏死机\"}, {\"kind\": \"symptom\", \"name\": \"电脑完全卡死，鼠标键盘无响应\"}, {\"kind\": \"root_cause\", \"name\": \"内存故障\"}, {\"kind\": \"root_cause\", \"name\": \"驱动程序不兼容\"}, {\"kind\": \"root_cause\", \"name\": \"系统文件损坏\"}, {\"kind\": \"root_cause\", \"name\": \"散热不良导致CPU/显卡过热保护\"}, {\"kind\": \"root_cause\", \"name\": \"硬盘坏道或SSD固件问题\"}, {\"kind\": \"tool\", \"name\": \"BlueScreenView\"}, {\"kind\": \"tool\", \"name\": \"MemTest86\"}, {\"kind\": \"tool\", \"name\": \"CrystalDiskInfo\"}]",
  "wiki_version": "v1.0"
}
  ```

---
### [TC-04] 邮件退信与附件限制
- **业务提问**：`发邮件收到退信提示552 Message size exceeds是什么意思？附件超过限制怎么办？`
- **潜在冲突与风险点**：退信代码含义与20-50MB限制、云盘替代方案必须完整召回
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：# 【MAIL-001】邮件无法发送处置指南  ## 现象描述  - 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message s...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【MAIL-001】邮件无法发送处置指南  ## 现象描述  - 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message s...
- **注入元数据快照**：
  ```json
{
  "wiki_department": "IT 部",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "wiki_entities": "[{\"name\": \"Outlook\", \"type\": \"软件\"}, {\"name\": \"网页邮箱\", \"type\": \"系统\"}, {\"name\": \"SMTP\", \"type\": \"协议\"}, {\"name\": \"退信\", \"type\": \"故障现象\"}, {\"name\": \"Exchange\", \"type\": \"软件\"}, {\"name\": \"反垃圾邮件网关\", \"type\": \"设备\"}, {\"name\": \"OneDrive\", \"type\": \"软件\"}, {\"name\": \"脱机工作\", \"type\": \"配置项\"}, {\"name\": \"邮箱配额\", \"type\": \"配置项\"}, {\"name\": \"白名单\", \"type\": \"配置项\"}, {\"name\": \"SPF/DKIM/DMARC\", \"type\": \"协议\"}, {\"name\": \"DNS\", \"type\": \"协议\"}, {\"name\": \"MXToolbox\", \"type\": \"命令工具\"}, {\"name\": \"防火墙\", \"type\": \"设备\"}, {\"name\": \"配置文件\", \"type\": \"配置项\"}]",
  "chunk_role": "child",
  "parent_id": "ITKB-MAIL-001",
  "wiki_graph_nodes": "[{\"kind\": \"symptom\", \"name\": \"邮件停留在发件箱无法发出\"}, {\"kind\": \"symptom\", \"name\": \"收到退信通知\"}, {\"kind\": \"root_cause\", \"name\": \"收件人邮箱地址写错\"}, {\"kind\": \"root_cause\", \"name\": \"附件超过大小限制\"}, {\"kind\": \"root_cause\", \"name\": \"SMTP服务器无响应或被防火墙拦截\"}, {\"kind\": \"root_cause\", \"name\": \"邮箱已满（达到存储配额上限）\"}, {\"kind\": \"root_cause\", \"name\": \"邮件被反垃圾邮件策略拦截\"}, {\"kind\": \"root_cause\", \"name\": \"Outlook离线模式误开启\"}, {\"kind\": \"tool\", \"name\": \"Exchange管理后台\"}, {\"kind\": \"tool\", \"name\": \"MXToolbox查询\"}]",
  "wiki_replaces": "[]",
  "child_idx": 1,
  "wiki_meta_source": "llm",
  "wiki_version": "v1.0",
  "wiki_keywords": "[\"邮件\", \"Outlook\", \"发送失败\", \"退信\", \"SMTP\", \"发送报告\", \"邮件在发件箱\", \"无法送达\"]",
  "wiki_category": "邮件与通讯问题",
  "child_id": "ITKB-MAIL-001#c1",
  "wiki_relations": "[{\"target\": \"ITKB-MAIL-002\", \"type\": \"related\", \"note\": \"邮件发送与接收为姊妹问题，共用网页邮箱测试、邮箱配额与垃圾拦截等排查手段\", \"evidence\": \"邮箱已满（达到存储配额上限）\"}, {\"target\": \"ITKB-APPENDIX-1\", \"type\": \"process_applies\", \"note\": \"本卡设有员工自助排查六个步骤，遵循员工IT故障自助排查流程规范\", \"evidence\": \"员工自助排查\"}, {\"target\": \"ITKB-APPENDIX-2\", \"type\": \"process_applies\", \"note\": \"IT工程师进阶处理包含日志分析与分层定位，符合IT故障排查通用七步流程\", \"evidence\": \"检查邮件服务器SMTP日志，定位拒绝原因\"}, {\"target\": \"ITKB-NET-004\", \"type\": \"related\", \"note\": \"外发邮件到达率依赖DNS的SPF/DKIM/DMARC记录配置，与DNS解析排查相关\", \"evidence\": \"检查DNS的SPF/DKIM/DMARC记录配置是否正确（影响外发邮件到达率）\"}, {\"target\": \"ITKB-STO-003\", \"type\": \"related\", \"note\": \"附件超过大小限制时建议改用OneDrive或公司内部云盘链接替代发送\", \"evidence\": \"超过限制的用云盘链接替代（如 OneDrive / 公司内部云盘）\"}]",
  "chunk_length": 179,
  "Header_1": "邮件无法发送处置指南",
  "wiki_status": "现行",
  "wiki_title": "邮件无法发送处置指南",
  "wiki_id": "ITKB-MAIL-001",
  "parent_content": "# 【MAIL-001】邮件无法发送处置指南\n\n## 现象描述\n\n- 在Outlook或网页邮箱中点击发送后，邮件停留在发件箱无法发出，或收到退信通知。退信常见提示：「550 Mailbox not found」「552 Message size exceeds」「554 Rejected」。\n\n## 常见根因\n\n- ① 收件人邮箱地址写错（拼写错误、用户不存在）\n- ② 附件超过大小限制（公司邮箱通常限制20-50MB）\n- ③ SMTP服务器无响应或被防火墙拦截\n- ④ 邮箱已满（达到存储配额上限）\n- ⑤ 邮件被反垃圾邮件策略拦截（内容含敏感词或可疑链接）\n- ⑥ Outlook离线模式误开启\n\n## 员工自助排查\n\n- 步骤1：检查收件人地址拼写，确认无误后重发。\n- 步骤2：检查附件大小，超过限制的用云盘链接替代（如 OneDrive / 公司内部云盘）。\n- 步骤3：Outlook → 发送/接收 → 确认「脱机工作」未被选中。\n- 步骤4：登录网页版邮箱测试发送是否正常——如果网页版正常，说明是Outlook客户端问题。\n- 步骤5：清理邮箱，删除不需要的旧邮件，清空已删除邮件和垃圾邮件文件夹。\n- 步骤6：暂时关闭杀毒软件邮件扫描功能测试。\n\n## IT工程师进阶处理\n\n- 1. 检查邮件服务器SMTP日志，定位拒绝原因。\n- 2. 检查用户邮箱配额：Exchange管理后台 → 邮箱使用情况 → 提高配额或归档旧邮件。\n- 3. 反垃圾邮件网关：检查该邮件是否被误判为垃圾邮件，添加到白名单。\n- 4. 检查DNS的SPF/DKIM/DMARC记录配置是否正确（影响外发邮件到达率）。\n- 5. Outlook配置修复：控制面板 → 邮件 → 配置文件 → 重建Outlook配置文件。\n- 6. 检查公网IP是否在黑名单中（MXToolbox查询），如被列入需申请移出。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 MAIL-001 · 分类「邮件与通讯问题」· 由清洗流水线自动生成\n",
  "wiki_graph_meta_source": "llm",
  "source_file": "ITKB-MAIL-001.md",
  "wiki_summary": "解决邮件发送失败或退信问题，按地址、附件、客户端、配额及反垃圾策略排查。",
  "Header_2": "常见根因"
}
  ```

---
### [TC-05] VPN错误代码与协议切换
- **业务提问**：`在家连公司VPN报错806怎么排查？推荐切换到什么协议穿透性最好？`
- **潜在冲突与风险点**：错误代码、协议名称与推荐结论(SSL VPN)需同时命中
- **朴素切块命中率**：4/4
  > **朴素切片摘要**：# 【VPN-001】VPN连接失败（拨号/认证失败）  ## 现象描述  - 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、6...
- **Wiki感知切块命中率**：**4/4**
  > **结构化切片摘要**：# 【VPN-001】VPN连接失败（拨号/认证失败）  ## 现象描述  - 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、6...
- **注入元数据快照**：
  ```json
{
  "source_file": "ITKB-VPN-001.md",
  "child_id": "ITKB-VPN-001#c0",
  "wiki_entities": "[{\"name\": \"VPN\", \"type\": \"概念\"}, {\"name\": \"SSL VPN\", \"type\": \"协议\"}, {\"name\": \"L2TP\", \"type\": \"协议\"}, {\"name\": \"IPSec\", \"type\": \"协议\"}, {\"name\": \"PPTP\", \"type\": \"协议\"}, {\"name\": \"IKEv2\", \"type\": \"协议\"}, {\"name\": \"AD账号\", \"type\": \"账号权限\"}, {\"name\": \"预共享密钥\", \"type\": \"配置项\"}, {\"name\": \"VPN服务器\", \"type\": \"系统\"}, {\"name\": \"VPN客户端\", \"type\": \"软件\"}, {\"name\": \"Windows防火墙\", \"type\": \"软件\"}, {\"name\": \"NAT穿透\", \"type\": \"概念\"}, {\"name\": \"HTTPS\", \"type\": \"协议\"}, {\"name\": \"服务器地址\", \"type\": \"配置项\"}, {\"name\": \"用户名密码\", \"type\": \"账号权限\"}]",
  "wiki_title": "VPN连接失败（拨号/认证失败）",
  "wiki_summary": "针对远程办公VPN拨号/认证失败问题，提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法。",
  "wiki_effective_date_source": "demo-constructed",
  "wiki_effective_date": "2024-03-01",
  "wiki_relations": "[{\"target\": \"ITKB-LEG-VPN-001\", \"type\": \"replaces\", \"note\": \"本卡为现行版本，废止旧版推荐PPTP并限制SSL VPN的处置方法，改为推荐SSL VPN\", \"evidence\": \"（已废止，v1.0 版 ITKB-VPN-001 为准）旧版推荐 PPTP 协议连接并限制 SSL VPN 的处置方法\"}, {\"target\": \"ITKB-VPN-002\", \"type\": \"related\", \"note\": \"本卡处理VPN拨号/认证失败，VPN-002处理已连接后无法访问内网资源，属同一VPN故障链的上下游环节\", \"evidence\": \"解决VPN已连接但无法访问内网资源问题\"}, {\"target\": \"ITKB-VPN-003\", \"type\": \"related\", \"note\": \"远程桌面连接内网电脑依赖VPN连通，VPN-003排查项明确包含VPN与防火墙\", \"evidence\": \"按开机状态、远程桌面开关、VPN与防火墙、NLA凭据、IP变更逐步排查处置\"}, {\"target\": \"ITKB-ACC-001\", \"type\": \"related\", \"note\": \"AD账号被锁定是VPN认证失败的常见根因之一，需联动账号锁定排查卡处理\", \"evidence\": \"③ 用户名密码错误或AD账号被锁定\"}, {\"target\": \"ITKB-ACC-002\", \"type\": \"related\", \"note\": \"密码过期会导致VPN认证失败，IT进阶处理中需检查密码是否过期，与密码重置卡关联\", \"evidence\": \"检查用户AD账号状态（是否锁定、密码是否过期）\"}, {\"target\": \"ITKB-APPENDIX-2\", \"type\": \"process_applies\", \"note\": \"本卡按本地网络、客户端配置到服务器与账号状态分层排查，符合IT故障排查通用流程\", \"evidence\": \"提供从本地网络、客户端配置到服务器与账号状态的分层排查处置方法\"}, {\"target\": \"ITKB-LEG-VPN-001\", \"type\": \"replaces\", \"note\": \"frontmatter replaces 规则迁移\", \"evidence\": \"frontmatter:replaces\"}]",
  "Header_2": "现象描述",
  "wiki_keywords": "[\"VPN\", \"远程办公\", \"拨号\", \"连接失败\", \"认证失败\", \"L2TP\", \"SSL VPN\", \"在家办公\"]",
  "Header_1": "VPN连接失败（拨号/认证失败）",
  "wiki_version": "v1.0",
  "wiki_category": "VPN与远程办公",
  "wiki_graph_nodes": "[{\"kind\": \"symptom\", \"name\": \"无法建立VPN连接\"}, {\"kind\": \"symptom\", \"name\": \"认证失败\"}, {\"kind\": \"symptom\", \"name\": \"远程服务器无响应\"}, {\"kind\": \"symptom\", \"name\": \"常见错误代码：800、806、807、809、868、691\"}, {\"kind\": \"root_cause\", \"name\": \"家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）\"}, {\"kind\": \"root_cause\", \"name\": \"VPN客户端配置错误（服务器地址、预共享密钥）\"}, {\"kind\": \"root_cause\", \"name\": \"用户名密码错误或AD账号被锁定\"}, {\"kind\": \"root_cause\", \"name\": \"证书过期（SSL VPN）\"}, {\"kind\": \"tool\", \"name\": \"SSL VPN\"}, {\"kind\": \"tool\", \"name\": \"IKEv2\"}]",
  "wiki_status": "现行",
  "wiki_graph_meta_source": "llm",
  "chunk_length": 302,
  "wiki_department": "IT 部",
  "wiki_id": "ITKB-VPN-001",
  "wiki_meta_source": "llm",
  "child_idx": 0,
  "wiki_replaces": "[\"ITKB-LEG-VPN-001\"]",
  "parent_id": "ITKB-VPN-001",
  "chunk_role": "child",
  "split_strategy": "Parent-Child (子块=512字符 H2边界行累加+差异化上下文头)",
  "parent_content": "# 【VPN-001】VPN连接失败（拨号/认证失败）\n\n## 现象描述\n\n- 在家/出差期间连接公司VPN时，提示「连接失败」「无法建立VPN连接」「认证失败」「远程服务器无响应」。常见错误代码：800、806、807、809、868、691。\n\n## 常见根因\n\n- ① 家庭网络/酒店网络防火墙阻断了VPN协议（PPTP/L2TP/IPSec）\n- ② VPN客户端配置错误（服务器地址、预共享密钥）\n- ③ 用户名密码错误或AD账号被锁定\n- ④ 运营商网络NAT穿透问题\n- ⑤ VPN服务器端故障或并发连接数已满\n- ⑥ 证书过期（SSL VPN）\n\n## 员工自助排查\n\n- 步骤1：检查本地网络是否能正常上网（浏览器打开百度测试）。\n- 步骤2：尝试手机热点连接——如果热点可以但家庭宽带不行，说明是家庭路由器/宽带问题。\n- 步骤3：重启家用路由器和电脑。\n- 步骤4：确认VPN服务器地址和密钥配置正确（对照公司VPN配置文档）。\n- 步骤5：尝试切换VPN协议（如从L2TP切换到SSL VPN，或从SSL VPN切换到IKEv2）。\n- 步骤6：关闭Windows防火墙和第三方杀毒软件临时测试。\n\n## IT工程师进阶处理\n\n- 1. 检查VPN服务器状态：CPU、内存、并发连接数、带宽占用。\n- 2. 检查防火墙策略：确保VPN协议端口（UDP 500/4500、TCP 443等）在边界防火墙上放行。\n- 3. 检查用户AD账号状态（是否锁定、密码是否过期）。\n- 4. 查看VPN服务器日志，定位具体拒绝原因。\n- 5. 为用户切换VPN协议或更新客户端配置。\n- 6. 推荐使用SSL VPN（基于HTTPS，穿透性最好，不易被酒店/咖啡厅WiFi阻断）。\n\n---\n> 🔗 溯源：摘自《IT常见问题RAG知识库.docx》· 条目 VPN-001 · 分类「VPN与远程办公」· 由清洗流水线自动生成\n"
}
  ```

---
## 三、 结论与阶段技术承接
1. **父子切块（Small-to-Big）价值确证**：以 H2 小节为语义边界生成子块做高精度向量与关键词匹配，仅在首块注入检索增强词以避免稀释步骤块特征，命中后回溯整卡父块，兼顾匹配聚焦度与上下文完整性；
2. **元数据前置过滤完全生效**：借助 `wiki_category` 与 `wiki_status` 的过滤条件，检索链路成功将查询范围物理限定在目标故障域并定位到具体 `Header_2` 小节；
3. **技术承接**：本日持久化落盘的 `chroma_wiki_structured/` 数据库，将无缝对接 **BM25 + Dense 双路召回与 Rerank 精排工程**。
