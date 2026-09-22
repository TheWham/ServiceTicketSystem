# -*- coding: utf-8 -*-
"""tests/test_service.py —— 质量负责人测试集（《验收评测协议书》§3 + §2 指标）

样本集：TC-01~TC-07 典型案例 / TC-08~TC-09 边界案例 / TC-10 注入案例
指标集：M-01 字段校验精确度 / M-03 提取准确率 / M-05 生成成功率 / M-06 幂等防重
        M-07 降级可用率 / M-08 附件校验 / M-09 资产校验
规格集：SPEC §3 状态机 13 条合法边 + Guard 守卫 + T2/T3 超时降级

运行：python -m pytest -v    （大屏展示目标：100% Passed）
"""
import json
import re

import pytest
from conftest import EXE_BYTES, JPG_BYTES, PNG_BYTES

from ticket_p0.constants import (
    CODE_ASSET_NOT_FOUND, CODE_BIZ_ERROR, CODE_CONFLICT, CODE_FORBIDDEN,
    TICKET_ID_RE, TicketStatus,
)
from ticket_p0.errors import BizError, ValidationFailed

# =====================================================================
# 一、典型案例 TC-01 ~ TC-05（正向）
# =====================================================================

def test_tc01_硬件高优_全字段正向(service, make_dto):
    """TC-01：HARDWARE/HIGH + 资产 + 2附件 + 期望时间 → 生成 CREATED 工单"""
    u1 = service.upload_attachment("截图1.jpg", JPG_BYTES, "E1001")
    u2 = service.upload_attachment("截图2.png", PNG_BYTES, "E1001")
    dto = make_dto(
        title="办公电脑开机蓝屏报错0x0000007B反复重启", category="HARDWARE", priority="HIGH",
        description="今早9点开机出现蓝屏错误代码0x0000007B，反复重启无法进入系统。"
                    "已尝试安全模式卸载更新未解决，设备型号ThinkCentreM920t，影响财务报表提交。",
        assetId="IT-PC-20260901", attachmentUrls=[u1, u2],
        expectedFinishTime="2026-09-21 18:00:00")
    t = service.submit(dto, "E1001")

    # M-05 生成合法性：ticket_id 格式 / 状态 / 提单人
    assert TICKET_ID_RE.match(t["ticket_id"]) and t["ticket_id"].startswith("TK20260921")
    assert t["ticket_status"] == TicketStatus.CREATED
    assert t["creator_id"] == "E1001" and t["assignee_id"] is None

    # M-03 提取准确率：落库字段与提交字段逐字段一致
    row = service.get_ticket(t["ticket_id"])
    assert row["title"] == dto["title"]
    assert row["category"] == "HARDWARE"
    assert row["priority"] == "HIGH"
    assert row["description"] == dto["description"]          # 不被截断
    assert row["asset_id"] == "IT-PC-20260901"
    assert json.loads(row["attachment_urls"]) == [u1, u2]    # JSON List 序列化
    assert row["expected_finish_time"] == "2026-09-21 18:00:00"

    # M-09 CMDB 联动：回显型号与责任人
    assert t["asset_echo"] == {"brand_model": "ThinkCentre M920t", "owner_id": "E1001"}

    # 通知事件 SUBMIT_SUCCESS → 提单人（P0 仅落库 LOG）
    notes = service.list_notify(t["ticket_id"])
    assert [(n["event_type"], n["receiver_id"], n["channel_used"], n["delivery_status"])
            for n in notes] == [("SUBMIT_SUCCESS", "E1001", "LOG", "SUCCESS")]

    # 流转日志：from=NULL → CREATED
    logs = service.list_logs(t["ticket_id"])
    assert (logs[0]["action"], logs[0]["from_status"], logs[0]["to_status"]) == \
           ("SUBMIT", None, "CREATED")


