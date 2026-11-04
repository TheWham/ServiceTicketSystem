# -*- coding: utf-8 -*-
"""run_cost_governance_web_demo.py

企业级 IT 智能服务台 (IT Service Desk) 成本治理与 Model Router 动态选模全景交互控制台 Web Demo。
深度契合项目 IT Service Desk 设计规范 (深空蓝黑 + 电光青未来科技感双栏大屏)。

核心能力演示：
1. 聚焦“未命中语义缓存之后的流程模型”；
2. 接入截图模型梯队：qwen3.7-flash (LITE)、qwen3.7-plus (STANDARD)、qwen3.8-max (PREMIUM)；
3. 保留 .env 中的 LLM_BASE_URL (https://kspmas.ksyun.com/v1) 与 LLM_API_KEY；
4. 真实 Server-Sent Events (SSE) 流式打字机输出；
5. 全阶段透明化决策与记账大盘（特征打分 -> 路由裁决 -> 预算审查与降级 -> 真实调用 -> 费用结算）；
6. 实时预算控制台：一键模拟低额降档与 429 熔断拦截。
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 引入 dotenv 与 OpenAI SDK
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

from openai import OpenAI

# 引入本地成本治理核心引擎与 RAG 检索客户端
from cost_governance import (
    BudgetExceeded,
    CostGovernor,
    ModelRouter,
    ModelTier,
    MODEL_CATALOG,
    RagRetrievalClient,
    SYSTEM_PROMPT_RESERVE,
    TokenBudgetManager,
    estimate_cost,
    estimate_tokens,
)

PORT = 8991
API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://kspmas.ksyun.com/v1")

# 初始化 OpenAI 客户端
openai_client = None
if API_KEY and BASE_URL:
    try:
        openai_client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0)
    except Exception as e:
        print(f"⚠️ OpenAI client init warning: {e}")

# 初始化共享单例：ModelRouter 由大模型 qwen3.7-flash 驱动自主意图判决
budget_manager = TokenBudgetManager(
    per_request_cap=6000,
    user_daily_limit=30000,
    dept_monthly_limit=500000,
)
router = ModelRouter(client=openai_client)
governor = CostGovernor(router, budget_manager)
rag_client = RagRetrievalClient()


# ==============================================================================
# HTML / CSS / JS 前端代码（严格符合 MASTER.md 设计系统与项目亮色主题）
# ==============================================================================

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IT Service Desk · 智能服务台 · 成本治理与选模控制台</title>
    <style>
        :root {
            /* 严格映射 MASTER.md 与 future-desk.css 亮色设计系统 */
            --future-accent: #08758C;
            --future-secondary: #245DCE;
            --future-glow: rgba(17, 135, 177, 0.12);
            --future-line: rgba(26, 127, 165, 0.22);
            --future-grid: rgba(16, 112, 151, 0.045);

            --bg-page: #EDF4FA;
            --bg-surface: #FFFFFF;
            --bg-card: #FFFFFF;
            --bg-subtle: #F4F8FC;
            --bg-subtle-hover: #EBF3FA;

            --border-color: #D3E2ED;
            --border-light: #E2ECF4;
            --border-focus: #245DCE;

            --text-primary: #10273D;
            --text-regular: #35516A;
            --text-secondary: #476176;
            --text-dim: #7A93A6;

            --accent-cyan: #08758C;
            --accent-blue: #245DCE;
            --accent-btn-from: #166BA5;
            --accent-btn-to: #245DCE;

            --status-success: #15803D;
            --status-success-bg: #F0FDF4;
            --status-success-border: #BBF7D0;

            --status-warning: #92400E;
            --status-warning-bg: #FFFBEB;
            --status-warning-border: #FDE68A;

            --status-danger: #B91C1C;
            --status-danger-bg: #FEF2F2;
            --status-danger-border: #FECACA;

            --status-purple: #7E22CE;
            --status-purple-bg: #FAF5FF;
            --status-purple-border: #E9D5FF;

            --desk-shadow: 0 4px 20px rgba(14, 67, 102, 0.04);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        html, body {
            height: 100%;
            width: 100%;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.5;
            font-size: 13px;
        }

        /* 主视口布局：全宽银白冰蓝主工作台 */
        .app-layout {
            display: flex;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
        }

        /* 顶部品牌 Logo (直接融入顶栏左侧) */
        .header-brand-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .brand-monogram {
            width: 32px;
            height: 32px;
            color: #A4F1FC;
            background: linear-gradient(135deg, #143E58, #112448);
            border: 1px solid #428DA9;
            border-radius: 8px;
            box-shadow: inset 0 0 12px rgba(72, 219, 246, 0.12), 0 0 12px rgba(39, 175, 216, 0.12);
            font-family: ui-monospace, Consolas, monospace;
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            letter-spacing: -0.5px;
        }
        .brand-text { display: flex; flex-direction: column; }
        .brand-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: 0.5px;
        }
        .brand-sub {
            font-size: 8px;
            font-family: ui-monospace, Consolas, monospace;
            color: var(--future-accent);
            letter-spacing: 1px;
        }

        /* ==============================================================================
           右侧主内容区（银白冰蓝背景 + 精细网格未来感）
           ============================================================================== */
        .desk-main-content {
            flex: 1;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-color: var(--bg-page);
            background-image: 
                radial-gradient(ellipse at 12% 0%, var(--future-glow), transparent 50%),
                radial-gradient(ellipse at 95% 0%, rgba(65, 100, 226, 0.04), transparent 40%),
                linear-gradient(var(--future-grid) 1px, transparent 1px),
                linear-gradient(90deg, var(--future-grid) 1px, transparent 1px);
            background-size: auto, auto, 40px 40px, 40px 40px;
            background-attachment: local;
        }

        /* 顶部通栏 Header */
        .desk-top-header {
            height: 52px;
            min-height: 52px;
            background: rgba(255, 255, 255, 0.92);
            border-bottom: 1px solid var(--border-color);
            backdrop-filter: blur(14px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            box-shadow: 0 1px 3px rgba(16, 39, 61, 0.03);
            position: relative;
            z-index: 5;
        }
        .desk-top-header::after {
            content: '';
            position: absolute;
            height: 1px;
            bottom: -1px;
            left: 24px;
            width: 140px;
            background: linear-gradient(90deg, var(--future-accent), transparent);
            pointer-events: none;
        }
        .breadcrumb-box {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }
        .breadcrumb-item { color: var(--text-secondary); }
        .breadcrumb-sep { color: var(--border-color); }
        .breadcrumb-current { color: var(--text-primary); font-weight: 600; }

        .header-right-tools {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .model-status-pill {
            background: #EEF6FC;
            color: var(--future-accent);
            border: 1px solid #C5D8E7;
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
        }
        .pulse-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10B981;
            animation: statusPulse 2s infinite;
        }
        @keyframes statusPulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

        .notify-badge {
            position: relative;
            display: flex;
            align-items: center;
            cursor: pointer;
        }
        .notify-count {
            position: absolute;
            top: -6px;
            right: -8px;
            background: #DC2626;
            color: #FFFFFF;
            font-size: 9px;
            font-weight: bold;
            padding: 1px 4px;
            border-radius: 8px;
            border: 1px solid #FFFFFF;
        }
        .theme-icon {
            display: flex;
            align-items: center;
            cursor: pointer;
            color: var(--text-secondary);
        }
        .theme-icon:hover { color: var(--future-accent); }
        .user-profile-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #F1F7FC;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 2px 10px 2px 3px;
            cursor: pointer;
        }
        .user-avatar {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: linear-gradient(135deg, #08758C, #245DCE);
            color: #FFFFFF;
            font-size: 11px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .user-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
        .user-role { font-size: 10px; color: var(--text-dim); }

        /* 智能服务次级 Banner（同截图样式） */
        .desk-sub-banner {
            background: #EEF6FC;
            border-bottom: 1px solid #DCE8F2;
            padding: 8px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .banner-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .eyebrow-tag {
            font-family: ui-monospace, Consolas, monospace;
            font-size: 10px;
            font-weight: 700;
            color: var(--future-accent);
            letter-spacing: 1.5px;
        }
        .banner-title {
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
        }
        .banner-right {
            font-size: 11px;
            color: var(--text-secondary);
        }

        /* 主工作区双栏 */
        .workspace-grid {
            flex: 1;
            display: grid;
            grid-template-columns: 1.15fr 1fr;
            gap: 16px;
            padding: 16px 24px;
            overflow: hidden;
            box-sizing: border-box;
        }

        /* ==============================================================================
           左栏：会话问答交互大屏 (白底白卡，精致边框与柔和投影)
           ============================================================================== */
        .chat-column {
            display: flex;
            flex-direction: column;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 16px;
            overflow: hidden;
            box-shadow: var(--desk-shadow);
        }

        /* 预置场景触发器 */
        .preset-section {
            margin-bottom: 10px;
            border-bottom: 1px solid #E5EDF5;
            padding-bottom: 10px;
        }
        .preset-title {
            font-size: 11px;
            color: var(--text-secondary);
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .preset-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .preset-btn {
            background: #F4F8FC;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            padding: 5px 9px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        .preset-btn:hover {
            border-color: var(--future-accent);
            background: #EBF5FE;
            color: var(--future-accent);
            transform: translateY(-1px);
        }
        .preset-btn.active-preset {
            border-color: var(--accent-blue) !important;
            background: #E3F2FD !important;
            color: var(--accent-blue) !important;
            font-weight: 600;
            box-shadow: 0 0 8px rgba(36, 93, 206, 0.2);
        }

        .preset-tag {
            font-size: 9px;
            padding: 1px 5px;
            border-radius: 4px;
            font-weight: 600;
        }
        .tag-lite { background: #F0FDF4; color: var(--status-success); border: 1px solid var(--status-success-border); }
        .tag-std { background: #EFF6FF; color: var(--accent-blue); border: 1px solid #BFDBFE; }
        .tag-prem { background: #FAF5FF; color: var(--status-purple); border: 1px solid var(--status-purple-border); }
        .tag-degrade { background: #FFFBEB; color: var(--status-warning); border: 1px solid var(--status-warning-border); }
        .tag-fuse { background: #FEF2F2; color: var(--status-danger); border: 1px solid var(--status-danger-border); }

        /* 聊天消息区 */
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding-right: 6px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            margin-bottom: 12px;
        }
        .chat-box::-webkit-scrollbar { width: 5px; }
        .chat-box::-webkit-scrollbar-track { background: transparent; }
        .chat-box::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }

        .chat-msg {
            display: flex;
            flex-direction: column;
            max-width: 92%;
            animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        /* 用户气泡：深海渐变蓝白字 */
        .msg-user { align-self: flex-end; }
        .msg-user .msg-bubble {
            background: linear-gradient(115deg, #12699B, #245DCE);
            color: #FFFFFF;
            border-radius: 12px 12px 2px 12px;
            padding: 10px 14px;
            box-shadow: 0 2px 8px rgba(36, 93, 206, 0.16);
            line-height: 1.6;
            font-size: 13px;
        }

        /* 助理气泡：纯白卡片，蓝灰细边框，精致头像与反馈条 (同项目截图) */
        .msg-assistant {
            align-self: flex-start;
            width: 100%;
            max-width: 100%;
        }
        .msg-assistant .assistant-card-inner {
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            border-radius: 12px 12px 12px 2px;
            padding: 12px 16px;
            box-shadow: 0 2px 10px rgba(16, 39, 61, 0.04);
        }
        .msg-assistant .msg-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #EDF4FA;
        }
        .assistant-avatar-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #EEF6FC;
            color: var(--future-accent);
            border: 1px solid #C5D8E7;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }
        .assistant-title-text {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-primary);
        }
        .assistant-sub-text {
            font-size: 11px;
            color: var(--text-dim);
        }
        .msg-header-right {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* 深度思考过程折叠条（冰蓝底色与青色细边） */
        .msg-thinking {
            background: #F0F7FF;
            border-left: 3px solid var(--future-accent);
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 11px;
            color: var(--future-accent);
            margin-bottom: 10px;
            line-height: 1.5;
            max-height: 140px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: ui-monospace, Consolas, monospace;
        }

        .assistant-content-text {
            color: var(--text-primary);
            font-size: 13px;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .msg-footer-stats {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 10px;
            color: var(--text-dim);
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid #EDF4FA;
        }

        /* 熔断告警卡片 */
        .msg-breaker .assistant-card-inner {
            background: #FFF1F0 !important;
            border: 1px solid #FFA39E !important;
            color: var(--status-danger) !important;
        }

        /* 知识库溯源卡片组件 */
        .citations-card {
            margin-top: 12px;
            border-top: 1px dashed var(--border-color);
            padding-top: 10px;
        }
        .citations-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            font-weight: 600;
            color: var(--future-accent);
            cursor: pointer;
            padding: 4px 10px;
            background: #F1F7FC;
            border-radius: 6px;
            border: 1px solid #C5D8E7;
            user-select: none;
            transition: background 0.15s ease;
        }
        .citations-header:hover {
            background: #E5F0FA;
        }
        .cite-arrow {
            font-size: 10px;
            transition: transform 0.2s ease;
        }
        .cite-arrow.rotate {
            transform: rotate(-90deg);
        }
        .citations-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 8px;
        }
        .citations-list.hidden {
            display: none;
        }
        .citation-item {
            background: #FAFCFF;
            border: 1px solid #E2EBF2;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 11px;
        }
        .citation-head {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
            flex-wrap: wrap;
        }
        .citation-idx {
            font-size: 10px;
            background: #E0EDF8;
            color: var(--future-accent);
            padding: 1px 5px;
            border-radius: 4px;
            font-weight: 600;
        }
        .citation-title {
            color: var(--text-primary);
            font-weight: 600;
        }
        .citation-score {
            font-size: 10px;
            color: #059669;
            background: #ECFDF5;
            padding: 1px 5px;
            border-radius: 4px;
            border: 1px solid #A7F3D0;
        }
        .citation-ver {
            font-size: 9px;
            color: var(--text-dim);
            font-family: monospace;
            margin-left: auto;
        }
        .citation-snippet {
            color: var(--text-secondary);
            font-size: 11px;
            line-height: 1.45;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* 输入区（白卡高保真） */
        .chat-input-bar {
            display: flex;
            flex-direction: column;
            gap: 6px;
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 8px 12px;
            box-shadow: 0 2px 8px rgba(16, 39, 61, 0.04);
            transition: border-color 0.2s;
        }
        .chat-input-bar:focus-within {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(36, 93, 206, 0.1);
        }
        .chat-input-controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
            padding-bottom: 4px;
            border-bottom: 1px solid #F1F5F9;
        }
        .input-tags { display: flex; align-items: center; gap: 8px; }
        .input-select {
            background: #F4F8FC;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            outline: none;
            cursor: pointer;
        }
        .chat-textarea {
            width: 100%;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-size: 13px;
            outline: none;
            resize: none;
            height: 44px;
            font-family: inherit;
            line-height: 1.5;
        }
        .chat-textarea::placeholder { color: var(--text-dim); }

        /* 输入区底部操作条（完全贴合截图布局） */
        .chat-input-bottom {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 4px;
        }
        .bottom-actions-left {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .btn-ghost-tool {
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .btn-ghost-tool:hover {
            border-color: var(--future-accent);
            background: #F1F7FC;
            color: var(--future-accent);
        }
        .hint-text {
            font-size: 11px;
            color: var(--text-dim);
            margin-left: 6px;
        }

        .bottom-actions-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .word-counter {
            font-size: 11px;
            color: var(--text-dim);
            font-family: ui-monospace, Consolas, monospace;
        }
        .btn-clear {
            background: none;
            border: none;
            color: var(--status-danger);
            font-size: 11px;
            cursor: pointer;
            padding: 4px 6px;
            transition: opacity 0.2s;
        }
        .btn-clear:hover { opacity: 0.8; text-decoration: underline; }
        .btn-send {
            background-image: linear-gradient(112deg, var(--accent-btn-from), var(--accent-btn-to));
            color: #FFFFFF;
            border: 1px solid #377DDA;
            border-radius: 6px;
            padding: 5px 18px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(36, 93, 206, 0.22);
            white-space: nowrap;
        }
        .btn-send:hover {
            background-image: linear-gradient(112deg, #126592, #1F52BA);
            box-shadow: 0 4px 14px rgba(36, 93, 206, 0.3);
            transform: translateY(-1px);
        }
        .btn-send:disabled {
            background: #CBD5E1;
            border-color: #94A3B8;
            color: #64748B;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }

        /* ==============================================================================
           右栏：成本治理透明化控制大盘 (白底白卡，银白冰蓝细部填充)
           ============================================================================== */
        .audit-column {
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .audit-column::-webkit-scrollbar { width: 5px; }
        .audit-column::-webkit-scrollbar-track { background: transparent; }
        .audit-column::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }

        .audit-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 13px 16px;
            position: relative;
            transition: all 0.2s;
            box-shadow: var(--desk-shadow);
        }
        .audit-card:hover {
            border-color: #A3BFD6;
        }
        .audit-card.active-stage {
            border-color: var(--future-accent) !important;
            box-shadow: 0 0 0 1px var(--future-accent), 0 4px 16px rgba(8, 117, 140, 0.12) !important;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .card-title {
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-primary);
        }
        .stage-badge {
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 4px;
            background: #EEF6FC;
            color: var(--future-accent);
            border: 1px solid #C5D8E7;
            font-family: ui-monospace, Consolas, monospace;
            font-weight: 600;
        }

        /* 预算指标仪表格 */
        .budget-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        .budget-metric {
            background: var(--bg-subtle);
            border: 1px solid var(--border-light);
            border-radius: 8px;
            padding: 8px 10px;
        }
        .metric-label {
            font-size: 11px;
            color: var(--text-secondary);
            margin-bottom: 4px;
            display: flex;
            justify-content: space-between;
        }
        .metric-val {
            font-size: 14px;
            font-weight: bold;
            color: var(--future-accent);
            font-family: ui-monospace, Consolas, monospace;
        }
        .progress-bar-bg {
            height: 6px;
            background: #E2ECF4;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 6px;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10B981, #245DCE);
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        .progress-warning {
            background: linear-gradient(90deg, #F59E0B, #EF4444) !important;
        }

        .budget-actions {
            display: flex;
            gap: 6px;
        }
        .btn-action {
            flex: 1;
            background: #FFFFFF;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 5px;
            padding: 5px 6px;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
            font-weight: 500;
        }
        .btn-action:hover {
            border-color: var(--future-accent);
            background: #EEF6FC;
            color: var(--future-accent);
        }
        .btn-action.btn-danger {
            background: #FEF2F2;
            border-color: #FECACA;
            color: var(--status-danger);
        }
        .btn-action.btn-danger:hover {
            border-color: #EF4444;
            background: #FEE2E2;
        }

        /* 阶段卡片内键值展示 */
        .stage-table {
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
        }
        .stage-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-subtle);
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-light);
        }
        .stage-label { color: var(--text-secondary); }
        .stage-val { font-weight: 500; font-family: ui-monospace, Consolas, monospace; color: var(--text-primary); }

        .tag-pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-lite { background: #F0FDF4; color: var(--status-success); border: 1px solid var(--status-success-border); }
        .badge-standard { background: #EFF6FF; color: var(--accent-blue); border: 1px solid #BFDBFE; }
        .badge-premium { background: #FAF5FF; color: var(--status-purple); border: 1px solid var(--status-purple-border); }
    </style>
</head>
<body>

    <div class="app-layout">
        <!-- ================= 银白冰蓝主工作台 ================= -->
        <main class="desk-main-content">
            <!-- 顶栏 Header -->
            <header class="desk-top-header">
                <div class="header-brand-box">
                    <div class="brand-monogram">IT</div>
                    <div class="brand-text">
                        <div class="brand-title">智能服务台</div>
                        <div class="brand-sub">SERVICE DESK</div>
                    </div>
                    <div class="breadcrumb-sep" style="margin: 0 12px; color: #D3E2ED;">|</div>
                    <div class="breadcrumb-box">
                        <span class="breadcrumb-item">员工服务</span>
                        <span class="breadcrumb-sep">/</span>
                        <span class="breadcrumb-current">智能客服 (Day29 成本治理与选模流水线)</span>
                    </div>
                </div>
                <div class="header-right-tools">
                    <div class="model-status-pill">
                        <span class="pulse-dot"></span>
                        <span>生产模型集群在线 (Qwen 3.7/3.8)</span>
                    </div>
                    <div class="notify-badge">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#476176" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                        <span class="notify-count">03</span>
                    </div>
                    <div class="theme-icon" title="明暗模式切换">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#476176" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                    </div>
                    <div class="user-profile-pill">
                        <div class="user-avatar">演</div>
                        <div class="user-name">演示员工</div>
                        <div class="user-role">架构组</div>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#7A93A6" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                </div>
            </header>

            <!-- 次级智能服务说明条 (同截图) -->
            <div class="desk-sub-banner">
                <div class="banner-left">
                    <span class="eyebrow-tag">INTELLIGENT SERVICE / 智能服务</span>
                    <span class="banner-title">工作遇到问题？我们来帮你。</span>
                </div>
                <div class="banner-right">
                    <span>描述你遇到的 IT 问题，获取处理建议，或直接联系工程师。</span>
                </div>
            </div>

            <!-- 主工作区：左右双栏 -->
            <div class="workspace-grid">

                <!-- 左栏：对话交互大屏 -->
                <div class="chat-column">
                    <!-- 预置场景快捷触发 -->
                    <div class="preset-section">
                        <div class="preset-title">
                            <span>⚡ 业务场景快捷触发 (点击即测)</span>
                            <span style="color: var(--future-accent); font-weight: normal;">未命中语义缓存后直穿 Model Router</span>
                        </div>
                        <div class="preset-list">
                            <button class="preset-btn" onclick="applyPreset(1)">
                                <span class="preset-tag tag-lite">LITE</span>
                                <span>公司访客 WiFi 密码</span>
                            </button>
                            <button class="preset-btn" onclick="applyPreset(2)">
                                <span class="preset-tag tag-std">STANDARD</span>
                                <span>内网 vs 异地 VPN 架构对比</span>
                            </button>
                            <button class="preset-btn" onclick="applyPreset(3)">
                                <span class="preset-tag tag-prem">PREMIUM</span>
                                <span>生产库 ALTER/DROP 特批工单</span>
                            </button>
                            <button class="preset-btn" onclick="applyPreset(4)">
                                <span class="preset-tag tag-degrade">降档演练</span>
                                <span>低额降档 (STANDARD → LITE)</span>
                            </button>
                            <button class="preset-btn" onclick="applyPreset(5)">
                                <span class="preset-tag tag-fuse">熔断演练</span>
                                <span>高危触底 429 熔断转人工</span>
                            </button>
                        </div>
                    </div>

                    <!-- 聊天会话列表 -->
                    <div class="chat-box" id="chatBox">
                        <!-- 初始欢迎卡片 -->
                        <div class="chat-msg msg-assistant">
                            <div class="assistant-card-inner">
                                <div class="msg-header">
                                    <div class="assistant-avatar-icon">🎧</div>
                                    <div>
                                        <div class="assistant-title-text">IT 智能助手</div>
                                        <div class="assistant-sub-text">办公遇到的问题，在这里解答</div>
                                    </div>
                                    <div class="msg-header-right">
                                        <span class="tag-pill badge-lite" style="font-size: 10px;">AI 实时协作</span>
                                    </div>
                                </div>
                                <div class="assistant-content-text">你好！我是 IT Service Desk 智能服务助理。
当前系统已装配**【Model Router 动态选模】**与**【Token 三级预算两阶段记账】**防御闸门。
请在上方选择预置测试用例或输入您的运维咨询；右侧大盘将全链路透明化展示每次请求的特征提取、规则打分、预扣降档、模型流式输出与费用结算。</div>
                            </div>
                        </div>
                    </div>

                    <!-- 输入控制栏 (同项目截图结构) -->
                    <div class="chat-input-bar">
                        <div class="chat-input-controls">
                            <div class="input-tags">
                                <span>👤 模拟用户:</span>
                                <select id="userSelect" class="input-select" onchange="refreshBudget()">
                                    <option value="U-TECH-01">U-TECH-01 (运维专员)</option>
                                    <option value="U-DEV-02">U-DEV-02 (研发工程师)</option>
                                </select>
                                <span>🏢 部门:</span>
                                <select id="deptSelect" class="input-select" onchange="refreshBudget()">
                                    <option value="DEPT-OPS">DEPT-OPS (运维保障部)</option>
                                    <option value="DEPT-RD">DEPT-RD (技术研发部)</option>
                                </select>
                            </div>
                            <div style="color: var(--text-dim); font-size: 10px;">
                                输入估算模式：中英混合动态分词
                            </div>
                        </div>

                        <textarea id="chatInput" class="chat-textarea" placeholder="描述你遇到的问题，回车发送" oninput="updateCharCount(this)" onkeydown="handleKeyDown(event)"></textarea>

                        <div class="chat-input-bottom">
                            <div class="bottom-actions-left">
                                <button class="btn-ghost-tool" onclick="alert('正在为您接入 IT 运维值班专家（转接人工中...）')">
                                    <span>🎧</span> <span>转人工</span>
                                </button>
                                <button class="btn-ghost-tool" onclick="alert('已打开工单提交流程，请填写具体问题现象与截图。')">
                                    <span>📋</span> <span>提交工单</span>
                                </button>
                                <span class="hint-text">Enter 发送 · Shift+Enter 换行 · AI 建议仅供参考</span>
                            </div>
                            <div class="bottom-actions-right">
                                <span class="word-counter" id="charCounter">0/8000</span>
                                <button class="btn-clear" onclick="clearChat()">✕ 清空对话</button>
                                <button id="sendBtn" class="btn-send" onclick="sendChat()">发送</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 右栏：全阶段透明化控制大盘 -->
                <div class="audit-column">

                    <!-- 卡片 0：实时预算控制台 -->
                    <div class="audit-card">
                        <div class="card-header">
                            <div class="card-title">
                                <span>💰 实时 Token 预算池大盘</span>
                            </div>
                            <span class="stage-badge" id="budgetScopeTag">U-TECH-01</span>
                        </div>
                        <div class="budget-grid">
                            <div class="budget-metric">
                                <div class="metric-label">
                                    <span>用户今日可用预算</span>
                                    <span id="userDailyPercent">100%</span>
                                </div>
                                <div class="metric-val" id="userDailyVal">30,000 / 30,000</div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" id="userDailyBar" style="width: 100%;"></div>
                                </div>
                            </div>
                            <div class="budget-metric">
                                <div class="metric-label">
                                    <span>部门当月可用预算</span>
                                    <span id="deptMonthlyPercent">100%</span>
                                </div>
                                <div class="metric-val" id="deptMonthlyVal">500,000 / 500,000</div>
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill" id="deptMonthlyBar" style="width: 100%;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="budget-actions">
                            <button class="btn-action" onclick="simulateBudget(1500)">⚡ 模拟日预算 1,500 (测降档)</button>
                            <button class="btn-action btn-danger" onclick="simulateBudget(0)">⛔ 模拟日预算耗尽 0 (测429熔断)</button>
                            <button class="btn-action" onclick="simulateBudget(30000)">🔄 重置满额</button>
                        </div>
                    </div>

                    <!-- 卡片 1：阶段 1 特征提取与规则打分 -->
                    <div class="audit-card" id="cardStage1">
                        <div class="card-header">
                            <div class="card-title">
                                <span>🔍 阶段一 · 特征提取与规则打分</span>
                            </div>
                            <span class="stage-badge">Feature Audit</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">输入长度估算:</span>
                                <span class="stage-val" id="s1Tokens">-- Token</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">高危权限/特批词 (+4):</span>
                                <span class="stage-val" id="s1RiskHits">无</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">多跳排查/对比词 (+2):</span>
                                <span class="stage-val" id="s1HopHits">无</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">综合复杂度总分:</span>
                                <span class="stage-val" id="s1Score" style="color: var(--future-accent); font-weight: bold;">--</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">评分明细依据:</span>
                                <span class="stage-val" id="s1Reasons" style="font-size: 11px; max-width: 65%; text-align: right; color: var(--text-secondary);">等待输入...</span>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片 2：阶段 2 Model Router 决策 -->
                    <div class="audit-card" id="cardStage2">
                        <div class="card-header">
                            <div class="card-title">
                                <span>🎯 阶段二 · Model Router 路由裁决</span>
                            </div>
                            <span class="stage-badge">Router Decision</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">路由裁决档位:</span>
                                <span class="stage-val" id="s2Tier"><span class="tag-pill badge-lite">LITE</span></span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">目标模型名称:</span>
                                <span class="stage-val" id="s2Model" style="color: var(--accent-blue);">qwen3.7-flash</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">模型单价 (入/出):</span>
                                <span class="stage-val" id="s2Pricing">¥0.0002 / ¥0.0006 per 1K</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">安全底线保护 (min_tier):</span>
                                <span class="stage-val" id="s2MinTier" style="color: var(--status-warning);">LITE (普通可降)</span>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片 RAG：企业知识库 RAG 检索与条目溯源流水 -->
                    <div class="audit-card" id="cardStageRag">
                        <div class="card-header">
                            <div class="card-title">
                                <span>🔍 知识检索 · RAG 多路召回与溯源</span>
                            </div>
                            <span class="stage-badge" id="sRagBadge">Vector & BM25</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">检索耗时 / 命中数:</span>
                                <span class="stage-val font-mono" id="sRagLatency">待检索</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">首位命中条目:</span>
                                <span class="stage-val" id="sRagTopTitle" style="max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;">-</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">最高相关度 (Top Score):</span>
                                <span class="stage-val" id="sRagScore">-</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">生效版本 / 可信度:</span>
                                <span class="stage-val font-mono" id="sRagVersion">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片 3：阶段 3 预算审查与两阶段预扣 -->
                    <div class="audit-card" id="cardStage3">
                        <div class="card-header">
                            <div class="card-title">
                                <span>⚖️ 阶段三 · Token 预算审查与两阶段预扣</span>
                            </div>
                            <span class="stage-badge">Budget Reserve</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">预扣 Token 估算:</span>
                                <span class="stage-val" id="s3Estimated">-- Token</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">预算放行状态:</span>
                                <span class="stage-val" id="s3Status" style="color: var(--status-success);">待命</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">是否触发降档:</span>
                                <span class="stage-val" id="s3Degraded" style="color: var(--text-secondary);">否 (原档放行)</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">最终执行模型:</span>
                                <span class="stage-val" id="s3ActualModel" style="color: var(--accent-blue);">--</span>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片 4：阶段 4 真实大模型调用 -->
                    <div class="audit-card" id="cardStage4">
                        <div class="card-header">
                            <div class="card-title">
                                <span>⚡ 阶段四 · 云端大模型真实流式推理</span>
                            </div>
                            <span class="stage-badge">Live Inference</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">网关 API 端点:</span>
                                <span class="stage-val" style="font-size: 11px;">https://kspmas.ksyun.com/v1</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">首字延迟 (TTFT):</span>
                                <span class="stage-val" id="s4TTFT" style="color: var(--future-accent);">-- ms</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">流式生成耗时:</span>
                                <span class="stage-val" id="s4Duration">-- s</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">输出吐字速度:</span>
                                <span class="stage-val" id="s4Speed">-- token/s</span>
                            </div>
                        </div>
                    </div>

                    <!-- 卡片 5：阶段 5 结算与审计出账 -->
                    <div class="audit-card" id="cardStage5">
                        <div class="card-header">
                            <div class="card-title">
                                <span>🧾 阶段五 · 费用真实结算与入账</span>
                            </div>
                            <span class="stage-badge">Settle & Ledger</span>
                        </div>
                        <div class="stage-table">
                            <div class="stage-row">
                                <span class="stage-label">实际使用 Prompt / Completion:</span>
                                <span class="stage-val" id="s5Usage">-- / -- Token</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">实扣总 Token (释放预扣):</span>
                                <span class="stage-val" id="s5TotalTokens" style="color: var(--accent-blue);">-- Token</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">折合调用费用 (¥ CNY):</span>
                                <span class="stage-val" id="s5Cost" style="color: var(--status-success); font-weight: bold;">¥ 0.000000</span>
                            </div>
                            <div class="stage-row">
                                <span class="stage-label">审计记账流水号:</span>
                                <span class="stage-val" id="s5ReqId" style="font-size: 10px; color: var(--text-dim);">--</span>
                            </div>
                        </div>
                    </div>

                </div>

            </div>
        </main>
    </div>

    <!-- 交互脚本 -->
    <script>
        const PRESETS = {
            1: {
                query: "公司访客 WiFi 密码是多少？外包人员如何申请网络准入连接？",
                desc: "LITE 标准 FAQ"
            },
            2: {
                query: "请详细对比公司内网专线直连与异地 SSL-VPN 接入方案的链路延迟、安全合规级别与客户端配置差异，并给出选择依据。",
                desc: "STANDARD 多跳对比"
            },
            3: {
                query: "工单号 IT-9821：申请对核心生产库 MySQL 生产环境 orders 表执行 DROP TABLE 与 ALTER 字段高危操作特批提权，请审查审批合规条件与防删库避险依据。",
                desc: "PREMIUM 高危特批"
            },
            4: {
                query: "请详细对比公司内网专线直连与异地 SSL-VPN 接入方案的链路延迟、安全合规级别与客户端配置差异，并给出选择依据。",
                desc: "低额降档演练 (STANDARD → LITE)"
            },
            5: {
                query: "工单号 IT-9823：申请对核心生产库 MySQL 生产环境 orders 表执行 DROP TABLE 高危特批提权与安全审计。",
                desc: "熔断演练 (429 安全拦截)"
            }
        };

        function updateCharCount(textarea) {
            const counter = document.getElementById('charCounter');
            if (counter) counter.innerText = `${textarea.value.length}/8000`;
        }

        function clearChat() {
            const box = document.getElementById('chatBox');
            box.innerHTML = `
                <div class="chat-msg msg-assistant">
                    <div class="assistant-card-inner">
                        <div class="msg-header">
                            <div class="assistant-avatar-icon">🎧</div>
                            <div>
                                <div class="assistant-title-text">IT 智能助手</div>
                                <div class="assistant-sub-text">办公遇到的问题，在这里解答</div>
                            </div>
                            <div class="msg-header-right">
                                <span class="tag-pill badge-lite" style="font-size: 10px;">AI 实时协作</span>
                            </div>
                        </div>
                        <div class="assistant-content-text">对话已清空。您可以随时提出新的 IT 运维问题或点击上方预置场景进行测试。</div>
                    </div>
                </div>
            `;
            resetStageCards();
        }

        function applyPreset(id) {
            const p = PRESETS[id];
            if (!p) return;
            // 高亮选中的按钮
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active-preset'));
            const clickedBtn = document.querySelector(`.preset-btn:nth-child(${id})`);
            if (clickedBtn) clickedBtn.classList.add('active-preset');

            const input = document.getElementById('chatInput');
            input.value = p.query;
            updateCharCount(input);

            if (id === 4) {
                simulateBudget(2500, () => {
                    sendChat();
                });
                return;
            }
            if (id === 5) {
                simulateBudget(0, () => {
                    sendChat();
                });
                return;
            }
            sendChat();
        }

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChat();
            }
        }

        function getUserDept() {
            return {
                userId: document.getElementById('userSelect').value,
                deptId: document.getElementById('deptSelect').value
            };
        }

        // 刷新预算大盘
        async function refreshBudget() {
            const { userId, deptId } = getUserDept();
            document.getElementById('budgetScopeTag').innerText = userId;
            try {
                const res = await fetch(`/api/budget/snapshot?user_id=${userId}&dept_id=${deptId}`);
                const data = await res.json();
                updateBudgetUI(data, userId, deptId);
            } catch (err) {
                console.error("Failed to load budget:", err);
            }
        }

        function updateBudgetUI(data, userId, deptId) {
            const dayKey = Object.keys(data).find(k => k.startsWith(`user:${userId}`));
            const deptKey = Object.keys(data).find(k => k.startsWith(`dept:${deptId}`));

            if (dayKey && data[dayKey]) {
                const u = data[dayKey];
                document.getElementById('userDailyVal').innerText = `${u.available.toLocaleString()} / ${u.limit.toLocaleString()}`;
                const pct = Math.round((u.available / u.limit) * 100);
                document.getElementById('userDailyPercent').innerText = `${pct}%`;
                const bar = document.getElementById('userDailyBar');
                bar.style.width = `${pct}%`;
                if (pct < 20) {
                    bar.classList.add('progress-warning');
                } else {
                    bar.classList.remove('progress-warning');
                }
            }

            if (deptKey && data[deptKey]) {
                const d = data[deptKey];
                document.getElementById('deptMonthlyVal').innerText = `${d.available.toLocaleString()} / ${d.limit.toLocaleString()}`;
                const pct = Math.round((d.available / d.limit) * 100);
                document.getElementById('deptMonthlyPercent').innerText = `${pct}%`;
                document.getElementById('deptMonthlyBar').style.width = `${pct}%`;
            }
        }

        async function simulateBudget(dailyAvailable, callback) {
            const { userId, deptId } = getUserDept();
            try {
                await fetch('/api/budget/simulate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, dept_id: deptId, daily_available: dailyAvailable })
                });
                await refreshBudget();
                if (callback) callback();
            } catch (err) {
                alert('模拟预算调节失败: ' + err);
            }
        }

        // 聊天主调用（SSE 接收）
        async function sendChat() {
            const input = document.getElementById('chatInput');
            const query = input.value.trim();
            if (!query) return;

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;
            input.value = '';
            updateCharCount(input);

            const { userId, deptId } = getUserDept();

            // 1. 添加用户气泡
            appendUserBubble(query);

            // 2. 创建助理气泡骨架
            const assistantBubble = appendAssistantBubbleSkeleton();

            // 3. 高亮卡片阶段初始化
            resetStageCards();

            const startTime = Date.now();

            try {
                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        user_id: userId,
                        dept_id: deptId,
                        history_turns: 0
                    })
                });

                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split(String.fromCharCode(10));
                    buffer = lines.pop(); // 保留不完整的一行

                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        if (line.startsWith('data:')) {
                            const dataStr = line.slice(5).trim();
                            if (!dataStr) continue;
                            try {
                                const evt = JSON.parse(dataStr);
                                handleServerEvent(evt, assistantBubble, startTime);
                            } catch (e) {
                                console.error("Parse event error:", e, dataStr);
                            }
                        }
                    }
                }
            } catch (err) {
                console.error("Stream error:", err);
                assistantBubble.contentSpan.innerHTML = `<span style="color: var(--status-danger);">❌ 通信异常: ${err.message}</span>`;
            } finally {
                sendBtn.disabled = false;
                await refreshBudget();
            }
        }

        function handleServerEvent(evt, bubbleObj, startTime) {
            // 阶段 1：模型自主意图特征分析
            if (evt.type === 'stage1') {
                highlightCard('cardStage1');
                document.getElementById('s1Tokens').innerText = `${evt.estimated_tokens} Token`;
                const riskColor = evt.risk_level === 'HIGH' ? 'var(--status-danger)' : (evt.risk_level === 'MEDIUM' ? 'var(--status-warning)' : 'var(--status-success)');
                document.getElementById('s1RiskHits').innerHTML = `<span class="tag-pill" style="background: rgba(0,0,0,0.04); color: ${riskColor}; border: 1px solid ${riskColor}; font-size: 10px;">模型判定风险: ${evt.risk_level}</span>`;
                document.getElementById('s1HopHits').innerHTML = '<span style="color: var(--future-accent); font-size: 11px;">由 qwen3.7-flash 自主评估</span>';
                document.getElementById('s1Score').innerText = `${evt.score} / 5`;
                document.getElementById('s1Reasons').innerText = evt.reasons.join('; ');
            }

            // 阶段 2：Router 决策
            else if (evt.type === 'stage2') {
                highlightCard('cardStage2');
                const tierClass = `badge-${evt.tier.toLowerCase()}`;
                document.getElementById('s2Tier').innerHTML = `<span class="tag-pill ${tierClass}">${evt.tier.toUpperCase()}</span>`;
                document.getElementById('s2Model').innerText = evt.model_name;
                document.getElementById('s2Pricing').innerText = `¥${evt.price_in} / ¥${evt.price_out} per 1K`;
                document.getElementById('s2MinTier').innerText = evt.min_tier.toUpperCase() + (evt.min_tier === 'standard' ? ' 🛡️(高危锁死)' : ' (可降)');
                bubbleObj.modelBadge.innerText = evt.model_name;
            }

            // 阶段 RAG：检索流水
            else if (evt.type === 'stage_rag') {
                highlightCard('cardStageRag');
                document.getElementById('sRagLatency').innerText = `${evt.latency_ms} ms / 命中 ${evt.count} 篇`;
                if (evt.citations && evt.citations.length > 0) {
                    const topDoc = evt.citations[0];
                    document.getElementById('sRagTopTitle').innerText = topDoc.title;
                    document.getElementById('sRagScore').innerHTML = `<span class="tag-pill badge-standard">${(evt.top_score * 100).toFixed(1)}%</span>`;
                    document.getElementById('sRagVersion').innerText = `${topDoc.version_id.substring(0, 16)}... (可信: ${evt.reliable ? '是' : '否'})`;
                } else {
                    document.getElementById('sRagTopTitle').innerText = '未命中企业知识库';
                    document.getElementById('sRagScore').innerText = '0.0%';
                    document.getElementById('sRagVersion').innerText = '无收录 (通用经验)';
                }
            }

            // 阶段 3：预扣与降档
            else if (evt.type === 'stage3') {
                highlightCard('cardStage3');
                document.getElementById('s3Estimated').innerText = `${evt.estimated} Token`;
                if (evt.degraded) {
                    document.getElementById('s3Status').innerHTML = '<span style="color: var(--status-warning);">⬇️ 触发降档</span>';
                    document.getElementById('s3Degraded').innerHTML = `<span style="color: var(--status-warning); font-weight: bold;">原 ${evt.routed_tier.toUpperCase()} 降至 ${evt.actual_tier.toUpperCase()}</span>`;
                    bubbleObj.modelBadge.innerText = evt.model_name;
                    bubbleObj.headerRight.innerHTML += ` <span class="tag-pill tag-degrade" style="font-size: 10px;">降档: ${evt.routed_tier.toUpperCase()} → ${evt.actual_tier.toUpperCase()}</span>`;
                } else {
                    document.getElementById('s3Status').innerHTML = '<span style="color: var(--status-success);">✅ 额度充足放行</span>';
                    document.getElementById('s3Degraded').innerText = '否 (原档放行)';
                }
                document.getElementById('s3ActualModel').innerText = evt.model_name;
            }

            // 429 熔断
            else if (evt.type === 'circuit_breaker') {
                highlightCard('cardStage3');
                document.getElementById('s3Status').innerHTML = '<span style="color: var(--status-danger);">⛔ 429 熔断拦截</span>';
                document.getElementById('s3Degraded').innerText = '已触底 min_tier 严禁小模型承接';
                bubbleObj.container.classList.add('msg-breaker');
                bubbleObj.modelBadge.innerText = '熔断拦截 (429)';
                bubbleObj.modelBadge.className = 'tag-pill tag-fuse';
                bubbleObj.contentSpan.innerHTML = `<strong>⛔ HTTP 429 预算安全熔断拦截：</strong><br>${evt.message}<br><br><span style="color: var(--text-dim); font-size: 11px;">建议动作：请向 IT 平台管理员申请增加日额度，或直接转人工运维工单处理。</span>`;
            }

            // 思考过程流
            else if (evt.type === 'thinking') {
                highlightCard('cardStage4');
                if (!bubbleObj.thinkingBox) {
                    bubbleObj.contentSpan.innerHTML = '';
                    bubbleObj.thinkingBox = document.createElement('div');
                    bubbleObj.thinkingBox.className = 'msg-thinking';
                    bubbleObj.thinkingBox.innerHTML = '<span style="font-weight: 600;">💭 深度思考推理中...</span><br>';
                    bubbleObj.innerCard.insertBefore(bubbleObj.thinkingBox, bubbleObj.contentSpan);
                }
                bubbleObj.thinkingBox.innerText += evt.delta;
                scrollToBottom();
            }

            // 阶段 4：Token 流式吐字
            else if (evt.type === 'token') {
                highlightCard('cardStage4');
                if (!bubbleObj.hasFirstToken) {
                    bubbleObj.hasFirstToken = true;
                    bubbleObj.contentSpan.innerHTML = '';
                    const ttft = Date.now() - startTime;
                    document.getElementById('s4TTFT').innerText = `${ttft} ms`;
                    if (bubbleObj.ttftSpan) bubbleObj.ttftSpan.innerText = `TTFT: ${ttft}ms`;
                }
                bubbleObj.contentSpan.innerText += evt.delta;
                scrollToBottom();

                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                document.getElementById('s4Duration').innerText = `${elapsed} s`;
            }

            // 阶段 5：结算审计
            else if (evt.type === 'stage5') {
                highlightCard('cardStage5');
                document.getElementById('s5Usage').innerText = `${evt.actual_in} / ${evt.actual_out} Token`;
                document.getElementById('s5TotalTokens').innerText = `${evt.actual_total} Token`;
                document.getElementById('s5Cost').innerText = `¥ ${evt.cost_cny.toFixed(6)}`;
                document.getElementById('s5ReqId').innerText = evt.request_id;

                const durationSec = ((Date.now() - startTime) / 1000).toFixed(2);
                let finishBadge = evt.finish_reason === 'length' ? ' <span class="tag-pill tag-fuse" style="font-size: 10px;">⚠️ 达长度上限截断</span>' : ' <span class="tag-pill" style="background: #F0FDF4; color: var(--status-success); border: 1px solid #BBF7D0; font-size: 10px;">✅ 完整输出</span>';
                
                bubbleObj.footerStats.innerHTML = `<span>⏱️ 耗时 ${durationSec}s</span> <span>📊 消耗 ${evt.actual_total} Token</span> <span>💰 费用 ¥${evt.cost_cny.toFixed(6)}</span>` + finishBadge;

                if (evt.budget_snapshot) {
                    const { userId, deptId } = getUserDept();
                    updateBudgetUI(evt.budget_snapshot, userId, deptId);
                }
            }

            // 知识库溯源卡片呈现
            else if (evt.type === 'citations') {
                if (evt.citations && evt.citations.length > 0) {
                    const citeBox = document.createElement('div');
                    citeBox.className = 'citations-card';
                    let itemsHtml = '';
                    evt.citations.forEach((c, idx) => {
                        const snippetShort = c.snippet ? c.snippet.replace(/#/g, '').trim().substring(0, 160) : '';
                        itemsHtml += `
                            <div class="citation-item">
                                <div class="citation-head">
                                    <span class="citation-idx">#${idx + 1}</span>
                                    <span class="citation-title font-medium">${escapeHtml(c.title)}</span>
                                    <span class="citation-score">匹配度: ${(c.score * 100).toFixed(1)}%</span>
                                    <span class="citation-ver">${escapeHtml(c.version_id)}</span>
                                </div>
                                <div class="citation-snippet">${escapeHtml(snippetShort)}...</div>
                            </div>
                        `;
                    });
                    citeBox.innerHTML = `
                        <div class="citations-header" onclick="this.nextElementSibling.classList.toggle('hidden'); this.querySelector('.cite-arrow').classList.toggle('rotate');">
                            <span class="citations-title">📚 企业知识库溯源依据 (${evt.citations.length} 篇参考资料)</span>
                            <span class="cite-arrow">▾</span>
                        </div>
                        <div class="citations-list">
                            ${itemsHtml}
                        </div>
                    `;
                    bubbleObj.innerCard.insertBefore(citeBox, bubbleObj.footerStats);
                    scrollToBottom();
                }
            }
        }

        function appendUserBubble(text) {
            const box = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'chat-msg msg-user';
            div.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
            box.appendChild(div);
            scrollToBottom();
        }

        function appendAssistantBubbleSkeleton() {
            const box = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'chat-msg msg-assistant';

            const innerCard = document.createElement('div');
            innerCard.className = 'assistant-card-inner';

            // 头部
            const header = document.createElement('div');
            header.className = 'msg-header';
            header.innerHTML = `
                <div class="assistant-avatar-icon">🎧</div>
                <div>
                    <div class="assistant-title-text">IT 智能助手</div>
                    <div class="assistant-sub-text">办公遇到的问题，在这里解答</div>
                </div>
                <div class="msg-header-right">
                    <span id="modelTag" class="tag-pill badge-lite" style="font-size: 10px;">调度模型中...</span>
                    <span id="ttftTag" style="color: var(--text-dim); font-size: 10px;"></span>
                </div>
            `;

            // 内容
            const contentSpan = document.createElement('div');
            contentSpan.className = 'assistant-content-text';
            contentSpan.innerHTML = '<span style="color: var(--future-accent);">⚡ Model Router 正在识别意图并配置预算通道...</span>';

            // 底部审计数据状态栏
            const footerStats = document.createElement('div');
            footerStats.className = 'msg-footer-stats';

            innerCard.appendChild(header);
            innerCard.appendChild(contentSpan);
            innerCard.appendChild(footerStats);
            div.appendChild(innerCard);
            box.appendChild(div);
            scrollToBottom();

            return {
                container: div,
                innerCard: innerCard,
                header: header,
                headerRight: header.querySelector('.msg-header-right'),
                contentSpan: contentSpan,
                footerStats: footerStats,
                modelBadge: header.querySelector('#modelTag'),
                ttftSpan: header.querySelector('#ttftTag'),
                hasFirstToken: false,
                thinkingBox: null
            };
        }

        function scrollToBottom() {
            const box = document.getElementById('chatBox');
            box.scrollTop = box.scrollHeight;
        }

        function highlightCard(cardId) {
            document.querySelectorAll('.audit-card').forEach(c => c.classList.remove('active-stage'));
            const card = document.getElementById(cardId);
            if (card) card.classList.add('active-stage');
        }

        function resetStageCards() {
            document.querySelectorAll('.audit-card').forEach(c => c.classList.remove('active-stage'));
            const sRagLat = document.getElementById('sRagLatency');
            if (sRagLat) sRagLat.innerText = '待检索';
            const sRagTop = document.getElementById('sRagTopTitle');
            if (sRagTop) sRagTop.innerText = '-';
            const sRagSc = document.getElementById('sRagScore');
            if (sRagSc) sRagSc.innerText = '-';
            const sRagVer = document.getElementById('sRagVersion');
            if (sRagVer) sRagVer.innerText = '-';
        }

        function escapeHtml(string) {
            return String(string).replace(/[&<>"']/g, function (s) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[s];
            });
        }

        // 初始化加载
        window.onload = function() {
            refreshBudget();
        };
    </script>
</body>
</html>
"""


