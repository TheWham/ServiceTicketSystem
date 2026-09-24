"""
终极高清矢量泳道图生成脚本 (4K UHD)
特点：
1. 100% 纯矢量绘制，包含 5 泳道、左侧 5 大角色标头、15 个节点、精准分支、完整连线逻辑与双飞轮闭环
2. 彻底解决位图模糊和分辨率低的问题：文字如刀刻般锐利，线条细腻平滑
3. 输出 4K 超高清 PNG (4320 x 2080) 与 矢量 SVG 文件
"""

import os
import subprocess
import shutil

SVG_CONTENT = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2160 1040" width="100%" height="100%" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;">
  <defs>
    <!-- 阴影滤镜 -->
    <filter id="shadow" x="-5%" y="-10%" width="110%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.05"/>
    </filter>
    <filter id="card-shadow" x="-8%" y="-12%" width="116%" height="135%">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.07"/>
    </filter>
    
    <!-- 箭头定义 -->
    <marker id="arrow-blue" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#0284c7" />
    </marker>
    <marker id="arrow-green" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#16a34a" />
    </marker>
    <marker id="arrow-orange" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#ea580c" />
    </marker>
    <marker id="arrow-purple" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#9333ea" />
    </marker>
    <marker id="arrow-red" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#ef4444" />
    </marker>
    <marker id="arrow-teal" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M1,1 L7,4 L1,7 Z" fill="#0d9488" />
    </marker>
  </defs>

  <!-- ================= 泳道背景与角色表头 ================= -->

  <!-- 泳道 1: 员工 -->
  <g id="lane-1">
    <rect x="200" y="20" width="1935" height="175" rx="8" fill="#f0f9ff" stroke="#bae6fd" stroke-width="1.5" />
    <rect x="25" y="20" width="175" height="175" rx="8" fill="#e0f2fe" stroke="#bae6fd" stroke-width="1.5" />
    <path d="M25,28 A8,8 0 0,1 33,20 L35,20 L35,195 L33,195 A8,8 0 0,1 25,187 Z" fill="#0284c7" />
    <line x1="200" y1="20" x2="200" y2="195" stroke="#bae6fd" stroke-width="1.5" />
    <text x="112" y="113" font-size="22" font-weight="700" fill="#0369a1" text-anchor="middle" letter-spacing="8">员工</text>
  </g>

  <!-- 泳道 2: 前端 -->
  <g id="lane-2">
    <rect x="200" y="205" width="1935" height="175" rx="8" fill="#f0fdf4" stroke="#bbf7d0" stroke-width="1.5" />
    <rect x="25" y="205" width="175" height="175" rx="8" fill="#dcfce7" stroke="#bbf7d0" stroke-width="1.5" />
    <path d="M25,213 A8,8 0 0,1 33,205 L35,205 L35,380 L33,380 A8,8 0 0,1 25,372 Z" fill="#16a34a" />
    <line x1="200" y1="205" x2="200" y2="380" stroke="#bbf7d0" stroke-width="1.5" />
    <text x="112" y="298" font-size="22" font-weight="700" fill="#15803d" text-anchor="middle" letter-spacing="8">前端</text>
  </g>

  <!-- 泳道 3: 后端 -->
  <g id="lane-3">
    <rect x="200" y="390" width="1935" height="175" rx="8" fill="#faf5ff" stroke="#e9d5ff" stroke-width="1.5" />
    <rect x="25" y="390" width="175" height="175" rx="8" fill="#f3e8ff" stroke="#e9d5ff" stroke-width="1.5" />
    <path d="M25,398 A8,8 0 0,1 33,390 L35,390 L35,565 L33,565 A8,8 0 0,1 25,557 Z" fill="#9333ea" />
    <line x1="200" y1="390" x2="200" y2="565" stroke="#e9d5ff" stroke-width="1.5" />
    <text x="112" y="483" font-size="22" font-weight="700" fill="#7e22ce" text-anchor="middle" letter-spacing="8">后端</text>
  </g>

  <!-- 泳道 4: 人工客服和工程师 -->
  <g id="lane-4">
    <rect x="200" y="575" width="1935" height="195" rx="8" fill="#fff7ed" stroke="#fed7aa" stroke-width="1.5" />
    <rect x="25" y="575" width="175" height="195" rx="8" fill="#ffedd5" stroke="#fed7aa" stroke-width="1.5" />
    <path d="M25,583 A8,8 0 0,1 33,575 L35,575 L35,770 L33,770 A8,8 0 0,1 25,762 Z" fill="#ea580c" />
    <line x1="200" y1="575" x2="200" y2="770" stroke="#fed7aa" stroke-width="1.5" />
    <text x="112" y="667" font-size="19" font-weight="700" fill="#c2410c" text-anchor="middle" letter-spacing="2">人工客服</text>
    <text x="112" y="697" font-size="19" font-weight="700" fill="#c2410c" text-anchor="middle" letter-spacing="2">和工程师</text>
  </g>

  <!-- 泳道 5: 存储引擎层 -->
  <g id="lane-5">
    <rect x="200" y="780" width="1935" height="235" rx="8" fill="#f0fdfb" stroke="#99f6e4" stroke-width="1.5" />
    <rect x="25" y="780" width="175" height="235" rx="8" fill="#ccfbf1" stroke="#99f6e4" stroke-width="1.5" />
    <path d="M25,788 A8,8 0 0,1 33,780 L35,780 L35,1015 L33,1015 A8,8 0 0,1 25,1007 Z" fill="#0d9488" />
    <line x1="200" y1="780" x2="200" y2="1015" stroke="#99f6e4" stroke-width="1.5" />
    <text x="112" y="903" font-size="20" font-weight="700" fill="#0f766e" text-anchor="middle" letter-spacing="3">存储引擎层</text>
  </g>


  <!-- ================= 连线层 ================= -->
  
  <!-- 1.1 发起故障咨询 -> 2.1 展示 AI 对话界面 -->
  <path d="M305,142 L305,250" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 2.1 展示 AI 对话界面 -> 3.1 AI+RAG知识检索 -->
  <path d="M305,326 L305,435" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 3.1 AI+RAG检索 <-> 5.1 RAG手册向量库 (双向交互) -->
  <path d="M305,511 L305,825" stroke="#0d9488" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-teal)" />
  
  <!-- 2.1 展示 AI 对话界面 -> 1.2 问题是否解决？ -->
  <path d="M380,250 L420,250 L420,105 L520,105" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 1.2 问题是否解决？ -> 已解决 -> 1.3 问题自愈结束 -->
  <path d="M605,75 L605,55 L660,55" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)" />
  <rect x="608" y="38" width="48" height="20" rx="4" fill="#dcfce7" stroke="#86efac" stroke-width="1" />
  <text x="632" y="52" font-size="12" font-weight="700" fill="#15803d" text-anchor="middle">已解决</text>
  
  <!-- 1.2 问题是否解决？ -> 未解决 -> 3.2 转人工3大条件 -->
  <path d="M565,145 L565,185 L440,185 L440,435" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  <rect x="445" y="174" width="112" height="22" rx="4" fill="#ffedd5" stroke="#fdba74" stroke-width="1" />
  <text x="501" y="189" font-size="11" font-weight="700" fill="#c2410c" text-anchor="middle">未解决/转人工/轮数&gt;5</text>
  
  <!-- 3.2 转人工3大条件 -> 1.4 确认转接人工 -->
  <path d="M575,445 L660,445 L660,142" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  
  <!-- 1.4 确认转接人工 -> 2.2 在线客服 IM 窗口 -->
  <path d="M750,142 L750,250" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  
  <!-- 2.2 在线客服 IM 窗口 -> 4.1 人工客服研判 -->
  <path d="M750,326 L750,635" stroke="#059669" stroke-width="2" fill="none" marker-end="url(#arrow-green)" />
  
  <!-- 4.1 人工客服研判 -> 4.2 是否需工程师处理？ -->
  <path d="M835,673 L875,673" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  
  <!-- 4.2 否(线上解决) -> 4.3 在线排除故障 -->
  <path d="M915,713 L915,730" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)" />
  <rect x="922" y="711" width="75" height="20" rx="3" fill="#dcfce7" stroke="#86efac" stroke-width="1" />
  <text x="959" y="725" font-size="11" font-weight="700" fill="#15803d" text-anchor="middle">否(线上解决)</text>
  
  <!-- 4.2 是(派单) -> 4.4 推送【报修卡片】 -->
  <path d="M915,633 L915,605" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  <rect x="923" y="610" width="48" height="20" rx="3" fill="#ffedd5" stroke="#fdba74" stroke-width="1" />
  <text x="947" y="624" font-size="11" font-weight="700" fill="#c2410c" text-anchor="middle">是(派单)</text>
  
  <!-- 4.4 推送卡片 -> 红色虚线 -> 2.3 展示工单填写页面 -->
  <path d="M915,555 L915,326" stroke="#ef4444" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-red)" />
  
  <!-- 2.3 展示工单填写页面 -> 1.5 填写工单信息 -->
  <path d="M975,250 L975,142" stroke="#0284c7" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 1.5 填写工单信息 -> 1.6 提交工单 -->
  <path d="M1065,102 L1115,102" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 1.6 提交工单 -> 2.4 发送提交请求 -->
  <path d="M1195,142 L1195,250" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 2.4 发送提交请求 -> 3.3 接收请求 -->
  <path d="M1195,326 L1195,435" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)" />
  
  <!-- 3.3 接收请求 -> 5.2 校验数据合法性 -->
  <path d="M1195,511 L1195,825" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)" />
  
  <!-- 5.2 校验数据合法性 -> 5.3 数据校验是否通过？ -->
  <path d="M1285,861 L1325,861" stroke="#0d9488" stroke-width="2" fill="none" marker-end="url(#arrow-teal)" />
  
  <!-- 5.3 校验通过(是) -> 5.4 存储工单数据 -->
  <path d="M1405,861 L1445,861" stroke="#16a34a" stroke-width="2" fill="none" marker-end="url(#arrow-green)" />
  <rect x="1410" y="844" width="28" height="20" rx="3" fill="#dcfce7" stroke="#86efac" stroke-width="1" />
  <text x="1424" y="858" font-size="12" font-weight="700" fill="#15803d" text-anchor="middle">是</text>
  
  <!-- 5.3 校验失败 -> 红色虚线回流到 2.3 展示工单填写页面 -->
  <path d="M1365,901 L1365,955 L1055,955 L1055,326" stroke="#ef4444" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-red)" />
  <rect x="1115" y="943" width="235" height="24" rx="4" fill="#fee2e2" stroke="#fca5a5" stroke-width="1" />
  <text x="1232" y="959" font-size="12" font-weight="700" fill="#b91c1c" text-anchor="middle">校验失败: 返回错误信息 (前端提示)</text>
  
  <!-- 5.4 存储工单数据 -> 3.4 创建工单 -->
  <path d="M1505,825 L1505,511" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  
  <!-- 3.4 创建工单 -> 向上返回工单号 -> 2.5 展示提交结果 -->
  <path d="M1445,435 L1445,326" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)" />
  <text x="1453" y="375" font-size="12" font-weight="600" fill="#7e22ce">返回工单号</text>
  
  <!-- 3.4 创建工单 -> 3.5 发送消息通知 -->
  <path d="M1525,471 L1575,471" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)" />
  
  <!-- 3.5 发送消息通知 -> 3.6 触发通知 -->
  <path d="M1710,471 L1750,471" stroke="#9333ea" stroke-width="2" fill="none" marker-end="url(#arrow-purple)" />
  
  <!-- 3.6 触发通知 -> 待办通知 (紫色虚线) -> 4.5 查看待办工单 -->
  <path d="M1825,511 L1825,550 L1615,550 L1615,635" stroke="#9333ea" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-purple)" />
  <rect x="1680" y="540" width="65" height="20" rx="3" fill="#f3e8ff" stroke="#d8b4fe" stroke-width="1" />
  <text x="1712" y="554" font-size="12" font-weight="600" fill="#7e22ce" text-anchor="middle">待办通知</text>
  
  <!-- 4.5 查看待办工单 -> 向上返回成功到 3.4 -->
  <path d="M1565,635 L1565,511" stroke="#0284c7" stroke-width="2" fill="none" marker-end="url(#arrow-blue)" />
  <text x="1572" y="590" font-size="12" font-weight="600" fill="#0369a1">返回成功</text>
  
  <!-- 4.5 查看待办工单 -> 4.6 处理工单 -->
  <path d="M1645,673 L1685,673" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  
  <!-- 4.6 处理工单 -> 4.7 提交处理结果 -->
  <path d="M1800,673 L1840,673" stroke="#ea580c" stroke-width="2" fill="none" marker-end="url(#arrow-orange)" />
  
  <!-- 4.7 提交处理结果 -> 向上蓝色虚线 -> 1.7 接收通知与验收 -->
  <path d="M1920,635 L1920,142" stroke="#0284c7" stroke-width="2" stroke-dasharray="6,4" fill="none" marker-end="url(#arrow-blue)" />
  <rect x="1926" y="345" width="65" height="22" rx="3" fill="#e0f2fe" stroke="#7dd3fc" stroke-width="1" />
  <text x="1958" y="360" font-size="12" font-weight="700" fill="#0369a1" text-anchor="middle">完工通知</text>
  
  <!-- 4.7 提交处理结果 -> 向下绿色实线 -> 5.5 知识沉淀与向量化 -->
  <path d="M1920,730 L1920,825" stroke="#059669" stroke-width="2.2" fill="none" marker-end="url(#arrow-green)" />
  <rect x="1926" y="765" width="75" height="22" rx="3" fill="#d1fae5" stroke="#6ee7b7" stroke-width="1" />
  <text x="1963" y="780" font-size="12" font-weight="700" fill="#047857" text-anchor="middle">抽取QA入库</text>
  
  <!-- 5.5 知识沉淀与向量化 -> 绿色长虚线反哺回流 -> 5.1 RAG手册向量库 -->
  <path d="M1840,861 L420,861" stroke="#0d9488" stroke-width="2.2" stroke-dasharray="8,5" fill="none" marker-end="url(#arrow-teal)" />
  
  <!-- 反哺回流胶囊提示卡 (置于中左侧，与右侧校验框完全避让) -->
  <g transform="translate(730, 861)">
    <rect x="-175" y="-14" width="350" height="28" rx="14" fill="#ffffff" stroke="#0d9488" stroke-width="1.8" filter="url(#shadow)" />
    <text x="0" y="4" font-size="13" font-weight="700" fill="#0f766e" text-anchor="middle">🔄 知识库更新入库 · 循环赋能下一次 AI 检索</text>
  </g>


  <!-- ================= 节点卡片层 ================= -->

  <!-- ====== 泳道 1: 员工 ====== -->
  <g transform="translate(225, 66)">
    <rect x="0" y="0" width="160" height="76" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2" filter="url(#card-shadow)" />
    <text x="80" y="34" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">1. 发起故障咨询</text>
    <text x="80" y="56" font-size="12" font-weight="500" fill="#64748b" text-anchor="middle">(描述现象/提问)</text>
  </g>

  <!-- 菱形：问题是否解决？ -->
  <g transform="translate(525, 72)">
    <polygon points="40,0 80,37 40,74 0,37" fill="#ffffff" stroke="#059669" stroke-width="2" filter="url(#shadow)" />
    <text x="40" y="33" font-size="13" font-weight="700" fill="#065f46" text-anchor="middle">问题是否</text>
    <text x="40" y="50" font-size="13" font-weight="700" fill="#065f46" text-anchor="middle">解决？</text>
  </g>

  <!-- 1.3 问题自愈·结束 -->
  <g transform="translate(660, 26)">
    <rect x="0" y="0" width="150" height="72" rx="8" fill="#ecfdf5" stroke="#10b981" stroke-width="2" filter="url(#card-shadow)" />
    <text x="75" y="32" font-size="14" font-weight="700" fill="#065f46" text-anchor="middle">✨ 问题自愈·结束</text>
    <text x="75" y="54" font-size="12" font-weight="600" fill="#047857" text-anchor="middle">[零工单闭环]</text>
  </g>

  <!-- 1.4 确认转接人工 -->
  <g transform="translate(660, 106)">
    <rect x="0" y="0" width="170" height="72" rx="8" fill="#ffffff" stroke="#ea580c" stroke-width="2" filter="url(#card-shadow)" />
    <text x="85" y="32" font-size="15" font-weight="700" fill="#7c2d12" text-anchor="middle">3. 确认转接人工</text>
    <text x="85" y="54" font-size="12" font-weight="500" fill="#9a3412" text-anchor="middle">(继承AI排查上下文)</text>
  </g>

  <!-- 1.5 填写工单信息 -->
  <g transform="translate(895, 66)">
    <rect x="0" y="0" width="170" height="76" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2" filter="url(#card-shadow)" />
    <text x="85" y="34" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">5. 填写工单信息</text>
    <text x="85" y="56" font-size="12" font-weight="500" fill="#64748b" text-anchor="middle">(核对预填/补充附件)</text>
  </g>

  <!-- 1.6 提交工单 -->
  <g transform="translate(1115, 66)">
    <rect x="0" y="0" width="150" height="76" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2" filter="url(#card-shadow)" />
    <text x="75" y="34" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">6. 提交工单</text>
    <text x="75" y="56" font-size="12" font-weight="500" fill="#64748b" text-anchor="middle">(点击提交)</text>
  </g>

  <!-- 1.7 接收通知与验收 -->
  <g transform="translate(1840, 66)">
    <rect x="0" y="0" width="160" height="76" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2" filter="url(#card-shadow)" />
    <text x="80" y="44" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">15. 接收通知与验收</text>
  </g>


  <!-- ====== 泳道 2: 前端 ====== -->
  <g transform="translate(225, 250)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#16a34a" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#14532d" text-anchor="middle">展示 AI 对话界面</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#166534" text-anchor="middle">(排查建议/操作按钮)</text>
  </g>

  <g transform="translate(665, 250)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#16a34a" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#14532d" text-anchor="middle">在线客服 IM 窗口</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#166534" text-anchor="middle">(建立实时文字沟通)</text>
  </g>

  <g transform="translate(895, 250)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#16a34a" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#14532d" text-anchor="middle">展示工单填写页面</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#166534" text-anchor="middle">(表单必填/字数校验)</text>
  </g>

  <g transform="translate(1115, 250)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#16a34a" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#14532d" text-anchor="middle">发送提交请求</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#166534" text-anchor="middle">(携带工单数据+防抖)</text>
  </g>

  <g transform="translate(1365, 250)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#16a34a" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#14532d" text-anchor="middle">展示提交结果</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#166534" text-anchor="middle">[工单号 / 状态展示]</text>
  </g>


  <!-- ====== 泳道 3: 后端 ====== -->
  <g transform="translate(225, 435)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#9333ea" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="14" font-weight="700" fill="#581c87" text-anchor="middle">2. AI+RAG 知识检索</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#6b21a8" text-anchor="middle">(匹配后生成方案)</text>
  </g>

  <!-- 转人工 3 大触发条件卡片 -->
  <g transform="translate(415, 415)">
    <rect x="0" y="0" width="160" height="114" rx="8" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.8" filter="url(#shadow)" />
    <text x="80" y="25" font-size="13" font-weight="700" fill="#b45309" text-anchor="middle">转人工 3 大触发条件</text>
    <line x1="12" y1="34" x2="148" y2="34" stroke="#fde68a" stroke-width="1" />
    <text x="16" y="55" font-size="11" font-weight="600" fill="#92400e">① 用户输入"转人工"</text>
    <text x="16" y="78" font-size="11" font-weight="600" fill="#92400e">② 会话轮数超过 5 轮</text>
    <text x="16" y="101" font-size="11" font-weight="600" fill="#92400e">③ 用户点击"未解决"</text>
  </g>

  <g transform="translate(1115, 435)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#9333ea" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#581c87" text-anchor="middle">7. 接收请求</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#6b21a8" text-anchor="middle">[参数校验/解析/防重]</text>
  </g>

  <g transform="translate(1365, 435)">
    <rect x="0" y="0" width="165" height="76" rx="8" fill="#ffffff" stroke="#9333ea" stroke-width="2" filter="url(#card-shadow)" />
    <text x="82" y="34" font-size="15" font-weight="700" fill="#581c87" text-anchor="middle">8. 创建工单</text>
    <text x="82" y="56" font-size="12" font-weight="500" fill="#6b21a8" text-anchor="middle">(生成TK号/状态:待处理)</text>
  </g>

  <g transform="translate(1575, 435)">
    <rect x="0" y="0" width="150" height="76" rx="8" fill="#ffffff" stroke="#9333ea" stroke-width="2" filter="url(#card-shadow)" />
    <text x="75" y="34" font-size="14" font-weight="700" fill="#581c87" text-anchor="middle">9. 发送消息通知</text>
    <text x="75" y="56" font-size="12" font-weight="500" fill="#6b21a8" text-anchor="middle">(通知相关责任人)</text>
  </g>

  <g transform="translate(1750, 435)">
    <rect x="0" y="0" width="150" height="76" rx="8" fill="#ffffff" stroke="#9333ea" stroke-width="2" filter="url(#card-shadow)" />
    <text x="75" y="34" font-size="14" font-weight="700" fill="#581c87" text-anchor="middle">10. 触发通知</text>
    <text x="75" y="56" font-size="12" font-weight="500" fill="#6b21a8" text-anchor="middle">[企微/短信/站内信]</text>
  </g>


  <!-- ====== 泳道 4: 人工客服和工程师 ====== -->
  <g transform="translate(665, 637)">
    <rect x="0" y="0" width="170" height="76" rx="8" fill="#ffffff" stroke="#ea580c" stroke-width="2" filter="url(#card-shadow)" />
    <text x="85" y="34" font-size="15" font-weight="700" fill="#7c2d12" text-anchor="middle">4. 人工客服研判</text>
    <text x="85" y="56" font-size="12" font-weight="500" fill="#9a3412" text-anchor="middle">(调阅摘要/文字沟通)</text>
  </g>

  <!-- 菱形：是否需工程师处理？ -->
  <g transform="translate(875, 633)">
    <polygon points="40,0 80,40 40,80 0,40" fill="#ffffff" stroke="#ea580c" stroke-width="2" filter="url(#shadow)" />
    <text x="40" y="36" font-size="12" font-weight="700" fill="#9a3412" text-anchor="middle">是否需工</text>
    <text x="40" y="53" font-size="12" font-weight="700" fill="#9a3412" text-anchor="middle">程师处理？</text>
  </g>

  <!-- 在线排除故障 (无需提单) -->
  <g transform="translate(845, 730)">
    <rect x="0" y="0" width="145" height="40" rx="6" fill="#ecfdf5" stroke="#10b981" stroke-width="1.8" filter="url(#shadow)" />
    <text x="72" y="20" font-size="12" font-weight="700" fill="#065f46" text-anchor="middle">在线排除故障</text>
    <text x="72" y="33" font-size="10" font-weight="600" fill="#047857" text-anchor="middle">(无需建单)</text>
  </g>

  <!-- 推送【报修卡片】 -->
  <g transform="translate(845, 567)">
    <rect x="0" y="0" width="145" height="40" rx="6" fill="#fff7ed" stroke="#f97316" stroke-width="1.8" filter="url(#shadow)" />
    <text x="72" y="20" font-size="12" font-weight="700" fill="#9a3412" text-anchor="middle">推送【报修卡片】</text>
    <text x="72" y="33" font-size="10" font-weight="500" fill="#c2410c" text-anchor="middle">(自动预填摘要)</text>
  </g>

  <!-- 11. 查看待办工单 -->
  <g transform="translate(1535, 637)">
    <rect x="0" y="0" width="155" height="76" rx="8" fill="#ffffff" stroke="#ea580c" stroke-width="2" filter="url(#card-shadow)" />
    <text x="77" y="34" font-size="14" font-weight="700" fill="#7c2d12" text-anchor="middle">11. 查看待办工单</text>
    <text x="77" y="56" font-size="12" font-weight="500" fill="#9a3412" text-anchor="middle">(接收通知/认领)</text>
  </g>

  <!-- 12. 处理工单 -->
  <g transform="translate(1710, 637)">
    <rect x="0" y="0" width="155" height="76" rx="8" fill="#ffffff" stroke="#ea580c" stroke-width="2" filter="url(#card-shadow)" />
    <text x="77" y="34" font-size="14" font-weight="700" fill="#7c2d12" text-anchor="middle">12. 处理工单</text>
    <text x="77" y="56" font-size="12" font-weight="500" fill="#9a3412" text-anchor="middle">(排查/填写结果/留痕)</text>
  </g>

  <!-- 13. 提交处理结果 -->
  <g transform="translate(1885, 635)">
    <rect x="0" y="0" width="175" height="80" rx="8" fill="#ecfdf5" stroke="#059669" stroke-width="2" filter="url(#card-shadow)" />
    <text x="87" y="28" font-size="14" font-weight="700" fill="#065f46" text-anchor="middle">13. 提交处理结果</text>
    <text x="87" y="49" font-size="11" font-weight="600" fill="#047857" text-anchor="middle">(更新状态: 待验收)</text>
    <text x="87" y="68" font-size="11" font-weight="700" fill="#059669" text-anchor="middle">☑ 勾选沉淀至知识库</text>
  </g>


  <!-- ====== 泳道 5: 存储引擎层 ====== -->
  <!-- 5.1 RAG 手册向量库 -->
  <g transform="translate(225, 825)">
    <rect x="0" y="0" width="160" height="76" rx="8" fill="#ffffff" stroke="#0d9488" stroke-width="2" filter="url(#card-shadow)" />
    <text x="80" y="34" font-size="14" font-weight="700" fill="#0f766e" text-anchor="middle">📚 RAG 手册向量库</text>
    <text x="80" y="56" font-size="12" font-weight="500" fill="#115e59" text-anchor="middle">[IT故障手册/SOP]</text>
  </g>

  <!-- 5.2 校验数据合法性 -->
  <g transform="translate(1115, 825)">
    <rect x="0" y="0" width="170" height="76" rx="8" fill="#ffffff" stroke="#0d9488" stroke-width="2" filter="url(#card-shadow)" />
    <text x="85" y="44" font-size="15" font-weight="700" fill="#0f766e" text-anchor="middle">校验数据合法性</text>
  </g>

  <!-- 5.3 菱形：数据校验是否通过？ -->
  <g transform="translate(1325, 825)">
    <polygon points="40,0 80,36 40,72 0,36" fill="#ffffff" stroke="#0d9488" stroke-width="2" filter="url(#shadow)" />
    <text x="40" y="32" font-size="12" font-weight="700" fill="#0f766e" text-anchor="middle">数据校验</text>
    <text x="40" y="49" font-size="12" font-weight="700" fill="#0f766e" text-anchor="middle">是否通过？</text>
  </g>

  <!-- 5.4 8. 存储工单数据 -->
  <g transform="translate(1445, 825)">
    <rect x="0" y="0" width="160" height="76" rx="8" fill="#ffffff" stroke="#0d9488" stroke-width="2" filter="url(#card-shadow)" />
    <text x="80" y="34" font-size="14" font-weight="700" fill="#0f766e" text-anchor="middle">8. 存储工单数据</text>
    <text x="80" y="56" font-size="12" font-weight="500" fill="#115e59" text-anchor="middle">(入库 / 初始状态)</text>
  </g>

  <!-- 5.5 14. 知识沉淀与向量化 -->
  <g transform="translate(1840, 825)">
    <rect x="0" y="0" width="170" height="76" rx="8" fill="#ffffff" stroke="#0d9488" stroke-width="2" filter="url(#card-shadow)" />
    <text x="85" y="34" font-size="13" font-weight="700" fill="#0f766e" text-anchor="middle">14. 知识沉淀与向量化</text>
    <text x="85" y="56" font-size="11" font-weight="500" fill="#115e59" text-anchor="middle">(抽取QA对写入RAG库)</text>
  </g>

</svg>
'''

def main():
    brain_dir = r'C:\Users\Admin\.gemini\antigravity\brain\c8132027-732e-4a37-818f-ad721a056a8c'
    docs_dir = r'd:\STS\ServiceTicketSystem\docs'
    
    # 1. 保存完善后的 SVG
    svg_brain = os.path.join(brain_dir, 'swimlane_vector_4k.svg')
    svg_docs = os.path.join(docs_dir, '业务流程泳道图-矢量高清.svg')
    
    with open(svg_brain, 'w', encoding='utf-8') as f:
        f.write(SVG_CONTENT)
    with open(svg_docs, 'w', encoding='utf-8') as f:
        f.write(SVG_CONTENT)
        
    print('SVG saved successfully.')

    # 2. 渲染 HTML 页面
    html_render = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      width: 2160px;
      height: 1040px;
      overflow: hidden;
    }}
  </style>
</head>
<body>
{SVG_CONTENT}
</body>
</html>'''
    
    render_html_path = os.path.join(brain_dir, 'render_4k.html')
    with open(render_html_path, 'w', encoding='utf-8') as f:
        f.write(html_render)

    # 3. 用 Edge 导出 4K 超高清 (4320 x 2080)
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_exe):
        edge_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        
    png_brain_path = os.path.join(brain_dir, 'swimlane_vector_4k.png')
    png_docs_4k = os.path.join(docs_dir, '业务流程泳道图-超清4K.png')
    
    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=2",
        "--window-size=2160,1040",
        f"--screenshot={png_brain_path}",
        f"file:///{render_html_path.replace(os.sep, '/')}"
    ]
    
    print('Rendering 4K PNG via Edge...')
    subprocess.run(cmd, check=True)
    shutil.copy(png_brain_path, png_docs_4k)
    print('4K PNG saved to:', png_docs_4k)

if __name__ == '__main__':
    main()