def test_tc02_软件中优_无资产编号(service, make_dto):
    """TC-02：SOFTWARE/MEDIUM，assetId 空（软件类选填）→ 通过"""
    u = service.upload_attachment("崩溃日志.png", PNG_BYTES, "E1001")
    t = service.submit(make_dto(
        title="WPS表格打开后频繁崩溃闪退", category="SOFTWARE", priority="MEDIUM",
        description="使用WPS表格处理大型数据表时频繁崩溃闪退，文件约50MB含多张工作表，"
                    "已尝试重装WPS最新版仍复现。",
        assetId=None, attachmentUrls=[u]), "E1001")
    assert t["ticket_status"] == TicketStatus.CREATED and t["asset_id"] is None


def test_tc03_网络高优_无附件(service, make_dto):
    """TC-03：NETWORK/HIGH + 资产、无附件（选填）→ 通过"""
    t = service.submit(make_dto(
        title="办公网VPN无法认证连接", category="NETWORK", priority="HIGH",
        description="今晨连接办公VPN时提示认证失败，输入正确账号密码仍无法登录，"
                    "重启AnyConnect客户端无效，同部门多位同事均有此问题。",
        assetId="IT-NW-20260815", attachmentUrls=[]), "E1001")
    assert t["ticket_status"] == TicketStatus.CREATED
    assert json.loads(t["attachment_urls"]) == []


def test_tc04_账号中优_最简填写(service, make_dto):
    """TC-04：ACCOUNT/MEDIUM 最简四字段 → 通过"""
    t = service.submit(make_dto(
        title="企业邮箱登录提示密码错误", category="ACCOUNT", priority="MEDIUM",
        description="今早登录企业邮箱时提示密码错误，确认密码未修改且输入正确，"
                    "怀疑账号被锁定或密码策略变更。"), "E1001")
    assert t["ticket_status"] == TicketStatus.CREATED


def test_tc05_其他低优_带资产(service, make_dto):
    """TC-05：OTHER/LOW + 资产 + 1附件 → 通过"""
    u = service.upload_attachment("卡纸照片.jpg", JPG_BYTES, "E1001")
    t = service.submit(make_dto(
        title="三楼打印机频繁卡纸", category="OTHER", priority="LOW",
        description="三楼公共打印机近期频繁卡纸，已清理纸屑仍复现，影响部门打印报销单据。",
        assetId="IT-PR-20240820", attachmentUrls=[u]), "E1001")
    assert t["ticket_status"] == TicketStatus.CREATED


# =====================================================================
# 二、典型案例 TC-06 ~ TC-07（负向：必填与长度下限）
# =====================================================================

def test_tc06_标题为空_必填拦截(service, make_dto):
    """TC-06：title 空 → 40000 拦截，不生成工单"""
    with pytest.raises(ValidationFailed) as exc:
        service.submit(make_dto(title=""), "E1001")
    assert exc.value.code == CODE_BIZ_ERROR and "title" in exc.value.fields
    assert service.count_tickets() == 0


def test_tc07_描述过短_下限拦截(service, make_dto):
    """TC-07：description=3 字符 < 10 → 拦截并提示引导文案"""
    with pytest.raises(ValidationFailed) as exc:
        service.submit(make_dto(title="电脑蓝屏", description="蓝屏了"), "E1001")
    assert "description" in exc.value.fields
    assert "10" in exc.value.msg
    assert service.count_tickets() == 0


# =====================================================================
# 三、边界案例 TC-08 ~ TC-09（字符数经脚本精确核验）
# =====================================================================

TC08_TITLE = "办公电脑开机后蓝屏报错代码0x0000007B反复重启无法进入系统影响工作需今日内修复完毕恢复急急急"


def test_tc08_临界合法边界(service, make_dto):
    """TC-08：title=50（上限）、desc=10（下限）、资产字母段=2位（正则下界）→ 全部放行"""
    assert len(TC08_TITLE) == 50
    desc = "我的电脑蓝屏无法开机"
    assert len(desc) == 10
    t = service.submit(make_dto(
        title=TC08_TITLE, priority="LOW", description=desc, assetId="IT-AB-12345678"), "E1001")
    assert t["ticket_status"] == TicketStatus.CREATED


