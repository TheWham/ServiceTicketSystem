"""对抗评测题集：Day12 TC 系列（切块质量）+ Day13 HC/NEG 系列（检索链路）。"""

# 设计说明：每道题的 expected_facts 均取自真实 Wiki 卡片正文的"硬事实"
# （命令、错误码、端口、阈值数字、工具名），用于量化"切块是否保住完整事实链"。
# 打分方式：把 Top-3 召回的切片正文拼接，统计 expected_facts 中有多少被包含。
# 这些题刻意挑选"考点横跨多个小节"或"含易漂移专有编号"的场景，
# 以便暴露过度切分 / 向量漂移等真实工程缺陷（见讲义 2.3 节）。
BENCHMARK_QUERIES = [
    {
        "id": "TC-01",
        "category": "账号锁定阈值与解锁",
        "query": "员工密码输错几次域账号会被锁定？锁定后等待多久可能自动解锁？",
        "expected_facts": ["5次", "15-30分钟", "锁定", "解锁"],
        "conflict_risk": "锁定阈值5次与自动解锁窗口15-30分钟是硬数字，切片必须保留完整条件句"
    },
    {
        "id": "TC-02",
        "category": "DNS故障现象与处置",
        "query": "电脑能上QQ但打不开网页，提示DNS_PROBE_FINISHED_NXDOMAIN，员工如何自助处理？",
        "expected_facts": ["ipconfig /flushdns", "223.5.5.5", "hosts", "nslookup"],
        "conflict_risk": "清缓存命令、阿里DNS地址、hosts路径必须同块召回，否则处置链断裂"
    },
    {
        "id": "TC-03",
        "category": "蓝屏内存排查与工具",
        "query": "电脑频繁蓝屏显示MEMORY_MANAGEMENT，如何检查内存？IT用什么工具分析dump文件？",
        "expected_facts": ["mdsched", "MemTest86", "BlueScreenView", "sfc /scannow"],
        "conflict_risk": "员工自助命令与工程师工具分属两节，切块需保住各自工具清单"
    },
    {
        "id": "TC-04",
        "category": "邮件退信与附件限制",
        "query": "发邮件收到退信提示552 Message size exceeds是什么意思？附件超过限制怎么办？",
        "expected_facts": ["552", "20-50MB", "云盘", "配额"],
        "conflict_risk": "退信代码含义与20-50MB限制、云盘替代方案必须完整召回"
    },
    {
        "id": "TC-05",
        "category": "VPN错误代码与协议切换",
        "query": "在家连公司VPN报错806怎么排查？推荐切换到什么协议穿透性最好？",
        "expected_facts": ["806", "SSL VPN", "防火墙", "L2TP"],
        "conflict_risk": "错误代码、协议名称与推荐结论(SSL VPN)需同时命中"
    }
]


# ==============================================================================
# 5. 主流水线协调控制器
# ==============================================================================



