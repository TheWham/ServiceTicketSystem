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
#   3) negative（NEG-01~02）：知识库无答案，考误召回/拒答能力（trap_ids 为易误召卡）。
# 打分方式（替代旧的"Top-3 拼接文本子串覆盖"，后者因高频通用词与整卡回溯而饱和）：
#   - 卡级 Recall@3 / MRR：目标卡 wiki_id 在回溯父块序列中的名次；
#   - 事实覆盖：expected_facts 只在"检索到的目标卡正文"内计数，目标卡未召回记 0；
#   - 负样本误召回率：Top-3 父块是否命中 trap_ids。
HARD_BENCHMARK_SUITE = [
    {
        "id": "HC-01",
        "category": "系统修复命令硬匹配",
        "query": "Windows系统文件损坏，应该用什么命令来扫描并修复？",
        "expected_facts": ["sfc /scannow", "系统文件"],
        "challenge_type": "精确命令字符串匹配 (向量易漂移，BM25强项)",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-SYS-001",
        "trap_ids": []
    },
    {
        "id": "HC-02",
        "category": "VPN错误代码与协议推荐",
        "query": "VPN连接报错806通常是什么原因？官方推荐切换到哪种协议穿透性最好？",
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
        "query": "域账号被锁定，IT工程师如何查安全日志定位是哪个设备在尝试登录？",
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
        "query": "发邮件收到退信提示550 Mailbox not found，最可能是什么问题？",
        "expected_facts": ["550", "收件人", "地址"],
        "challenge_type": "退信代码 550 与根因(收件人地址错误)关联",
        "filter": None,
        "qtype": "hard",
        "target_id": "ITKB-MAIL-001",
        "trap_ids": []
    },
    {
        "id": "HC-05",
        "category": "文件误删恢复与防覆盖",
        "query": "文件被Shift+Delete永久删除且已清空回收站，如何恢复？恢复前要注意什么防止数据被覆盖？",
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
        "query": "Authenticator验证码总是提示错误，手机时间偏差超过多少秒会导致失败？换手机后如何处理？",
        "expected_facts": ["30秒", "时间", "重新绑定"],
        "challenge_type": "精确阈值数字(30秒)与处置动作关联",
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
        "query": "表格里改了原始数据，汇总列的数字却一直不跟着变，要检查哪些设置？",
        "expected_facts": ["计算选项", "循环引用", "F9"],
        "challenge_type": "query 无'公式不计算'词面，'汇总列不更新'需语义映射到计算选项",
        "filter": None,
        "qtype": "paraphrase",
        "target_id": "ITKB-OFF-004",
        "trap_ids": []
    },
    # ---- 负样本题：知识库确无答案，理想行为是低置信拒答；命中 trap 卡即误召回 ----
    {
        "id": "NEG-01",
        "category": "负样本·Mac邮箱配置",
        "query": "Mac 笔记本如何配置公司邮箱客户端（Outlook for Mac）？",
        "expected_facts": [],
        "challenge_type": "库外问题：KB 仅有 Windows 邮件卡；'Mac' 与 NET 卡'MAC地址'字面撞车，考误召回",
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
    }
]


# ==============================================================================
# 4. 主流程控制器与四轨评测大比武
# ==============================================================================