def test_tc09_临界非法边界(service, make_dto):
    """TC-09：title=51 / desc=501 / 资产字母段5位 / 期望时间过去 → 四字段独立报错"""
    desc_501 = ("我的电脑蓝屏无法开机，需要尽快处理。" * 40)[:500] + "啊"
    dto = make_dto(title=TC08_TITLE + "X", category="SOFTWARE", description=desc_501,
                   assetId="IT-ABCDE-12345678", expectedFinishTime="2020-01-01 00:00:00")
    assert len(dto["title"]) == 51 and len(dto["description"]) == 501
    with pytest.raises(ValidationFailed) as exc:
        service.submit(dto, "E1001")
    # 多字段同时越界：逐字段收集一次性返回，禁止遇第一个错就中断
    assert {"title", "description", "assetId", "expectedFinishTime"} <= exc.value.fields
    assert service.count_tickets() == 0


# =====================================================================
# 四、注入案例 TC-10（XSS + SQL + 路径穿越 + 伪造附件）
# =====================================================================

def test_tc10_多向量恶意注入(service, make_dto):
    """TC-10：不执行脚本、不删表、不越权读文件、不上传伪造附件"""
    # 1) XSS：title 含尖括号 → 校验拒绝
    with pytest.raises(ValidationFailed) as e1:
        service.submit(make_dto(title="<script>alert('xss')</script>蓝屏"), "E1001")
    assert "title" in e1.value.fields

    # 2) SQL 注入：description 不拦截，但参数化存储、表不被删、内容原样落库
    evil_sql = "'; DROP TABLE ticket; -- 我的电脑蓝屏无法开机需尽快处理"
    t = service.submit(make_dto(title="SQL注入测试标题", description=evil_sql), "E1001")
    assert service.get_ticket(t["ticket_id"])["description"] == evil_sql
    assert service.count_tickets() == 1            # ticket 表完好，DROP 未执行

    # 3) 路径穿越：asset_id 不符正则 → 40000，不得越权读文件
    with pytest.raises(ValidationFailed) as e3:
        service.submit(make_dto(title="路径穿越测试标题", assetId="../../etc/passwd"), "E1001")
    assert "assetId" in e3.value.fields

    # 4) 伪造附件：.exe 伪装 .jpg，魔数为 MZ → MIME 嗅探拒绝（不能只看扩展名）
    with pytest.raises(BizError) as e4:
        service.upload_attachment("恶意.jpg", EXE_BYTES, "E1001")
    assert e4.value.code == CODE_BIZ_ERROR and "格式" in e4.value.msg

    # 整体：仅 2 号 SQL 样本生成安全工单，其余均被拦截
    assert service.count_tickets() == 1


# =====================================================================
# 五、核心指标 M-01 / M-05 / M-06 / M-07 / M-08 / M-09
# =====================================================================

def test_m01_字段校验精确度(service, make_dto, clock):
    """10 条样本回放：真阳性(非法被拦)+真阴性(合法放行) 精确度 100%（阈值 ≥98%）"""
    samples = [  # (dto, 是否应通过, 预期错误字段子集)
        (make_dto(title="样本1硬件蓝屏", description="开机蓝屏无法进入系统需要处理"), True, set()),
        (make_dto(title="样本2软件崩溃", category="SOFTWARE",
                  description="软件频繁崩溃闪退无法正常使用"), True, set()),
        (make_dto(title="", description="开机蓝屏无法进入系统需要处理"), False, {"title"}),
        (make_dto(title="样本4描述过短", description="蓝屏了"), False, {"description"}),
        (make_dto(title="样本5分类非法", category="HR_OA",
                  description="开机蓝屏无法进入系统需要处理"), False, {"category"}),
        (make_dto(title="样本6优先级非法", priority="P0",
                  description="开机蓝屏无法进入系统需要处理"), False, {"priority"}),
        (make_dto(title="样本7资产格式错", assetId="IT-A-12345678",
                  description="开机蓝屏无法进入系统需要处理"), False, {"assetId"}),
        (make_dto(title="样本8时间过去", expectedFinishTime="2020-01-01 00:00:00",
                  description="开机蓝屏无法进入系统需要处理"), False, {"expectedFinishTime"}),
        (make_dto(title="<script>x</script>样本9", description="开机蓝屏无法进入系统需要处理"),
         False, {"title"}),
        (make_dto(title="样本10资产穿越", assetId="../../etc/passwd",
                  description="开机蓝屏无法进入系统需要处理"), False, {"assetId"}),
    ]
    correct = 0
    for dto, should_pass, expect_fields in samples:
        try:
            service.submit(dto, "E1001")
            passed, fields = True, set()
        except ValidationFailed as e:
            passed, fields = False, e.fields
        clock.advance(4)  # 避开 3s 防重窗干扰
        if passed == should_pass and (should_pass or expect_fields <= fields):
            correct += 1
    accuracy = correct / len(samples)
    print(f"\n[M-01] 字段校验精确度 = {accuracy:.0%}（阈值 ≥98%）")
    assert accuracy >= 0.98