# 设计说明：评测集分三类题型，打分以"目标卡片是否进 Top-3"为卡级金标准：
#   1) hard（HC-01~07）：精确编号/命令/多跳/元数据过滤，考字面与结构召回；
#   2) paraphrase（HC-08~10）：query 刻意不含卡片词面，考纯语义召回；
#   3) confusable（HC-11~14）：字面贴近兄弟卡（confusable_with），考精排对真实诉求的辨别；
#   4) negative（NEG-01~06）：知识库无答案，考误召回/拒答能力（trap_ids 为易误召卡）。
# 打分方式（替代旧的"Top-3 拼接文本子串覆盖"，后者因高频通用词与整卡回溯而饱和）：
#   - 卡级 Recall@3 / MRR：目标卡 wiki_id 在回溯父块序列中的名次；
#   - 事实覆盖：expected_facts 只在"检索到的目标卡正文"内计数，目标卡未召回记 0；
#   - 负样本误召回率：Top-3 父块是否命中 trap_ids。
HARD_BENCHMARK_SUITE = [
    {
        "id": "HC-01",
        "category": "系统修复命令硬匹配",
        "query": "电脑频繁蓝屏，怀疑是非正常关机导致系统文件损坏，员工自己可以运行什么命令扫描修复？",
        "expected_facts": ["sfc /scannow", "系统文件"],
        "challenge_type": "精确命令字符串匹配 (向量易漂移，BM25强项)；以'蓝屏'锚定场景，避免与附录命令速查表的同名行抢答",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-SYS-001",
        "trap_ids": []
    },
    {
        "id": "HC-02",
        "category": "VPN错误代码与协议推荐",
        "query": "出差在酒店连公司VPN一直报错806，IT推荐改用哪种VPN协议穿透性最好、不容易被酒店WiFi阻断？",
        "expected_facts": ["806", "SSL VPN", "防火墙"],
        "challenge_type": "精确错误码 806 与协议名(SSL VPN)硬匹配",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-VPN-001",
        "trap_ids": []
    },
    {
        "id": "HC-03",
        "category": "跨分类元数据前置过滤 (账号域限定)",
        "query": "域账号反复被锁定，IT工程师应查看哪个事件ID的安全日志来定位锁定来源的IP和设备名？",
        "expected_facts": ["4740", "解锁", "Active Directory"],
        "challenge_type": "必须借助 wiki_category 前置过滤物理限定账号权限域，再命中事件ID 4740",
        "filter": {"wiki_category": "账号与权限问题"},
        "qtype": "hard",
        "target_id": "ITKB-ACC-001",
        "trap_ids": []
    },
    {
        "id": "HC-04",
        "category": "邮件退信代码含义",
        "query": "给客户发出去的邮件被退回，退信提示「550 Mailbox not found」，最可能是哪里出了问题？",
        "expected_facts": ["550", "收件人", "地址"],
        "challenge_type": "退信代码 550 与根因(收件人地址错误)关联；强调'发出去被退回'，与邮件接收失败卡区分",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-MAIL-001",
        "trap_ids": []
    },
    {
        "id": "HC-05",
        "category": "文件误删恢复与防覆盖",
        "query": "文件被Shift+Delete永久删除、回收站也清空了，在恢复之前应该先做什么、不该做什么，才能避免数据被覆盖？",
        "expected_facts": ["卷影副本", "停止", "快照", "Recuva"],
        "challenge_type": "多跳处置链 (停止写入→卷影副本→恢复软件) 完整召回",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-STO-001",
        "trap_ids": []
    },
    {
        "id": "HC-06",
        "category": "MFA时间偏差阈值与重新绑定",
        "query": "Authenticator验证码总是提示错误，手机时间和服务器时间偏差超过多少秒就会导致验证失败？",
        "expected_facts": ["30秒", "时间偏差", "时间校正"],
        "challenge_type": "精确阈值数字(30秒)硬匹配，单一意图聚焦根因小节",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-ACC-004",
        "trap_ids": []
    },
    {
        "id": "HC-07",
        "category": "DNS服务端口号硬约束",
        "query": "网页打不开但QQ正常，IT排查DNS时，要检查防火墙是否拦截了哪个端口？",
        "expected_facts": ["UDP 53", "53", "DNS"],
        "challenge_type": "精确端口号 53 硬匹配 (BM25强项)",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-NET-004",
        "trap_ids": []
    },
    # ---- 同义改写题：query 刻意不含卡片词面，考纯语义召回（Dense 主场，BM25 易脱靶）----
    {
        "id": "HC-08",
        "category": "同义改写·无线网排查",
        "query": "同事的笔记本在办公室连不上公司无线网，但手机连同一个网络却完全正常，应该怎么一步步排查？",
        "expected_facts": ["忘记此网络", "物理开关", "DHCP"],
        "challenge_type": "query 无 WiFi/无线局域网 等卡片词面（仅'无线网'），考语义对齐",
        "filter": None,
        "qtype": "paraphrase",
        "target_id": "ITKB-NET-001",
        "trap_ids": []
    },
    {
        "id": "HC-09",
        "category": "同义改写·打印无响应",
        "query": "点了打印按钮之后打印机毫无反应，之前发送的任务也都卡住不动了，怎么办？",
        "expected_facts": ["Print Spooler", "脱机", "打印队列"],
        "challenge_type": "query 为口语化描述，无'打印服务/队列'等术语词面，考语义召回",
        "filter": None,
        "qtype": "paraphrase",
        "target_id": "ITKB-HW-002",
        "trap_ids": []
    },
    {
        "id": "HC-10",
        "category": "同义改写·公式不刷新",
        "query": "Excel里改了明细数据，底下合计那一格的数字还是旧的，非得双击进去回车才会变，是哪里设置不对？",
        "expected_facts": ["计算选项", "循环引用", "F9"],
        "challenge_type": "query 无'公式/计算'词面，'合计不跟着变、双击才刷新'需语义映射到计算选项(手动/自动)",
        "filter": None,
        "qtype": "paraphrase",
        "target_id": "ITKB-OFF-004",
        "trap_ids": []
    },
    # ---- 近邻混淆题：答案唯一，但 query 字面刻意贴近同分类的"兄弟卡"（confusable_with）。
    # 双路召回按字面/向量相似度容易把兄弟卡顶上来，需要 Cross-Encoder 读懂"真实诉求"才能排对，
    # 用于量化精排环节相对 RRF 的真实增益（前 10 题四轨均已饱和，测不出差距）----
    {
        "id": "HC-11",
        "category": "近邻混淆·只收不到某人邮件",
        "query": "有位客户说邮件早就发给我了，也没收到任何退信，可我这边偏偏只收不到他的邮件，其他人发的都正常，应该怎么查？",
        "expected_facts": ["垃圾邮件", "白名单", "邮件追踪"],
        "challenge_type": "'发邮件/退信'字面贴近发送失败卡 MAIL-001，真实诉求是接收侧拦截(垃圾邮件/阻止发件人)",
        "filter": None,
        "qtype": "confusable",
        "target_id": "ITKB-MAIL-002",
        "confusable_with": "ITKB-MAIL-001",
        "trap_ids": []
    },
    {
        "id": "HC-12",
        "category": "近邻混淆·VPN已连接但内网不通",
        "query": "在家连公司VPN，客户端显示已经连上了，可OA和共享文件夹全都打不开，这算不算VPN连接失败，该怎么排查？",
        "expected_facts": ["路由", "内部DNS", "IP段冲突"],
        "challenge_type": "query 自带'VPN连接失败'字样（= VPN-001 标题），但现象是已连接、内网不通，答案在 VPN-002",
        "filter": None,
        "qtype": "confusable",
        "target_id": "ITKB-VPN-002",
        "confusable_with": "ITKB-VPN-001",
        "trap_ids": []
    },
    {
        "id": "HC-13",
        "category": "近邻混淆·改密后反复锁定",
        "query": "密码明明没有输错，登录却总提示账户已被锁定，前几天刚改过密码，是不是密码过期了？",
        "expected_facts": ["旧密码", "4740", "15-30分钟"],
        "challenge_type": "'改密码/密码过期'字面贴近密码重置卡 ACC-002，真实根因是其他设备用旧密码重试导致锁定(ACC-001)",
        "filter": None,
        "qtype": "confusable",
        "target_id": "ITKB-ACC-001",
        "confusable_with": "ITKB-ACC-002",
        "trap_ids": []
    },
    {
        "id": "HC-14",
        "category": "近邻混淆·单个共享文件夹无权限",
        "query": "共享盘里其他文件夹都能正常打开，唯独部门调整后新分给我的项目文件夹提示没有权限访问，怎么处理？",
        "expected_facts": ["安全组", "NTFS", "有效访问"],
        "challenge_type": "'共享盘/无法访问'字面贴近共享盘断连卡 STO-002，但只有单个文件夹无权限，答案是权限组问题(ACC-003)",
        "filter": None,
        "qtype": "confusable",
        "target_id": "ITKB-ACC-003",
        "confusable_with": "ITKB-STO-002",
        "trap_ids": []
    },
    # ---- 负样本题：知识库确无答案，理想行为是低置信拒答；命中 trap 卡即误召回 ----
    {
        "id": "NEG-01",
        "category": "负样本·Mac邮箱配置",
        "query": "MacBook 上的 Outlook for Mac 怎么添加公司 Exchange 邮箱账户？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 邮件卡只讲收发故障排查，无 macOS 客户端配置指引；'Outlook/Exchange' 与邮件卡字面撞车，考误召回",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-MAIL-001", "ITKB-MAIL-002"]
    },
    {
        "id": "NEG-02",
        "category": "负样本·Linux上装VPN",
        "query": "公司 VPN 在 Linux 系统上怎么安装配置客户端？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 的 VPN 卡只覆盖 Windows 客户端，Linux 无任何指引，考误召回",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-VPN-001", "ITKB-VPN-002", "ITKB-VPN-003"]
    },
    # NEG-03~06：原 2 道负样本不足以标定拒答阈值，补充"同主题但不同诉求"的库外题——
    # KB 只有故障排查卡，没有功能使用/配置教程，这类题字面极易撞上同主题故障卡
    {
        "id": "NEG-03",
        "category": "负样本·打印机双面默认设置",
        "query": "怎么把办公室打印机的默认打印方式设置成双面黑白，省得每次都手动选？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 打印机卡只讲'无法打印'故障处置，无打印首选项配置；'打印机/设置'字面撞车",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-HW-002"]
    },
    {
        "id": "NEG-04",
        "category": "负样本·Excel数据透视表",
        "query": "Excel 里怎么用数据透视表把销售明细按月份汇总求和？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 的 Excel 卡只讲公式不计算/文件损坏，无数据透视表教程；'Excel/汇总'字面撞车",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-OFF-004", "ITKB-OFF-001"]
    },
    {
        "id": "NEG-05",
        "category": "负样本·企业微信预约会议",
        "query": "企业微信里怎么预约一个线上会议并在会议中开启直播？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 的企业微信只出现在 IM 登录故障卡，无会议/直播功能说明；'企业微信'字面撞车",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-MAIL-003"]
    },
    {
        "id": "NEG-06",
        "category": "负样本·手机无线投屏",
        "query": "会议室的大屏怎么用手机无线投屏，需要装什么App？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 只有笔记本外接显示器有线连接故障卡，无手机无线投屏指引；'会议室/显示'语义撞车",
        "filter": None,
        "qtype": "negative",
        "target_id": None,
        "trap_ids": ["ITKB-HW-003"]
    }
]


