# -*- coding: utf-8 -*-
"""MCP Service 核心数据契约与数据模型定义。

包含：
- 企业 IT 末级分类白名单字典与描述
- 工单优先级约束
- 工单草稿数据类 (TicketDraft)
- 工具返回通用信封 (ToolResultEnvelope)
"""
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional

# 企业系统启用的末级有效分类字典
VALID_CATEGORIES: Dict[str, Dict[str, str]] = {
    "C_HW_PC": {
        "id": "C_HW_PC",
        "name": "PC与电脑硬件",
        "description": "台式机/笔记本/显示器/键盘鼠标等硬件损坏、开机黑屏、配件更换",
    },
    "C_HW_PR": {
        "id": "C_HW_PR",
        "name": "打印机与外设",
        "description": "办公室共享打印机卡纸/缺墨/扫描仪连接故障与驱动问题",
    },
    "C_SW": {
        "id": "C_SW",
        "name": "办公软件与授权",
        "description": "办公软件、系统激活、正版授权申请与客户端崩溃报错",
    },
    "C_NET": {
        "id": "C_NET",
        "name": "办公网络与VPN",
        "description": "工位网口亮红灯、Wi-Fi 掉线、远程 VPN 拨号失败及网络限速",
    },
    "C_ACC": {
        "id": "C_ACC",
        "name": "账号权限与密码",
        "description": "域账号密码锁定/重置、邮箱登录异常、ERP/代码仓等系统权限申请",
    },
    "C_OTH": {
        "id": "C_OTH",
        "name": "其他IT支持",
        "description": "未归类办公 IT 支持、设备搬迁咨询与综合故障",
    },
}

VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}
DEFAULT_CATEGORY_FALLBACK = "C_OTH"
DEFAULT_PRIORITY_FALLBACK = "MEDIUM"


@dataclass
class TicketDraft:
    """工单草稿数据类（仅用于前端人机复核，不自动持久化写入数据库）。"""
    title: str
    description: str
    category: str = DEFAULT_CATEGORY_FALLBACK
    priority: str = DEFAULT_PRIORITY_FALLBACK

    def __post_init__(self):
        # 规整与防呆校验
        self.title = (self.title or "").strip()
        self.description = (self.description or "").strip()

        # 分类校验
        if self.category not in VALID_CATEGORIES:
            self.category = DEFAULT_CATEGORY_FALLBACK

        # 优先级校验
        up_prio = (self.priority or "").upper().strip()
        if up_prio not in VALID_PRIORITIES:
            self.priority = DEFAULT_PRIORITY_FALLBACK
        else:
            self.priority = up_prio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "category_name": VALID_CATEGORIES.get(self.category, {}).get("name", "其他"),
            "priority": self.priority,
        }


@dataclass
class CategoryItem:
    id: str
    name: str
    description: str


@dataclass
class ToolResultEnvelope:
    """统一 MCP 工具结果信封，便于格式化为纯文本或 JSON 返回给模型。"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    def to_text(self) -> str:
        if self.success:
            if isinstance(self.data, str):
                return self.data
            return json.dumps(self.data, ensure_ascii=False, indent=2)
        else:
            return f"❌ 执行失败: {self.error or '未知错误'}"