def test_m05_工单生成成功率(service, make_dto, clock):
    """5 条校验通过样本 100% 落库（阈值 ≥99.5%）"""
    cases = [
        dict(title="M05样本A", category="HARDWARE", priority="HIGH"),
        dict(title="M05样本B", category="SOFTWARE", priority="MEDIUM"),
        dict(title="M05样本C", category="NETWORK", priority="LOW"),
        dict(title="M05样本D", category="ACCOUNT", priority="MEDIUM"),
        dict(title="M05样本E", category="OTHER", priority="HIGH"),
    ]
    desc = "开机蓝屏无法进入系统需要尽快处理"
    ok = 0
    for c in cases:
        t = service.submit(make_dto(description=desc, **c), "E1001")
        if t["ticket_status"] == TicketStatus.CREATED and TICKET_ID_RE.match(t["ticket_id"]):
            ok += 1
        clock.advance(4)
    rate = ok / len(cases)
    print(f"\n[M-05] 工单生成成功率 = {rate:.0%}（阈值 ≥99.5%）")
    assert rate >= 0.995 and service.count_tickets() == 5


def test_m06_幂等防重率(service, make_dto, clock):
    """3s 窗口内同用户+同标题连点仅落库 1 条；窗口外放行（阈值 100%）"""
    dto = make_dto()
    t1 = service.submit(dto, "E1001")
    with pytest.raises(BizError) as e1:
        service.submit(dto, "E1001")                    # 第 2 次点击：40900
    assert e1.value.code == CODE_CONFLICT
    clock.advance(2)
    with pytest.raises(BizError):                       # t0+2s 仍在窗口内
        service.submit(dto, "E1001")
    assert service.count_tickets() == 1                 # 仅落库 1 条
    clock.advance(2)                                    # t0+4s 超出 3s 窗口
    t2 = service.submit(dto, "E1001")
    assert t2["ticket_id"] != t1["ticket_id"] and service.count_tickets() == 2


def test_m07_推荐降级可用率(service, make_dto):
    """推荐接口异常 → 静默降级返回空，提单链路 100% 可用（阈值 100%）"""
    class BoomRecommender:
        def recommend(self, category, title=""):
            raise TimeoutError("recommend api timeout > 2s")

    service.recommender = BoomRecommender()
    assert service.recommend_safely("HARDWARE", "蓝屏") == []   # 不弹框、不阻塞
    t = service.submit(make_dto(), "E1001")                     # 提单正常
    assert t["ticket_status"] == TicketStatus.CREATED


def test_m08_附件校验准确率(service, make_dto):
    """四维校验：格式白名单 / 大小≤5MB / 数量≤3 / 魔数与扩展名一致（阈值 100%）"""
    # 超大小：>5MB
    with pytest.raises(BizError) as e1:
        service.upload_attachment("big.jpg", b"\xff\xd8\xff" + bytes(5 * 1024 * 1024), "E1001")
    assert "5MB" in e1.value.msg
    # 非白名单格式
    with pytest.raises(BizError):
        service.upload_attachment("文档.gif", b"GIF89a" + bytes(64), "E1001")
    # 魔数与扩展名不符（png 改名 .jpg）
    with pytest.raises(BizError):
        service.upload_attachment("伪装.jpg", PNG_BYTES, "E1001")
    # 合法上传 → 规范 URL
    u1 = service.upload_attachment("a.jpg", JPG_BYTES, "E1001")
    u2 = service.upload_attachment("b.png", PNG_BYTES, "E1001")
    u3 = service.upload_attachment("c.jpeg", JPG_BYTES, "E1001")
    assert re.match(r"^/files/[0-9a-f]{32}\.jpg$", u1)
    # 数量 >3 拦截
    u4 = service.upload_attachment("d.jpg", JPG_BYTES, "E1001")
    with pytest.raises(ValidationFailed) as e5:
        service.submit(make_dto(attachmentUrls=[u1, u2, u3, u4]), "E1001")
    assert "attachmentUrls" in e5.value.fields
    # 3 张放行
    t = service.submit(make_dto(attachmentUrls=[u1, u2, u3]), "E1001")
    assert json.loads(t["attachment_urls"]) == [u1, u2, u3]