# ==============================================================================
# 开发集（DEV）：原验证集，首轮已作为 hold-out 跑过一次（见讲义 6.7），之后降级为调参用
# ==============================================================================
# 题目设计：
#   - 正样本 HO-*（confusable）：query 刻意使用兄弟卡（confusable_with）的词汇与表述，
#     真实诉求只有目标卡能解答——专门制造 RRF 字面/向量相似度会排错、需要精排理解语义的场景；
#   - 负样本 HN-*（negative）：知识库确无答案，但存在一张主题极近的兄弟卡（trap_ids），
#     检验拒答阈值会不会被"很像但答非所问"的卡骗过。
# 首轮作为 hold-out 的结论（未调参时）：KSP qwen3-reranker-8b 误召回 2/7、正负分数重叠；
# qwen3.7-text-rerank 误召回 0/7。此后召回扩展、融合权重等参数在 主题集+本集 上调整。
DEV_SUITE = [
    {
        "id": "HO-01",
        "category": "验证·证书报错误判为DNS",
        "query": "电脑上打开网站都提示「您的连接不是私密连接」，同事的电脑访问同样的网址都正常，是不是我这台的DNS坏了？",
        "expected_facts": ["系统时间", "SSL证书", "清除浏览数据"],
        "challenge_type": "用户自判'DNS坏了'诱导到 NET-004；证书报错的真实根因(系统时间/缓存)在浏览器卡",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-SYS-005", "confusable_with": "ITKB-NET-004", "trap_ids": []
    },
    {
        "id": "HO-02",
        "category": "验证·Mac格式硬盘误判为误删",
        "query": "同事从苹果电脑拷了资料的移动硬盘，插到我的Windows电脑上提示需要格式化，里面的文件是不是丢了，怎么把数据恢复出来？",
        "expected_facts": ["APFS", "磁盘管理", "R-Studio"],
        "challenge_type": "'文件丢了/恢复数据'诱导到误删恢复卡 STO-001；真实根因是 Mac 文件系统不兼容(HW-004)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-HW-004", "confusable_with": "ITKB-STO-001", "trap_ids": []
    },
    {
        "id": "HO-03",
        "category": "验证·私接路由器误判为带宽占用",
        "query": "自从隔壁组自己接了一个无线路由器，我们这一片电脑就时不时断网，是不是网速带宽都被他们占了？",
        "expected_facts": ["私接路由器", "DHCP Snooping", "ipconfig /renew"],
        "challenge_type": "'断网/网速/带宽'诱导到网络断连卡 NET-003；私接路由器开 DHCP 导致的是 IP 冲突(NET-005)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-NET-005", "confusable_with": "ITKB-NET-003", "trap_ids": []
    },
    {
        "id": "HO-04",
        "category": "验证·Office卡死与打印机",
        "query": "最近一打开Word就卡死转圈，IT说可能跟打印机有关，可我根本没在打印东西，这是怎么回事？",
        "expected_facts": ["默认打印机", "Microsoft Print to PDF", "安全模式"],
        "challenge_type": "'打印机'诱导到打印故障卡 HW-002；答案是 Office 渲染依赖默认打印机驱动(OFF-002)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-OFF-002", "confusable_with": "ITKB-HW-002", "trap_ids": []
    },
    {
        "id": "HO-05",
        "category": "验证·更新回滚误判为电脑老旧",
        "query": "这几天每次开机都特别慢，要等很久，屏幕上总显示「撤销对计算机所做的更改」，是电脑太老了需要清理或者加内存吗？",
        "expected_facts": ["Windows Update", "SoftwareDistribution", "cleanmgr"],
        "challenge_type": "'开机慢/加内存'诱导到运行缓慢卡 SYS-004；'撤销更改'是更新安装失败回滚(SYS-003)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-SYS-003", "confusable_with": "ITKB-SYS-004", "trap_ids": []
    },
    {
        "id": "HO-06",
        "category": "验证·强制改密误判为锁定",
        "query": "早上登录提示必须先修改密码才能进系统，可我改了好几次都说新密码不符合要求，再这样试下去账号会不会被锁？",
        "expected_facts": ["复杂度", "90天", "自助密码重置"],
        "challenge_type": "'账号被锁'诱导到锁定卡 ACC-001；真实诉求是密码过期与复杂度要求(ACC-002)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-ACC-002", "confusable_with": "ITKB-ACC-001", "trap_ids": []
    },
    {
        "id": "HO-07",
        "category": "验证·路径过长误判为同步冲突",
        "query": "OneDrive 图标一直转圈显示正在同步，有个放在很多层子文件夹里的文件始终传不上去，是不是和别人同时编辑冲突了？",
        "expected_facts": ["256字符", "暂停同步", "onedrive.exe /reset"],
        "challenge_type": "'同时编辑冲突'诱导到 WPS 云文档冲突卡 OFF-003；深层目录是路径超长(STO-003)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-STO-003", "confusable_with": "ITKB-OFF-003", "trap_ids": []
    },
    {
        "id": "HO-08",
        "category": "验证·VPN已连但远程桌面失败",
        "query": "在家VPN已经连上了，可用远程桌面连工位电脑一直提示无法连接，工位电脑我下班前没关机，可能是什么原因？",
        "expected_facts": ["休眠", "3389", "NLA"],
        "challenge_type": "'VPN已连接但连不上公司电脑'贴近 VPN-002(已连接无法访问内网)；远程桌面专属根因在 VPN-003",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-VPN-003", "confusable_with": "ITKB-VPN-002", "trap_ids": []
    },
    {
        "id": "HO-09",
        "category": "验证·合盖外屏黑屏误判为无法开机",
        "query": "笔记本接着显示器，一合上盖子外面的屏幕就黑了，按电源键也没反应，是不是电脑开不了机了？",
        "expected_facts": ["合盖", "输入源", "Win+P"],
        "challenge_type": "'黑屏/按电源键无反应'诱导到无法开机卡 HW-001；合盖休眠导致外接屏无信号(HW-003)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-HW-003", "confusable_with": "ITKB-HW-001", "trap_ids": []
    },
    {
        "id": "HO-10",
        "category": "验证·换工位后网线不通",
        "query": "换了工位之后插上网线右下角一直是红叉，但连公司WiFi又是好的，应该怎么排查？",
        "expected_facts": ["网口指示灯", "VLAN", "交换机端口"],
        "challenge_type": "query 含'公司WiFi'诱导到 WiFi 卡 NET-001；实际是有线网口/交换机端口问题(NET-002)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-NET-002", "confusable_with": "ITKB-NET-001", "trap_ids": []
    },
    {
        "id": "HO-11",
        "category": "验证·业务软件闪退",
        "query": "公司新装的报销系统客户端一双击就闪退，Word、Excel 这些办公软件倒是都正常，需要检查哪些地方？",
        "expected_facts": ["VC++", "兼容模式", "事件 ID 1000"],
        "challenge_type": "'Word/Excel'字面诱导到 Office 崩溃卡 OFF-002；非 Office 软件闪退在 SYS-002",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-SYS-002", "confusable_with": "ITKB-OFF-002", "trap_ids": []
    },
    {
        "id": "HO-12",
        "category": "验证·企业微信登录超时误判为认证问题",
        "query": "企业微信一直提示登录超时，用手机热点就能登上，换回公司网络就不行，是不是我的账号认证出问题了？",
        "expected_facts": ["手机热点", "防火墙", "80/443"],
        "challenge_type": "'账号认证'诱导到 MFA 认证卡 ACC-004；热点可用说明是公司网络拦截 IM(MAIL-003)",
        "filter": None, "qtype": "confusable",
        "target_id": "ITKB-MAIL-003", "confusable_with": "ITKB-ACC-004", "trap_ids": []
    },
    # ---- 负样本：库内无答案，但有主题极近的兄弟卡 ----
    {
        "id": "HN-01",
        "category": "验证负样本·笔记本电池鼓包",
        "query": "笔记本电池鼓包把底壳都顶起来了，还能继续插电用吗，怎么申请换电池？",
        "expected_facts": [],
        "challenge_type": "库外：KB 只有'电池耗尽无法开机'与'主板电容鼓包'，无电池安全与更换流程",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-HW-001"]
    },
    {
        "id": "HN-02",
        "category": "验证负样本·Outlook自动回复",
        "query": "休假前怎么在 Outlook 里设置自动回复，让别人发邮件时收到我不在的提示？",
        "expected_facts": [],
        "challenge_type": "库外：KB 邮件卡只讲收发故障，无 Outlook 功能设置；'Outlook/邮件'字面撞车",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-MAIL-001", "ITKB-MAIL-002"]
    },
    {
        "id": "HN-03",
        "category": "验证负样本·查看已保存WiFi密码",
        "query": "电脑已经连着公司WiFi，但我忘了密码想给手机也连上，怎么在电脑里查看这个WiFi的密码？",
        "expected_facts": [],
        "challenge_type": "库外：WiFi 卡只讲连不上的排查（含'密码错误'根因），无查看已保存密码方法",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-NET-001"]
    },
    {
        "id": "HN-04",
        "category": "验证负样本·Excel设置打开密码",
        "query": "Excel 文件怎么设置打开密码，防止别人随便查看里面的工资数据？",
        "expected_facts": [],
        "challenge_type": "库外：OFF-001 只把'文件被加密'列为打不开的根因，无加密操作方法；OFF-004 同为 Excel 卡",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-OFF-001", "ITKB-OFF-004"]
    },
    {
        "id": "HN-05",
        "category": "验证负样本·离职账号交接",
        "query": "员工离职后，他的域账号和公司邮箱应该怎么交接、什么时候禁用？",
        "expected_facts": [],
        "challenge_type": "库外：ACC-001 只提到'离职员工账号未及时禁用被他人尝试登录'这一现象，无离职交接流程",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-ACC-001", "ITKB-ACC-002"]
    },
    {
        "id": "HN-06",
        "category": "验证负样本·远程桌面传文件",
        "query": "远程桌面连上工位电脑以后，怎么把家里电脑上的文件直接复制过去？",
        "expected_facts": [],
        "challenge_type": "库外：VPN-003 只讲远程桌面连不上的排查，无本地资源/剪贴板映射说明",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-VPN-003"]
    },
    {
        "id": "HN-07",
        "category": "验证负样本·自行安装开发软件",
        "query": "公司电脑上能不能自己安装 Python 和 VS Code 这类开发软件，需要走什么审批流程？",
        "expected_facts": [],
        "challenge_type": "库外：KB 只有软件闪退处置与 USB 禁用的审批提及，无软件安装规范",
        "filter": None, "qtype": "negative", "target_id": None,
        "trap_ids": ["ITKB-SYS-002", "ITKB-HW-004"]
    },
]

