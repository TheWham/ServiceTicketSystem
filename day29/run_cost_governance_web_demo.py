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

# 引入本地成本治理核心引擎
from cost_governance import (
    BudgetExceeded,
    CostGovernor,
    ModelRouter,
    ModelTier,
    MODEL_CATALOG,
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


# ==============================================================================
# HTML / CSS / JS 前端代码（严格符合 MASTER.md 设计系统）
# ==============================================================================

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IT Service Desk · 成本治理与 Model Router 动态选模全景控制台</title>
    <style>
        :root {
            --bg-page: #060D19;
            --bg-card: #0D1B2C;
            --bg-header: #091828;
            --bg-input: #0b1524;
            --border-color: #233C55;
            --border-focus: #245DCE;
            
            --text-primary: #E8F4FF;
            --text-secondary: #A1B6CF;
            --text-dim: #5c7591;
            
            --accent-cyan: #67E8F9;
            --accent-blue: #78ADFF;
            --accent-btn: #166BA5;
            --accent-btn-hover: #245DCE;
            
            --status-success: #78DCA0;
            --status-warning: #F2BF71;
            --status-danger: #FFA0A0;
            --status-purple: #C084FC;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 18px 24px;
            font-size: 13px;
            min-height: 100vh;
        }

        /* 顶部 Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 14px;
            margin-bottom: 18px;
        }
        .header-title-box { display: flex; align-items: center; gap: 12px; }
        .header-logo-icon {
            width: 38px; height: 38px;
            background: linear-gradient(135deg, #08758C, #245DCE);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px; font-weight: bold; color: #fff;
            border: 1px solid var(--accent-cyan);
            box-shadow: 0 0 12px rgba(103, 232, 249, 0.3);
        }
        .header-title { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 0.5px; }
        .header-subtitle { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
        .header-status-box { display: flex; align-items: center; gap: 10px; }
        .status-badge {
            background: rgba(103, 232, 249, 0.12);
            color: var(--accent-cyan);
            border: 1px solid rgba(103, 232, 249, 0.4);
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 12px;
            display: flex; align-items: center; gap: 6px;
        }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--status-success); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

        /* 双栏主布局 */
        .main-container {
            display: grid;
            grid-template-columns: 1.15fr 1fr;
            gap: 20px;
            height: calc(100vh - 90px);
        }

        /* 左栏：会话问答交互大屏 */
        .chat-column {
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }

        /* 思考过程折叠卡片 */
        .msg-thinking {
            background: rgba(8, 24, 40, 0.6);
            border-left: 2px solid var(--accent-cyan);
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 11px;
            color: var(--accent-cyan);
            margin-bottom: 8px;
            line-height: 1.4;
            max-height: 140px;
            overflow-y: auto;
            opacity: 0.85;
            white-space: pre-wrap;
        }

        /* 预置场景选中激活态 */
        .preset-btn.active-preset {
            border-color: var(--accent-cyan) !important;
            background: rgba(103, 232, 249, 0.25) !important;
            box-shadow: 0 0 10px rgba(103, 232, 249, 0.4);
        }
        .preset-section {
            margin-bottom: 12px;
            border-bottom: 1px solid rgba(35, 60, 85, 0.6);
            padding-bottom: 12px;
        }
        .preset-title {
            font-size: 11px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }
        .preset-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .preset-btn {
            background: rgba(22, 107, 165, 0.2);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            padding: 6px 10px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        .preset-btn:hover {
            border-color: var(--accent-cyan);
            background: rgba(103, 232, 249, 0.15);
            color: #fff;
            transform: translateY(-1px);
        }
        .preset-tag {
            font-size: 9px;
            padding: 1px 5px;
            border-radius: 4px;
            font-weight: 600;
        }
        .tag-lite { background: rgba(120, 220, 160, 0.2); color: var(--status-success); border: 1px solid var(--status-success); }
        .tag-std { background: rgba(120, 173, 255, 0.2); color: var(--accent-blue); border: 1px solid var(--accent-blue); }
        .tag-prem { background: rgba(192, 132, 252, 0.2); color: var(--status-purple); border: 1px solid var(--status-purple); }
        .tag-degrade { background: rgba(242, 191, 113, 0.2); color: var(--status-warning); border: 1px solid var(--status-warning); }
        .tag-fuse { background: rgba(255, 160, 160, 0.2); color: var(--status-danger); border: 1px solid var(--status-danger); }

        /* 聊天消息区域 */
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding-right: 6px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-bottom: 12px;
        }
        .chat-box::-webkit-scrollbar { width: 5px; }
        .chat-box::-webkit-scrollbar-track { background: transparent; }
        .chat-box::-webkit-scrollbar-thumb { background: #233C55; border-radius: 4px; }

        .chat-msg {
            display: flex;
            flex-direction: column;
            max-width: 90%;
            animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        .msg-user {
            align-self: flex-end;
        }
        .msg-user .msg-bubble {
            background: linear-gradient(135deg, #166BA5, #245DCE);
            color: #ffffff;
            border-radius: 12px 12px 2px 12px;
            padding: 10px 14px;
            box-shadow: 0 2px 8px rgba(36, 93, 206, 0.25);
        }
        .msg-assistant {
            align-self: flex-start;
        }
        .msg-assistant .msg-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 5px;
            font-size: 11px;
            color: var(--text-secondary);
        }
        .msg-assistant .msg-bubble {
            background: #112238;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 12px 12px 12px 2px;
            padding: 12px 16px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .msg-assistant .msg-footer {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 6px;
            font-size: 10px;
            color: var(--text-dim);
        }

        /* 熔断告警气泡 */
        .msg-breaker .msg-bubble {
            background: rgba(185, 28, 28, 0.15) !important;
            border: 1px solid var(--status-danger) !important;
            color: #FFA0A0 !important;
        }

        /* 输入区 */
        .chat-input-bar {
            display: flex;
            flex-direction: column;
            gap: 8px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 12px;
        }
        .chat-input-controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-secondary);
        }
        .input-tags { display: flex; gap: 8px; }
        .input-select {
            background: #0D1B2C;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            outline: none;
        }
        .chat-input-row {
            display: flex;
            gap: 8px;
        }
        .chat-textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-size: 13px;
            outline: none;
            resize: none;
            height: 48px;
            font-family: inherit;
        }
        .chat-textarea::placeholder { color: var(--text-dim); }
        .btn-send {
            background: linear-gradient(135deg, var(--accent-btn), var(--accent-btn-hover));
            border: 1px solid var(--accent-cyan);
            color: #ffffff;
            border-radius: 6px;
            padding: 0 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 0 10px rgba(103, 232, 249, 0.2);
            white-space: nowrap;
        }
        .btn-send:hover {
            box-shadow: 0 0 16px rgba(103, 232, 249, 0.5);
            transform: scale(1.02);
        }
        .btn-send:disabled {
            background: #233C55;
            border-color: #3b536b;
            color: #7b93ab;
            cursor: not-allowed;
            box-shadow: none;
            transform: none;
        }

        /* 右栏：全阶段透明化控制大盘 */
        .audit-column {
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .audit-column::-webkit-scrollbar { width: 5px; }
        .audit-column::-webkit-scrollbar-track { background: transparent; }
        .audit-column::-webkit-scrollbar-thumb { background: #233C55; border-radius: 4px; }

        .audit-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px 16px;
            position: relative;
            transition: all 0.2s;
        }
        .audit-card:hover {
            border-color: #385d82;
        }
        .audit-card.active-stage {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 12px rgba(103, 232, 249, 0.15);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .card-title {
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #ffffff;
        }
        .stage-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(103, 232, 249, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(103, 232, 249, 0.3);
            font-family: monospace;
        }

        /* 预算控制台 */
        .budget-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 10px;
        }
        .budget-metric {
            background: #091828;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 10px;
        }
        .metric-label { font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; display: flex; justify-content: space-between; }
        .metric-val { font-size: 14px; font-weight: bold; color: var(--accent-cyan); font-family: monospace; }
        .progress-bar-bg {
            height: 6px;
            background: #142538;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 6px;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #3b82f6);
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        .progress-warning { background: linear-gradient(90deg, #f59e0b, #ef4444) !important; }

        .budget-actions {
            display: flex;
            gap: 6px;
        }
        .btn-action {
            flex: 1;
            background: #112238;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 4px;
            padding: 5px 6px;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }
        .btn-action:hover {
            border-color: var(--accent-cyan);
            background: rgba(103, 232, 249, 0.12);
        }
        .btn-action.btn-danger:hover {
            border-color: var(--status-danger);
            background: rgba(255, 160, 160, 0.15);
            color: var(--status-danger);
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
            background: #091828;
            padding: 6px 10px;
            border-radius: 4px;
            border: 1px solid rgba(35, 60, 85, 0.5);
        }
        .stage-label { color: var(--text-secondary); }
        .stage-val { font-weight: 500; font-family: monospace; color: var(--text-primary); }

        .tag-pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-lite { background: rgba(120, 220, 160, 0.2); color: var(--status-success); border: 1px solid var(--status-success); }
        .badge-standard { background: rgba(120, 173, 255, 0.2); color: var(--accent-blue); border: 1px solid var(--accent-blue); }
        .badge-premium { background: rgba(192, 132, 252, 0.2); color: var(--status-purple); border: 1px solid var(--status-purple); }

        .keyword-chip {
            background: rgba(255, 160, 160, 0.2);
            color: var(--status-danger);
            border: 1px solid rgba(255, 160, 160, 0.4);
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 10px;
            margin-right: 4px;
        }
        .hop-chip {
            background: rgba(103, 232, 249, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(103, 232, 249, 0.4);
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 10px;
            margin-right: 4px;
        }
    </style>
</head>
<body>

    <!-- 顶部状态栏 -->
    <div class="header">
        <div class="header-title-box">
            <div class="header-logo-icon">FDE</div>
            <div>
                <div class="header-title">IT Service Desk · 成本治理与 Model Router 动态选模全景控制台</div>
                <div class="header-subtitle">Day 29 工业级三道防线生产演示 | 语义缓存未命中后全阶段透明化流水线</div>
            </div>
        </div>
        <div class="header-status-box">
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>生产模型集群在线 (Qwen 3.7/3.8)</span>
            </div>
        </div>
    </div>

    <!-- 主布局网格 -->
    <div class="main-container">

        <!-- 左侧：对话交互大屏 -->
        <div class="chat-column">
            
            <!-- 预置场景快捷触发 -->
            <div class="preset-section">
                <div class="preset-title">
                    <span>⚡ 业务场景快捷触发 (点击即测)</span>
                    <span style="color: var(--accent-cyan)">未命中直穿 Model Router</span>
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
                        <span>低额特批 (PREMIUM → STANDARD)</span>
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
                <div class="msg-assistant">
                    <div class="msg-header">
                        <span style="color: var(--accent-cyan); font-weight: 600;">🤖 IT 智能服务台</span>
                        <span>系统初始化就绪</span>
                    </div>
                    <div class="msg-bubble">你好！我是 IT Service Desk 智能服务助理。
当前系统已装配**【Model Router 动态选模】**与**【Token 三级预算两阶段记账】**防御闸门。
请在上方选择预置测试用例或输入您的运维咨询；右侧大盘将全链路透明化展示每次请求的特征提取、规则打分、预扣降档、模型流式输出与费用结算。</div>
                </div>
            </div>

            <!-- 输入控制栏 -->
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
                <div class="chat-input-row">
                    <textarea id="chatInput" class="chat-textarea" placeholder="输入 IT 运维咨询、架构对比问题，或申请高危权限特批工单..." onkeydown="handleKeyDown(event)"></textarea>
                    <button id="sendBtn" class="btn-send" onclick="sendChat()">发送提问</button>
                </div>
            </div>

        </div>

        <!-- 右侧：全阶段透明化控制大盘 -->
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
                        <div class="metric-val" id="userDailyVal">20,000 / 20,000</div>
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
                    <button class="btn-action" onclick="simulateBudget(20000)">🔄 重置满额</button>
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
                        <span class="stage-val" id="s1Score" style="color: var(--accent-cyan); font-weight: bold;">--</span>
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
                        <span class="stage-val" id="s2Model" style="color: var(--accent-cyan);">qwen3.7-flash</span>
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
                        <span class="stage-val" id="s3ActualModel" style="color: var(--accent-cyan);">--</span>
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
                        <span class="stage-val" id="s4TTFT" style="color: var(--accent-cyan);">-- ms</span>
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
                        <span class="stage-val" id="s5TotalTokens" style="color: var(--accent-cyan);">-- Token</span>
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
                query: "工单号 IT-9822：申请对核心生产库 MySQL 生产环境 user_info 表执行 ALTER 字段特批提权，请给出安全审查意见。",
                desc: "低额降档演练"
            },
            5: {
                query: "工单号 IT-9823：申请对核心生产库 MySQL 生产环境 数据库特批提权与安全审计。",
                desc: "熔断演练"
            }
        };

        function applyPreset(id) {
            const p = PRESETS[id];
            if (!p) return;
            // 高亮选中的按钮
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active-preset'));
            const clickedBtn = document.querySelector(`.preset-btn:nth-child(${id})`);
            if (clickedBtn) clickedBtn.classList.add('active-preset');

            document.getElementById('chatInput').value = p.query;

            if (id === 4) {
                simulateBudget(1500, () => {
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
        let activeEventSource = null;

        async function sendChat() {
            const input = document.getElementById('chatInput');
            const query = input.value.trim();
            if (!query) return;

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;
            input.value = '';

            const { userId, deptId } = getUserDept();

            // 1. 添加用户气泡
            appendUserBubble(query);

            // 2. 创建助理气泡骨架
            const assistantBubble = appendAssistantBubbleSkeleton();

            // 3. 高亮卡片阶段初始化
            resetStageCards();

            const startTime = Date.now();
            let ttftCaptured = false;

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
                assistantBubble.bubble.innerHTML = `<span style="color: var(--status-danger);">❌ 通信异常: ${err.message}</span>`;
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
                document.getElementById('s1RiskHits').innerHTML = `<span class="tag-pill" style="background: rgba(255,255,255,0.08); color: ${riskColor}; border: 1px solid ${riskColor}; font-size: 10px;">模型判定风险: ${evt.risk_level}</span>`;
                document.getElementById('s1HopHits').innerHTML = '<span style="color: var(--accent-cyan); font-size: 11px;">由 qwen3.7-flash 自主评估</span>';
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

            // 阶段 3：预扣与降档
            else if (evt.type === 'stage3') {
                highlightCard('cardStage3');
                document.getElementById('s3Estimated').innerText = `${evt.estimated} Token`;
                if (evt.degraded) {
                    document.getElementById('s3Status').innerHTML = '<span style="color: var(--status-warning);">⬇️ 触发降档</span>';
                    document.getElementById('s3Degraded').innerHTML = `<span style="color: var(--status-warning); font-weight: bold;">原 ${evt.routed_tier.toUpperCase()} 降至 ${evt.actual_tier.toUpperCase()}</span>`;
                    bubbleObj.header.innerHTML += ` <span class="tag-pill tag-degrade">降档: ${evt.routed_tier.toUpperCase()} → ${evt.actual_tier.toUpperCase()}</span>`;
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
                bubbleObj.bubble.innerHTML = `<strong>⛔ HTTP 429 预算安全熔断拦截：</strong><br>${evt.message}<br><br><span style="color: var(--text-dim); font-size: 11px;">建议动作：请向 IT 平台管理员申请增加日额度，或直接转人工运维工单处理。</span>`;
            }

            // 思考过程流
            else if (evt.type === 'thinking') {
                highlightCard('cardStage4');
                if (!bubbleObj.thinkingBox) {
                    bubbleObj.bubble.innerHTML = '';
                    bubbleObj.thinkingBox = document.createElement('div');
                    bubbleObj.thinkingBox.className = 'msg-thinking';
                    bubbleObj.thinkingBox.innerHTML = '<span style="font-weight: 600;">💭 深度思考推理中...</span><br>';
                    bubbleObj.bubble.appendChild(bubbleObj.thinkingBox);
                    bubbleObj.contentSpan = document.createElement('div');
                    bubbleObj.bubble.appendChild(bubbleObj.contentSpan);
                }
                bubbleObj.thinkingBox.innerText += evt.delta;
                scrollToBottom();
            }

            // 阶段 4：Token 流式吐字
            else if (evt.type === 'token') {
                highlightCard('cardStage4');
                if (!bubbleObj.hasFirstToken) {
                    bubbleObj.hasFirstToken = true;
                    if (!bubbleObj.contentSpan) {
                        bubbleObj.bubble.innerHTML = '';
                        bubbleObj.contentSpan = document.createElement('div');
                        bubbleObj.bubble.appendChild(bubbleObj.contentSpan);
                    }
                    const ttft = Date.now() - startTime;
                    document.getElementById('s4TTFT').innerText = `${ttft} ms`;
                    if (bubbleObj.ttftSpan) bubbleObj.ttftSpan.innerText = `TTFT: ${ttft}ms`;
                }
                if (bubbleObj.contentSpan) {
                    bubbleObj.contentSpan.innerText += evt.delta;
                } else {
                    bubbleObj.bubble.innerText += evt.delta;
                }
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
                let finishBadge = evt.finish_reason === 'length' ? ' <span class="tag-pill tag-fuse">⚠️ 达长度上限截断</span>' : ' <span class="tag-pill" style="background: rgba(120,220,160,0.15); color: var(--status-success);">✅ 完整输出</span>';
                bubbleObj.footer.innerHTML = `<span>⏱️ 耗时 ${durationSec}s</span> <span>📊 消耗 ${evt.actual_total} Token</span> <span>💰 费用 ¥${evt.cost_cny.toFixed(6)}</span>` + finishBadge;

                if (evt.budget_snapshot) {
                    const { userId, deptId } = getUserDept();
                    updateBudgetUI(evt.budget_snapshot, userId, deptId);
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

            const header = document.createElement('div');
            header.className = 'msg-header';
            header.innerHTML = `<span>🤖</span> <span id="modelTag" class="tag-pill badge-lite" style="font-size: 10px;">路由中...</span> <span id="ttftTag" style="color: var(--text-dim); font-size: 10px;"></span>`;

            const bubble = document.createElement('div');
            bubble.className = 'msg-bubble';
            bubble.innerHTML = '<span style="color: var(--accent-cyan)">⚡ Model Router 正在审计并调度模型...</span>';

            const footer = document.createElement('div');
            footer.className = 'msg-footer';

            div.appendChild(header);
            div.appendChild(bubble);
            div.appendChild(footer);
            box.appendChild(div);
            scrollToBottom();

            return {
                container: div,
                header: header,
                bubble: bubble,
                footer: footer,
                modelBadge: header.querySelector('#modelTag'),
                ttftSpan: header.querySelector('#ttftTag'),
                hasFirstToken: false
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
# 后端 HTTP 服务器与 SSE 事件流封装
# ==============================================================================

class CostGovernanceHTTPHandler(http.server.BaseHTTPRequestHandler):
    """处理前端页面、预算快照与 SSE 流式问答"""

    def log_message(self, format, *args):
        # 简化日志，避免控制台刷屏
        if "POST /api/chat/stream" in args[0] or "GET /api/budget" in args[0]:
            return
        super().log_message(format, *args)

    def do_GET(self):
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
        """处理未命中缓存后的 Model Router 决策与 SSE 真实模型推理流"""
        query = body.get("query", "")
        user_id = body.get("user_id", "U-TECH-01")
        dept_id = body.get("dept_id", "DEPT-OPS")
        history_turns = int(body.get("history_turns", 0))
        request_id = f"fde-{uuid.uuid4().hex[:8]}"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True

        def send_event(data: dict):
            msg = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()

        # 1. 阶段 1：模型自主意图与风险裁决
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

        # 2. 阶段 2：Router 决策
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

        # 3. 阶段 3：预算预扣与降档
        try:
            plan = governor.plan(request_id, query, user_id, dept_id, history_turns)
            send_event({
                "type": "stage3",
                "estimated": plan.estimated_tokens,
                "routed_tier": plan.routed_tier.value,
                "actual_tier": plan.model.tier.value,
                "model_name": plan.model.model_name,
                "degraded": plan.degraded,
            })
        except BudgetExceeded as exc:
            # 触发 429 熔断
            send_event({
                "type": "circuit_breaker",
                "scope": exc.scope,
                "message": exc.detail,
                "is_circuit_breaker": exc.is_circuit_breaker,
            })
            return

        # 4. 阶段 4：真实大模型调用（带智能 Mock 兜底，防止云端网络异常中断演示）
        actual_in = estimate_tokens(query) + 260
        actual_out = 0
        full_text = ""

        system_instruction = (
            "你是一个企业级专业 IT Service Desk 智能服务工程师。"
            "面对普通 FAQ 给出准确精炼的步骤；面对多跳架构给出专业对比；"
            "面对高危提权或 DROP/ALTER 特批申请，必须严格提示审批制度、回避原则与应急回滚方案。"
        )

        try:
            if openai_client:
                call_kwargs = {
                    "model": plan.model.model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": query},
                    ],
                    "max_tokens": plan.model.max_output_tokens,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }
                # LITE 常见 FAQ 关闭耗时思考链，实现 1~2 秒内极速直出
                if plan.model.tier == ModelTier.LITE:
                    call_kwargs["extra_body"] = {"enable_thinking": False}

                finish_reason = "stop"
                stream = openai_client.chat.completions.create(**call_kwargs)
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        # 思考推理流（Qwen 深度思考过程）
                        reasoning = getattr(delta, "reasoning_content", None)
                        if reasoning:
                            send_event({"type": "thinking", "delta": reasoning})
                        # 最终回复流
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
            governor.budget.release(request_id)
            send_event({"type": "error", "message": f"云端大模型推理异常: {str(e)}"})
            return

        if actual_out == 0:
            actual_out = estimate_tokens(full_text)

        # 5. 阶段 5：释放预扣与真实结算
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