def test_m09_资产编号校验准确率(service, make_dto, clock):
    """正则校验 + CMDB 联动：查无→40401、查中→回显型号责任人（阈值 100%）"""
    # 正则不过 → 40000（字段级）
    with pytest.raises(ValidationFailed) as e1:
        service.submit(make_dto(assetId="IT-PC-123"), "E1001")
    assert "assetId" in e1.value.fields
    # 正则过、CMDB 查无 → 40401
    with pytest.raises(BizError) as e2:
        service.submit(make_dto(title="CMDB查无此资产", assetId="IT-PC-00000000"), "E1001")
    assert e2.value.code == CODE_ASSET_NOT_FOUND
    assert "未在资产库中找到该编号" in e2.value.msg
    # 查中 → 回显型号与责任人
    t = service.submit(make_dto(title="CMDB命中资产", assetId="IT-PC-20260901"), "E1001")
    assert t["asset_echo"]["brand_model"] == "ThinkCentre M920t"


# =====================================================================
# 六、SPEC §3 状态机：合法边全链路 + Guard 守卫 + 超时降级
# =====================================================================

def _to_assigned(service, make_dto, title="状态机主链路工单"):
    t = service.submit(make_dto(title=title), "E1001")
    service.transit(t["ticket_id"], "ACCEPT", "E2001")
    return t["ticket_id"]


def test_state_machine_全链路合法流转(service, make_dto, clock):
    """主链路：CREATED→ASSIGNED→待补充→ASSIGNED→待外部→ASSIGNED→待验收→驳回→返工→验收→关闭
    （每次流转推进 61s：越过 60s 通知幂等窗，同名事件重复触发应各落一条记录）"""
    t = service.submit(make_dto(title="全链路流转工单"), "E1001")
    tid = t["ticket_id"]
    assert t["ticket_status"] == TicketStatus.CREATED

    clock.advance(61)
    r = service.transit(tid, "ACCEPT", "E2001")                       # 接单
    assert r["ticket_status"] == TicketStatus.ASSIGNED and r["assignee_id"] == "E2001"

    clock.advance(61)
    r = service.transit(tid, "REQUEST_SUPPLEMENT", "E2001", remark="请补充崩溃日志")
    assert r["ticket_status"] == TicketStatus.PENDING_SUPPLEMENT
    clock.advance(61)
    r = service.transit(tid, "SUPPLEMENT", "E1001", remark="已上传日志")
    assert r["ticket_status"] == TicketStatus.ASSIGNED

    clock.advance(61)
    r = service.transit(tid, "TRANSFER_EXTERNAL", "E2001", remark="需厂商备件")
    assert r["ticket_status"] == TicketStatus.PENDING_EXTERNAL
    clock.advance(61)
    r = service.transit(tid, "RESUME", "E2001")
    assert r["ticket_status"] == TicketStatus.ASSIGNED

    clock.advance(61)
    r = service.transit(tid, "RESOLVE", "E2001")                      # 提交方案
    assert r["ticket_status"] == TicketStatus.PENDING_ACCEPTANCE

    clock.advance(61)
    r = service.transit(tid, "ACCEPT_REJECT", "E1001", remark="问题复现未解决")  # 驳回
    assert r["ticket_status"] == TicketStatus.REJECTED and r["reject_count"] == 1
    clock.advance(61)
    r = service.transit(tid, "REWORK", "E2001")                       # 返工（复用 DISPATCH）
    assert r["ticket_status"] == TicketStatus.ASSIGNED

    clock.advance(61)
    service.transit(tid, "RESOLVE", "E2001")
    clock.advance(61)
    r = service.transit(tid, "ACCEPT_APPROVE", "E1001")               # 验收通过（终态）
    assert r["ticket_status"] == TicketStatus.ACCEPTED
    clock.advance(61)
    r = service.transit(tid, "CLOSE", "E1001")                        # 关闭（终态）
    assert r["ticket_status"] == TicketStatus.CLOSED

    # 流转日志完整：11 条动作 + 1 条 SUBMIT
    actions = [l["action"] for l in service.list_logs(tid)]
    assert actions == ["SUBMIT", "ACCEPT", "REQUEST_SUPPLEMENT", "SUPPLEMENT",
                       "TRANSFER_EXTERNAL", "RESUME", "RESOLVE", "ACCEPT_REJECT",
                       "REWORK", "RESOLVE", "ACCEPT_APPROVE", "CLOSE"]
    # 事件矩阵：DISPATCH/PENDING_SUPPLEMENT/PENDING_EXTERNAL/PENDING_ACCEPTANCE/
    # ACCEPT_REJECTED/DISPATCH(REWORK)/PENDING_ACCEPTANCE/ACCEPT_APPROVED
    events = [n["event_type"] for n in service.list_notify(tid)]
    assert events == ["SUBMIT_SUCCESS", "DISPATCH", "PENDING_SUPPLEMENT", "PENDING_EXTERNAL",
                      "PENDING_EXTERNAL", "PENDING_ACCEPTANCE", "ACCEPT_REJECTED",
                      "DISPATCH", "PENDING_ACCEPTANCE", "ACCEPT_APPROVED"]