# 兼容旧名（首轮作为 hold-out 运行时的叫法）
HOLDOUT_SUITE = DEV_SUITE


# ==============================================================================
# 测试集（TEST）：2026-10-14 在任何调参之前一次性写好并封存，方案定稿后只运行一次
# ==============================================================================
# 纪律：调参期间不运行本集；定稿后跑一次如实记录。若此后再据本集结果改参数，
# 本集即失效，需另出新题。题目只对照卡片原文出题，出题时未运行任何检索。
# 构成：16 道正样本（近邻混淆 + 口语化/词表错位，如"蓝色的屏幕"≈蓝屏、"动态验证码"≈Authenticator）
#       + 10 道库外负样本（均有字面/主题相近的陷阱卡）。
TEST_SUITE = [
    {"id": "TO-01", "category": "测试·调岗后单个共享目录无权限",
     "query": "部门调整后，以前常用的那个共享文件夹打不开了，提示拒绝访问，同组其他人都能进，该怎么处理？",
     "expected_facts": ["安全组", "有效访问", "gpupdate /force"],
     "challenge_type": "'共享文件夹打不开'贴近共享盘断连卡 STO-002；只有自己无权限是权限组问题(ACC-003)",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-ACC-003", "confusable_with": "ITKB-STO-002", "trap_ids": []},
    {"id": "TO-02", "category": "测试·打印任务挂起",
     "query": "打印的时候提示文档被挂起了，后面同事发的也都排在那里出不来，怎么弄？",
     "expected_facts": ["打印队列", "Print Spooler", "spool"],
     "challenge_type": "口语'挂起/排着出不来'需映射到打印队列阻塞",
     "filter": None, "qtype": "paraphrase", "target_id": "ITKB-HW-002", "confusable_with": None, "trap_ids": []},
    {"id": "TO-03", "category": "测试·浏览器找不到服务器IP",
     "query": "QQ 和微信都能用，但浏览器所有网站都打不开，提示「找不到服务器 IP 地址」，怎么解决？",
     "expected_facts": ["nslookup", "ipconfig /flushdns", "223.5.5.5"],
     "challenge_type": "Chrome 中文报错文案与卡片英文错误码 ERR_NAME_NOT_RESOLVED 词表错位；浏览器卡 SYS-005 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-NET-004", "confusable_with": "ITKB-SYS-005", "trap_ids": []},
    {"id": "TO-04", "category": "测试·口语描述蓝屏",
     "query": "电脑用着用着突然变成整个蓝色的屏幕，上面一堆英文，然后自己就重启了，经常这样怎么办？",
     "expected_facts": ["mdsched", "BlueScreenView", "sfc /scannow"],
     "challenge_type": "'蓝色的屏幕+一堆英文'需映射到蓝屏(BSOD)，无'蓝屏'词面",
     "filter": None, "qtype": "paraphrase", "target_id": "ITKB-SYS-001", "confusable_with": None, "trap_ids": []},
    {"id": "TO-05", "category": "测试·映射盘红叉",
     "query": "周一来上班，电脑里那个映射的 Z 盘出现了红叉，双击说找不到网络路径，怎么恢复？",
     "expected_facts": ["凭据", "重新映射", "SMB"],
     "challenge_type": "'Z盘/网络路径'需对齐共享盘卡；权限卡 ACC-003 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-STO-002", "confusable_with": "ITKB-ACC-003", "trap_ids": []},
    {"id": "TO-06", "category": "测试·U盘拷来的表格打不开",
     "query": "从 U 盘拷过来的 Excel 报表，双击提示文件格式和扩展名不匹配，打不开怎么办？",
     "expected_facts": ["打开并修复", "另存为", "解除锁定"],
     "challenge_type": "'U盘/Excel'字面诱导到 U 盘卡 HW-004 与 Excel 公式卡；答案是文档损坏卡 OFF-001",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-OFF-001", "confusable_with": "ITKB-HW-004", "trap_ids": []},
    {"id": "TO-07", "category": "测试·酒店拨不上远程连接",
     "query": "出差住酒店，公司那个远程连接软件一直拨不上，用手机热点倒是能连，怎么回事？",
     "expected_facts": ["SSL VPN", "手机热点", "L2TP"],
     "challenge_type": "'远程连接'贴近远程桌面卡 VPN-003；'拨不上/酒店'实为 VPN 拨号失败(VPN-001)",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-VPN-001", "confusable_with": "ITKB-VPN-003", "trap_ids": []},
    {"id": "TO-08", "category": "测试·换手机动态验证码不对",
     "query": "换了新手机以后，登录公司系统要输的那个动态验证码一直提示不对，怎么处理？",
     "expected_facts": ["重新绑定", "时间", "Authenticator"],
     "challenge_type": "'动态验证码'与 Authenticator/MFA 词表错位；密码卡 ACC-002 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-ACC-004", "confusable_with": "ITKB-ACC-002", "trap_ids": []},
    {"id": "TO-09", "category": "测试·视频会议卡顿丢包",
     "query": "开视频会议一直卡，ping 网关老是超时，有时候延迟好几百毫秒，要怎么排查？",
     "expected_facts": ["Wireshark", "ARP", "114.114.114.114"],
     "challenge_type": "网络质量问题；WiFi 卡 NET-001 与 IM 卡 MAIL-003 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-NET-003", "confusable_with": "ITKB-NET-001", "trap_ids": []},
    {"id": "TO-10", "category": "测试·磁盘100%",
     "query": "电脑越用越卡，任务管理器里磁盘一直 100%，开个网页都要等半天，怎么办？",
     "expected_facts": ["CrystalDiskInfo", "SSD", "开机自启"],
     "challenge_type": "运行缓慢卡；'开网页慢'贴近浏览器卡 SYS-005",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-SYS-004", "confusable_with": "ITKB-SYS-005", "trap_ids": []},
    {"id": "TO-11", "category": "测试·鼠标单击变双击",
     "query": "鼠标点一下变成了双击，拖文件的时候老是拖不动，是什么问题？",
     "expected_facts": ["双击速度", "USB接收器", "Keyboard Test Utility"],
     "challenge_type": "键鼠卡；常规口语题",
     "filter": None, "qtype": "paraphrase", "target_id": "ITKB-HW-005", "confusable_with": None, "trap_ids": []},
    {"id": "TO-12", "category": "测试·在线表格冲突副本",
     "query": "两个人同时改了同一个 WPS 在线表格，现在多出来一个冲突的副本，我改的内容不见了，怎么找回？",
     "expected_facts": ["历史版本", "WPS协作", "冲突的副本"],
     "challenge_type": "WPS 云文档冲突卡；云盘同步卡 STO-003 与误删卡 STO-001 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-OFF-003", "confusable_with": "ITKB-STO-003", "trap_ids": []},
    {"id": "TO-13", "category": "测试·大附件卡在发件箱",
     "query": "发给客户的报价单附件太大了，邮件一直卡在发件箱里发不出去，怎么办？",
     "expected_facts": ["20-50MB", "云盘链接", "脱机工作"],
     "challenge_type": "发送失败卡；接收失败卡 MAIL-002 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-MAIL-001", "confusable_with": "ITKB-MAIL-002", "trap_ids": []},
    {"id": "TO-14", "category": "测试·新笔记本搜不到无线",
     "query": "新领的笔记本搜不到公司的无线信号，旁边同事的电脑都能搜到，怎么排查？",
     "expected_facts": ["物理开关", "驱动", "MAC地址"],
     "challenge_type": "'无线信号'≈WiFi；有线卡 NET-002 是陷阱",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-NET-001", "confusable_with": "ITKB-NET-002", "trap_ids": []},
    {"id": "TO-15", "category": "测试·共享盘整个目录被删",
     "query": "共享盘里我们组的一个文件夹被人整个删掉了，还能找回来吗？",
     "expected_facts": ["卷影副本", "以前的版本", "快照"],
     "challenge_type": "误删恢复卡；'共享盘'诱导到共享盘断连卡 STO-002",
     "filter": None, "qtype": "confusable", "target_id": "ITKB-STO-001", "confusable_with": "ITKB-STO-002", "trap_ids": []},
    {"id": "TO-16", "category": "测试·更新下载一半报错",
     "query": "电脑右下角一直提醒要更新，点了更新下载到一半就报错，重试好几次都一样，怎么处理？",
     "expected_facts": ["services.msc", "DISM", "catalog.update.microsoft.com"],
     "challenge_type": "无错误码、无'安装失败'词面的口语描述，需对齐 Windows 更新失败卡",
     "filter": None, "qtype": "paraphrase", "target_id": "ITKB-SYS-003", "confusable_with": None, "trap_ids": []},
    # ---- 库外负样本 ----
    {"id": "TN-01", "category": "测试负样本·连接蓝牙音箱", "query": "公司电脑怎么连接会议室的蓝牙音箱放声音？",
     "expected_facts": [], "challenge_type": "库外；键鼠卡含蓝牙配对步骤", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-HW-005", "ITKB-HW-003"]},
    {"id": "TN-02", "category": "测试负样本·共享Outlook日历", "query": "怎么在 Outlook 里把我的日历共享给同事查看？",
     "expected_facts": [], "challenge_type": "库外；Outlook 字面撞邮件卡", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-MAIL-001", "ITKB-MAIL-002"]},
    {"id": "TN-03", "category": "测试负样本·扫描发邮箱", "query": "怎么用办公室的打印机把纸质文件扫描后直接发到我的邮箱？",
     "expected_facts": [], "challenge_type": "库外；'打印机/邮箱'双重字面陷阱", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-HW-002", "ITKB-MAIL-001"]},
    {"id": "TN-04", "category": "测试负样本·定时自动关机", "query": "Windows 电脑怎么设置每天晚上定时自动关机？",
     "expected_facts": [], "challenge_type": "库外；系统类卡片字面相近", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-SYS-004", "ITKB-SYS-003", "ITKB-HW-001"]},
    {"id": "TN-05", "category": "测试负样本·访客WiFi申请", "query": "来访客户能不能连公司 WiFi，访客网络要怎么申请？",
     "expected_facts": [], "challenge_type": "库外；WiFi 卡 + STO-002'访客登录'字面撞车", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-NET-001", "ITKB-STO-002"]},
    {"id": "TN-06", "category": "测试负样本·Excel删除重复", "query": "Excel 表格里有很多重复的行，怎么批量删除重复数据？",
     "expected_facts": [], "challenge_type": "库外；Excel 卡字面撞车", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-OFF-004", "ITKB-OFF-001"]},
    {"id": "TN-07", "category": "测试负样本·护眼模式", "query": "电脑屏幕怎么开护眼模式，晚上看着不那么刺眼？",
     "expected_facts": [], "challenge_type": "库外；显示器卡字面相近", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-HW-003"]},
    {"id": "TN-08", "category": "测试负样本·企业微信记录迁移", "query": "企业微信的聊天记录怎么迁移到新手机上？",
     "expected_facts": [], "challenge_type": "库外；企业微信只出现在 IM 登录卡", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-MAIL-003"]},
    {"id": "TN-09", "category": "测试负样本·U盘加密", "query": "U 盘怎么加密，防止丢了被别人看到里面的资料？",
     "expected_facts": [], "challenge_type": "库外；U 盘卡字面撞车", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-HW-004"]},
    {"id": "TN-10", "category": "测试负样本·预约会议室", "query": "怎么用公司邮箱预约会议室？",
     "expected_facts": [], "challenge_type": "库外；邮箱字面撞邮件卡", "filter": None, "qtype": "negative",
     "target_id": None, "trap_ids": ["ITKB-MAIL-001", "ITKB-MAIL-002", "ITKB-HW-003"]},
]


# ==============================================================================
# 4. 主流程控制器与四轨评测大比武
# ==============================================================================