# ==============================================================================
# 核心模块五：云端真实大模型推理与 SSE 流式网关 (CostGovernanceHTTPHandler)
#
# 【设计目标与生产规范】：
# 1. 协议标准：严格采用 W3C Server-Sent Events (SSE) 协议，Header 指定 `Content-Type: text/event-stream`；
# 2. 全阶段透明化流水线：
#    - Stage 1 (stage1): 路由器执行小模型语义判决，上报预估 Token 与风险等级；
#    - Stage 2 (stage2): 输出选定目标模型画像、基准单价与降级安全红线 (min_tier)；
#    - Stage 3 (stage3): 预算管理器执行两阶段预扣 (reserve)，若触发降档则输出降级事件；若额度耗尽且触底安全红线，
#                       立即抛出 circuit_breaker (HTTP 429 熔断拦截) 并安全阻断后续模型调用；
#    - Stage 4 (token / thinking): 真实连接云端推理网关，双通道流式分发思考链推理过程 (reasoning_content) 与
#                                正式回复文字增量 (delta)，精准捕获首字生成时间 (TTFT) 与吐字速率；
#    - Stage 5 (stage5): 会话结束时，按 API 真实 Usage 释放预扣并精确记账结算，实时刷新并回写前端多维预算池。
# 3. 动态加速策略：
#    - 对于 LITE (qwen3.7-flash) 标准常见 FAQ，通过 `extra_body={"enable_thinking": False}` 关闭耗时思考链，
#      实现 1~2 秒内极速直出首字，极大提升普通员工运维求助满意度；
#    - 对于 STANDARD / PREMIUM 深度架构与高危提权，开启全量深度推理，保障推理严谨性与审计合规。
# ==============================================================================