def test_state_machine_非法流转40900(service, make_dto):
    """状态机中不存在的边 → 40900，工单状态不变"""
    t = service.submit(make_dto(title="非法流转测试"), "E1001")
    with pytest.raises(BizError) as e:
        service.transit(t["ticket_id"], "RESOLVE", "E2001")   # CREATED 不能直接提交方案
    assert e.value.code == CODE_CONFLICT and "非法状态流转" in e.value.msg
    assert service.get_ticket(t["ticket_id"])["ticket_status"] == TicketStatus.CREATED


def test_guard_角色守卫40300(service, make_dto):
    """员工不能接单（仅 ENGINEER）；SUPERVISOR 全局放行"""
    t = service.submit(make_dto(title="角色守卫测试A"), "E1001")
    with pytest.raises(BizError) as e:
        service.transit(t["ticket_id"], "ACCEPT", "E1001")
    assert e.value.code == CODE_FORBIDDEN
    t2 = service.submit(make_dto(title="角色守卫测试B"), "E1001")
    r = service.transit(t2["ticket_id"], "ACCEPT", "E9001")   # SUPERVISOR 放行
    assert r["ticket_status"] == TicketStatus.ASSIGNED


def test_guard_remark必填40000(service, make_dto):
    """REQUEST_SUPPLEMENT / TRANSFER_EXTERNAL / ACCEPT_REJECT 强制 remark"""
    tid = _to_assigned(service, make_dto, "remark守卫测试")
    with pytest.raises(BizError) as e:
        service.transit(tid, "REQUEST_SUPPLEMENT", "E2001")
    assert e.value.code == CODE_BIZ_ERROR and "说明" in e.value.msg


def test_guard_仅本人40300(service, make_dto):
    """补充/验收/关闭仅提单本人；SUPERVISOR 也不放行 creator_only"""
    tid = _to_assigned(service, make_dto, "本人守卫测试")
    service.transit(tid, "REQUEST_SUPPLEMENT", "E2001", remark="请补充")
    with pytest.raises(BizError) as e1:
        service.transit(tid, "SUPPLEMENT", "E2001")           # 非本人
    assert e1.value.code == CODE_FORBIDDEN
    with pytest.raises(BizError):
        service.transit(tid, "SUPPLEMENT", "E9001")           # 主管同样不放行
    service.transit(tid, "SUPPLEMENT", "E1001")
    service.transit(tid, "RESOLVE", "E2001")
    with pytest.raises(BizError):
        service.transit(tid, "ACCEPT_APPROVE", "E2001")       # 非本人验收
    assert service.get_ticket(tid)["ticket_status"] == TicketStatus.PENDING_ACCEPTANCE


def test_guard_乐观锁冲突40900(service, make_dto):
    """expected_version 过期 → 40900「工单已被他人操作」"""
    t = service.submit(make_dto(title="乐观锁测试"), "E1001")
    with pytest.raises(BizError) as e:
        service.transit(t["ticket_id"], "ACCEPT", "E2001", expected_version=t["version"] + 1)
    assert e.value.code == CODE_CONFLICT
    r = service.transit(t["ticket_id"], "ACCEPT", "E2001", expected_version=t["version"])
    assert r["version"] == t["version"] + 1


def test_terminal_终态不可逆与撤单(service, make_dto):
    """CLOSED 终态无合法边；CREATED 可由本人 CLOSE 撤单"""
    t = service.submit(make_dto(title="撤单测试"), "E1001")
    r = service.transit(t["ticket_id"], "CLOSE", "E1001")     # 撤单
    assert r["ticket_status"] == TicketStatus.CLOSED
    with pytest.raises(BizError) as e:
        service.transit(t["ticket_id"], "ACCEPT", "E2001")    # 终态不可逆
    assert e.value.code == CODE_CONFLICT


def test_timeout_T2_超时只告警不改状态(service, make_dto, clock):
    """T2：ASSIGNED 超 2h 未更新 → TIMEOUT_ALERT 落库给主管，状态不变；60s 幂等"""
    tid = _to_assigned(service, make_dto, "超时告警测试")
    clock.advance(3 * 3600)                                    # 3h 未更新
    r1 = service.scan_timeouts()
    assert r1["timeout_alert"] == 1
    note = service.list_notify(tid)[-1]
    assert note["event_type"] == "TIMEOUT_ALERT" and note["receiver_id"] == "E9001"
    assert service.get_ticket(tid)["ticket_status"] == TicketStatus.ASSIGNED  # 不自动销毁

    assert service.scan_timeouts()["timeout_alert"] == 0       # 60s 幂等键防轰炸
    clock.advance(61)
    assert service.scan_timeouts()["timeout_alert"] == 1       # 窗口外重新告警


def test_timeout_T3_待外部滞留催办(service, make_dto, clock):
    """T3：PENDING_EXTERNAL 超 24h → 重新生成事件（提单人+处理人），状态不变"""
    tid = _to_assigned(service, make_dto, "滞留催办测试")
    service.transit(tid, "TRANSFER_EXTERNAL", "E2001", remark="等厂商")
    clock.advance(25 * 3600)
    stats = service.scan_timeouts()
    assert stats["external_remind"] == 2                       # 提单人 + 处理人
    receivers = {n["receiver_id"] for n in service.list_notify(tid)
                 if n["event_type"] == "PENDING_EXTERNAL"}
    assert receivers == {"E1001", "E2001"}
    assert service.get_ticket(tid)["ticket_status"] == TicketStatus.PENDING_EXTERNAL


# =====================================================================
# 七、SPEC §2.2-3 草稿兜底
# =====================================================================

def test_draft_草稿保存与提交后清除(service, make_dto):
    """表单可随时存草稿（一人一份），提单成功后自动清除"""
    service.save_draft("E1001", {"title": "写了一半的草稿"})
    service.save_draft("E1001", {"title": "覆盖后的草稿"})     # 一人一份，覆盖
    assert service.get_draft("E1001")["title"] == "覆盖后的草稿"
    service.submit(make_dto(), "E1001")
    assert service.get_draft("E1001") is None                  # 提单成功自动清草稿


# =====================================================================
# 八、SPEC §1.6 发号合法性
# =====================================================================

def test_ticket_id_当日序号原子递增(service, make_dto, clock):
    """ticket_id = TK+yyyyMMdd+4位序号，当日递增不串号"""
    t1 = service.submit(make_dto(title="发号测试A"), "E1001")
    clock.advance(4)
    t2 = service.submit(make_dto(title="发号测试B"), "E1001")
    assert t1["ticket_id"] == "TK202609210001"
    assert t2["ticket_id"] == "TK202609210002"