class CostGovernanceHTTPHandler(http.server.BaseHTTPRequestHandler):
    """工业级 HTTP 演示服务网关与 SSE 事件调度分发器"""

    def log_message(self, format, *args):
        # 简化日志，过滤高频 SSE 与心跳轮询日志，避免控制台刷屏
        if "POST /api/chat/stream" in args[0] or "GET /api/budget" in args[0]:
            return
        super().log_message(format, *args)

    def do_GET(self):
        """GET 请求路由分发：页面渲染与预算快照"""
        url = urllib.parse.urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/budget/snapshot":
            params = urllib.parse.parse_qs(url.query)
            user_id = params.get("user_id", ["U-TECH-01"])[0]
            dept_id = params.get("dept_id", ["DEPT-OPS"])[0]
            snap = budget_manager.snapshot(user_id, dept_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(snap).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """POST 请求路由分发：预算模拟与 SSE 问答流"""
        url = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_data = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_data)
        except Exception:
            body = {}

        if url.path == "/api/budget/simulate":
            user_id = body.get("user_id", "U-TECH-01")
            dept_id = body.get("dept_id", "DEPT-OPS")
            daily_available = int(body.get("daily_available", 20000))
            budget_manager.set_budget_simulation(user_id, dept_id, daily_available)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

        elif url.path == "/api/chat/stream":
            self.handle_chat_stream(body)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_chat_stream(self, body: dict):
        """核心处理链路：语义缓存未命中后的 Model Router 决策、预算两阶段预扣与云端真实模型 SSE 推理
        
        Args:
            body: 包含 query(用户提问), user_id(用户工号), dept_id(所属部门), history_turns(历史轮数)
        """
        query = body.get("query", "")
        user_id = body.get("user_id", "U-TECH-01")
        dept_id = body.get("dept_id", "DEPT-OPS")
        history_turns = int(body.get("history_turns", 0))
        request_id = f"fde-{uuid.uuid4().hex[:8]}"

        # 1. 建立 W3C 标准 SSE 单向流式长连接
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True

        def send_event(data: dict):
            """向前端实时写入单帧 SSE 数据块：data: {...}\\n\\n"""
            msg = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()

        # ----------------------------------------------------------------------
        # 【阶段 1】：小模型自主意图识别与风险初筛 (Stage 1)
        # ----------------------------------------------------------------------
        decision = router.route(query, history_turns)
        send_event({
            "type": "stage1",
            "estimated_tokens": estimate_tokens(query),
            "risk_hits": decision.risk_hits,
            "hop_hits": decision.hop_hits,
            "score": decision.score,
            "reasons": decision.reasons,
            "risk_level": getattr(decision, "risk_level", "LOW"),
        })
        time.sleep(0.08)

        # ----------------------------------------------------------------------
        # 【阶段 2】：Model Router 档位裁决与安全下限锁定 (Stage 2)
        # ----------------------------------------------------------------------
        profile = MODEL_CATALOG[decision.tier]
        send_event({
            "type": "stage2",
            "tier": decision.tier.value,
            "model_name": profile.model_name,
            "price_in": profile.price_per_1k_input,
            "price_out": profile.price_per_1k_output,
            "min_tier": decision.min_tier.value,
        })
        time.sleep(0.08)

        # ----------------------------------------------------------------------
        # 【阶段 2.5】：企业知识库 RAG 多路检索与条目溯源 (Stage RAG)
        # ----------------------------------------------------------------------
        rag_res = rag_client.retrieve(query, top_k=3)
        if rag_res.error:
            # 严格遵循 AGENTS.md：不为外部依赖故障添加静默回退，保留真实原因并向用户展示
            send_event({
                "type": "error",
                "message": f"知识库检索服务异常 (503): {rag_res.error}，请检查 rag_service (8310) 服务状态。"
            })
            return

        citations = []
        rag_context_parts = []
        for doc in rag_res.items:
            citations.append({
                "chunk_id": doc.chunk_id,
                "title": doc.title,
                "score": doc.score,
                "version_id": doc.version_id,
                "snippet": doc.snippet,
            })
            rag_context_parts.append(
                f"【条目: {doc.title} (编号: {doc.chunk_id}, 相似度: {doc.score:.3f}, 版本: {doc.version_id})】\n{doc.snippet}"
            )
        rag_context_text = "\n\n".join(rag_context_parts)
        rag_tokens = estimate_tokens(rag_context_text) if rag_context_text else 0

        # 推送 RAG 检索流水事件
        send_event({
            "type": "stage_rag",
            "latency_ms": rag_res.latency_ms,
            "reliable": rag_res.reliable,
            "top_score": rag_res.top_score,
            "count": len(rag_res.items),
            "citations": citations,
        })
        time.sleep(0.08)

        # ----------------------------------------------------------------------
        # 【阶段 3】：两阶段 Token 预算审查与级联降档 (Stage 3)
        # ----------------------------------------------------------------------
        try:
            plan = governor.plan(
                request_id,
                query,
                user_id,
                dept_id,
                history_turns,
                extra_prompt_tokens=rag_tokens,
            )
            send_event({
                "type": "stage3",
                "estimated": plan.estimated_tokens,
                "routed_tier": plan.routed_tier.value,
                "actual_tier": plan.model.tier.value,
                "model_name": plan.model.model_name,
                "degraded": plan.degraded,
            })
        except BudgetExceeded as exc:
            # 触底安全底线或总额度不足，触发 HTTP 429 熔断拦截
            send_event({
                "type": "circuit_breaker",
                "scope": exc.scope,
                "message": exc.detail,
                "is_circuit_breaker": exc.is_circuit_breaker,
            })
            return

        # ----------------------------------------------------------------------
        # 【阶段 4】：云端大模型真实流式推理与思考链分发 (Stage 4)
        # ----------------------------------------------------------------------
        system_instruction = (
            "你是一个企业级专业 IT Service Desk 智能服务工程师。\n"
            "你的核心职责是结合检索到的【企业 IT 知识库参考资料】对用户的提问进行权威、结构化的总结归纳与解答。\n\n"
            "【输出格式与归纳规范】：\n"
            "1. 严格优先依据知识库参考资料事实作答，分步骤给出清晰排查/解决指引（分节明确区分【员工自助排查步骤】与【IT 进阶运维支持】）；\n"
            "2. 若问题涉及核心生产库 ALTER/DROP 高危表结构变更或特批提权，必须严格提示审批制度、回避原则、双人复核与应急回滚方案；\n"
            "3. 仅当知识库参考资料确实为空或完全未提及相关问题时，才在正文开头注明：\n"
            "   「⚠️ 当前企业知识库未收录直接对应条目，以下解答基于 IT 运维通用经验归纳」；若参考资料中已命中相关指引，严禁输出该未收录声明。"
        )

        user_content = query
        if rag_context_text:
            user_content = (
                f"【用户提问】：{query}\n\n"
                f"【企业 IT 知识库参考资料】：\n{rag_context_text}\n\n"
                f"请严格结合上述参考资料进行深度归纳总结，输出清晰、专业、分步的解答。"
            )

        actual_in = estimate_tokens(user_content) + SYSTEM_PROMPT_RESERVE
        actual_out = 0
        full_text = ""

        try:
            if openai_client:
                call_kwargs = {
                    "model": plan.model.model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": plan.model.max_output_tokens,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }
                # LITE 常见 FAQ 关闭耗时思考链，实现 1~2 秒内极速直出首字
                if plan.model.tier == ModelTier.LITE:
                    call_kwargs["extra_body"] = {"enable_thinking": False}

                finish_reason = "stop"
                stream = openai_client.chat.completions.create(**call_kwargs)
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        # 思考推理流（Qwen 深度思考过程透传）
                        reasoning = getattr(delta, "reasoning_content", None)
                        if reasoning:
                            send_event({"type": "thinking", "delta": reasoning})
                        # 正式文本回复流
                        content = getattr(delta, "content", None)
                        if content:
                            full_text += content
                            send_event({"type": "token", "delta": content})
                    if chunk.choices and chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                    if chunk.usage:
                        actual_in = chunk.usage.prompt_tokens
                        actual_out = chunk.usage.completion_tokens
            else:
                raise RuntimeError("未配置有效的 LLM_API_KEY 与 LLM_BASE_URL")
        except Exception as e:
            print(f"❌ 云端大模型推理异常: {e}")
            governor.budget.release(request_id)  # 异常撤销，归还预扣额度
            send_event({"type": "error", "message": f"云端大模型推理异常: {str(e)}"})
            return

        if actual_out == 0:
            actual_out = estimate_tokens(full_text)

        # 推送知识库溯源引用卡片
        if citations:
            send_event({
                "type": "citations",
                "citations": citations,
            })

        # ----------------------------------------------------------------------
        # 【阶段 5】：释放预扣、真实 Usage 结算入账与多退少补 (Stage 5)
        # ----------------------------------------------------------------------
        actual_total = actual_in + actual_out
        governor.budget.settle(request_id, actual_total)
        cost_cny = estimate_cost(plan.model, actual_in, actual_out)
        snapshot = governor.budget.snapshot(user_id, dept_id)

        send_event({
            "type": "stage5",
            "request_id": request_id,
            "actual_in": actual_in,
            "actual_out": actual_out,
            "actual_total": actual_total,
            "cost_cny": cost_cny,
            "finish_reason": finish_reason,
            "budget_snapshot": snapshot,
        })
        send_event({"type": "done"})


def run_server(port=PORT, auto_open_browser=True):
    server = socketserver.ThreadingTCPServer(("0.0.0.0", port), CostGovernanceHTTPHandler)
    server.daemon_threads = True
    print("=" * 80)
    print(f"🚀 IT Service Desk 成本治理与 Model Router Web 控制台已启动！")
    print(f"🌐 本地访问地址: http://localhost:{port}")
    print(f"🤖 默认模型梯队: LITE(3.7-flash) | STANDARD(3.7-plus) | PREMIUM(3.8-max)")
    print(f"🔑 API 端点: {BASE_URL}")
    print("=" * 80)
    
    # 自动拉起浏览器
    if auto_open_browser:
        def open_browser():
            time.sleep(1.0)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务正常停止。")
        server.shutdown()


if __name__ == "__main__":
    run_server(PORT)
