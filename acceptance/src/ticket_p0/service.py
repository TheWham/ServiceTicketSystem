# -*- coding: utf-8 -*-
"""工单核心服务（SPEC §1-§3）：
submit 提单（七字段校验 + CMDB + 3s 幂等 + 原子发号 + 通知落库 + 草稿清除）
transit 状态流转（状态机 + 角色/本人/remark/乐观锁守卫 + 流转日志 + 事件落库）
scan_timeouts 超时扫描（T2/T3 只告警不改状态）/ recommend_safely 推荐降级（M-07）
"""
import json
import uuid
from datetime import datetime, timedelta

from .attachment import validate_upload
from .constants import (
    CODE_ASSET_NOT_FOUND, CODE_BIZ_ERROR, CODE_CONFLICT, CODE_FORBIDDEN,
    CODE_NOT_FOUND, CODE_UNAUTHORIZED, DEFAULT_PRIORITY,
    EXTERNAL_REMIND_HOURS, NOTIFY_DEDUP_TTL_SECONDS, Role, SUBMIT_DEDUP_TTL_SECONDS,
    SUPERVISOR_ID, TIME_FMT, TIMEOUT_ALERT_HOURS, TicketStatus,
)
from .errors import BizError, FieldError, ValidationFailed
from .state_machine import ACTION_TARGET, resolve_edge
from .storage import SQLiteStore
from .validation import validate_submission

# 通知事件文案模板（SPEC §1.5，占位符 {ticketId}/{title}；P0 仅落库 LOG）
NOTIFY_TEMPLATES = {
    "SUBMIT_SUCCESS":      ("工单提交成功",   "您的工单 {ticketId}（{title}）已提交成功，工程师将尽快接单处理"),
    "DISPATCH":            ("新工单提醒",     "工单 {ticketId}（{title}）已派发至您，请及时处理"),
    "PENDING_SUPPLEMENT":  ("请补充工单信息", "工单 {ticketId}（{title}）需要您补充说明"),
    "PENDING_EXTERNAL":    ("工单转外部处理", "工单 {ticketId}（{title}）已转外部协同处理"),
    "PENDING_ACCEPTANCE":  ("请验收工单",     "工单 {ticketId}（{title}）已提交解决方案，请验收"),
    "ACCEPT_APPROVED":     ("验收通过",       "工单 {ticketId}（{title}）验收通过"),
    "ACCEPT_REJECTED":     ("验收被驳回",     "工单 {ticketId}（{title}）验收被驳回，请重新处理"),
    "TIMEOUT_ALERT":       ("工单超时预警",   "工单 {ticketId}（{title}）处理中超 2 小时未更新，请关注"),
}


def java_hashcode(s: str) -> int:
    """Java String.hashCode 语义（SPEC §1.6 防重键构成）"""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h - 0x100000000 if h >= 0x80000000 else h


class TicketService:
    def __init__(self, store: SQLiteStore, clock, recommender=None):
        self.store = store
        self.clock = clock
        self.recommender = recommender      # 知识库推荐钩子（可空；异常/超时不影响提单，M-07）
        self.users = {}                     # user_id -> role（SPEC §1.3 sys_user 简表）
        self.uploads = {}                   # file_name -> {size, ext, uploader}

    # ---------- 种子数据（评测环境 CMDB/用户） ----------
    def seed_user(self, user_id: str, role: str):
        self.users[user_id] = role

    def seed_asset(self, asset_id: str, name: str, brand_model: str, owner_id: str):
        self.store.execute(
            "INSERT OR REPLACE INTO asset(asset_id, asset_name, brand_model, owner_id, status, create_time)"
            " VALUES (?,?,?,?,?,?)",
            (asset_id, name, brand_model, owner_id, "IN_USE", self._fmt(self.clock.now())))

    # ---------- 附件上传（SPEC §1.7，魔数嗅探） ----------
    def upload_attachment(self, filename: str, content: bytes, uploader: str) -> str:
        ext = validate_upload(filename, content)  # 不通过抛 BizError(40000)
        fname = f"{uuid.uuid4().hex}.{ext}"
        self.uploads[fname] = {"size": len(content), "ext": ext, "uploader": uploader}
        return f"/files/{fname}"

    # ---------- 提单（SPEC §1.7 / §2.2 提单链路降级） ----------
    def submit(self, dto: dict, operator_id: str) -> dict:
        role = self._role_of(operator_id)
        if role not in (Role.EMPLOYEE, Role.SUPERVISOR):
            raise BizError(CODE_FORBIDDEN, "仅员工可提交工单")

        # 1. 归一化：title 去空白、priority 缺省 MEDIUM
        dto = dict(dto)
        dto["title"] = (dto.get("title") or "").strip()
        dto["priority"] = dto.get("priority") or DEFAULT_PRIORITY

        # 2. 字段级校验：任意不过 → 40000，不建单、不占防重锁（§2.2-1）
        errors = validate_submission(dto, self.clock.now())
        if errors:
            raise ValidationFailed(errors)

        # 3. CMDB 联动：正则已过，查无 → 40401（M-09）
        asset = None
        if dto.get("assetId"):
            asset = self.store.query_one("SELECT * FROM asset WHERE asset_id=?", (dto["assetId"],))
            if asset is None:
                raise BizError(CODE_ASSET_NOT_FOUND, "未在资产库中找到该编号")

        # 4. 附件必须为先前上传返回的 URL
        for url in dto.get("attachmentUrls") or []:
            if url.rsplit("/", 1)[-1] not in self.uploads:
                raise BizError(CODE_BIZ_ERROR, "附件不存在或已失效，请重新上传")

        # 5. 3s 幂等防重（T1）：宁可拒绝也不产生重复工单
        lock_key = f"submit:{operator_id}:{java_hashcode(dto['title'])}"
        if not self._acquire_lock(lock_key, SUBMIT_DEDUP_TTL_SECONDS):
            raise BizError(CODE_CONFLICT, "请勿重复提交")

        # 6. 原子发号 + 参数化落库（SQL 注入串仅作文本存储，TC-10）
        now_s = self._fmt(self.clock.now())
        ticket_id = self._next_ticket_id()
        urls_json = json.dumps(dto.get("attachmentUrls") or [], ensure_ascii=False)
        self.store.execute(
            "INSERT INTO ticket(ticket_id,title,category,asset_id,description,attachment_urls,"
            "priority,expected_finish_time,ticket_status,creator_id,assignee_id,reject_count,"
            "version,create_time,update_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, dto["title"], dto["category"], dto.get("assetId"), dto["description"],
             urls_json, dto["priority"], dto.get("expectedFinishTime"), TicketStatus.CREATED,
             operator_id, None, 0, 0, now_s, now_s))
        self._log(ticket_id, operator_id, "SUBMIT", None, TicketStatus.CREATED, None, None)

        # 7. 草稿清除（§2.2-3）+ 通知落库（§2.4，失败仅记日志不影响主链路）
        self.store.execute("DELETE FROM ticket_draft WHERE creator_id=?", (operator_id,))
        ticket = self.get_ticket(ticket_id)
        self._notify_safe(ticket, "SUBMIT_SUCCESS", [operator_id])

        # 8. 资产回显（M-09 CMDB 联动：型号与责任人）
        if asset:
            ticket["asset_echo"] = {"brand_model": asset["brand_model"], "owner_id": asset["owner_id"]}
        return ticket

    # ---------- 状态流转（SPEC §3，全部收口于此） ----------
    def transit(self, ticket_id: str, action: str, operator_id: str,
                remark: str = None, expected_version: int = None,
                attachment_urls: list = None) -> dict:
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise BizError(CODE_NOT_FOUND, "工单号不存在")
        role = self._role_of(operator_id)

        # 1. 合法边校验
        edge = resolve_edge(ticket["ticket_status"], action)
        if edge is None:
            target = ACTION_TARGET.get(action, action)
            raise BizError(CODE_CONFLICT, f"非法状态流转:{ticket['ticket_status']} -> {target}")

        # 2. Guard：角色（SUPERVISOR 放行）/ 本人（SUPERVISOR 不放行）/ remark / 乐观锁
        if edge.roles and role not in edge.roles and role != Role.SUPERVISOR:
            raise BizError(CODE_FORBIDDEN, "无权限访问")
        if edge.creator_only and operator_id != ticket["creator_id"]:
            raise BizError(CODE_FORBIDDEN, "无权限访问")
        if edge.remark_required and not (remark or "").strip():
            raise BizError(CODE_BIZ_ERROR, "请填写说明")
        if expected_version is not None and expected_version != ticket["version"]:
            raise BizError(CODE_CONFLICT, "工单已被他人操作,请刷新后重试")

        # 3. 乐观锁更新（UPDATE ... WHERE version=?，影响行数=0 → 40900）
        now_s = self._fmt(self.clock.now())
        assignee = operator_id if edge.set_assignee else ticket["assignee_id"]
        reject_count = ticket["reject_count"] + (1 if edge.reject_incr else 0)
        cur = self.store.execute(
            "UPDATE ticket SET ticket_status=?, assignee_id=?, reject_count=?, version=version+1,"
            " update_time=? WHERE ticket_id=? AND version=?",
            (edge.to_status, assignee, reject_count, now_s, ticket_id, ticket["version"]))
        if cur.rowcount == 0:
            raise BizError(CODE_CONFLICT, "工单已被他人操作,请刷新后重试")

        # 4. 流转日志 + 事件落库（afterCommit 语义：通知异常绝不影响流转结果）
        self._log(ticket_id, operator_id, action, ticket["ticket_status"], edge.to_status,
                  remark, attachment_urls)
        updated = self.get_ticket(ticket_id)
        if edge.event:
            self._notify_safe(updated, edge.event, self._receivers(edge.receivers, updated))
        return updated

    # ---------- 超时扫描（SPEC §2.1 T2/T3 + §2.5：只告警，绝不改状态） ----------
    def scan_timeouts(self) -> dict:
        now = self.clock.now()
        stats = {"timeout_alert": 0, "external_remind": 0}

        t2_deadline = self._fmt(now - timedelta(hours=TIMEOUT_ALERT_HOURS))
        for t in self.store.query_all(
                "SELECT * FROM ticket WHERE ticket_status=? AND update_time<?",
                (TicketStatus.ASSIGNED, t2_deadline)):
            stats["timeout_alert"] += self._notify_safe(t, "TIMEOUT_ALERT", [SUPERVISOR_ID])

        t3_deadline = self._fmt(now - timedelta(hours=EXTERNAL_REMIND_HOURS))
        for t in self.store.query_all(
                "SELECT * FROM ticket WHERE ticket_status=? AND update_time<?",
                (TicketStatus.PENDING_EXTERNAL, t3_deadline)):
            stats["external_remind"] += self._notify_safe(
                t, "PENDING_EXTERNAL", self._receivers("CREATOR_ASSIGNEE", t))
        return stats

    # ---------- 知识库推荐降级（协议书 M-07：接口异常/超时，提单仍 100% 可用） ----------
    def recommend_safely(self, category: str, title: str = "") -> list:
        if self.recommender is None:
            return []
        try:
            return self.recommender.recommend(category, title) or []
        except Exception:
            return []  # 静默降级：不弹框、不阻塞、不影响提单

    # ---------- 草稿（SPEC §1.6 ticket_draft：一人一份，提交成功自动清除） ----------
    def save_draft(self, user_id: str, content: dict):
        self.store.execute(
            "INSERT INTO ticket_draft(creator_id, draft_content, update_time) VALUES (?,?,?)"
            " ON CONFLICT(creator_id) DO UPDATE SET draft_content=excluded.draft_content,"
            " update_time=excluded.update_time",
            (user_id, json.dumps(content, ensure_ascii=False), self._fmt(self.clock.now())))

    def get_draft(self, user_id: str):
        row = self.store.query_one(
            "SELECT draft_content FROM ticket_draft WHERE creator_id=?", (user_id,))
        return json.loads(row["draft_content"]) if row else None

    # ---------- 只读查询 ----------
    def get_ticket(self, ticket_id: str):
        return self.store.query_one("SELECT * FROM ticket WHERE ticket_id=?", (ticket_id,))

    def list_logs(self, ticket_id: str):
        return self.store.query_all(
            "SELECT * FROM ticket_log WHERE ticket_id=? ORDER BY id", (ticket_id,))

    def list_notify(self, ticket_id: str = None):
        if ticket_id:
            return self.store.query_all(
                "SELECT * FROM notify_record WHERE ticket_id=? ORDER BY id", (ticket_id,))
        return self.store.query_all("SELECT * FROM notify_record ORDER BY id")

    def count_tickets(self) -> int:
        return self.store.query_one("SELECT COUNT(*) AS c FROM ticket")["c"]

    # ================= 内部实现 =================
    def _role_of(self, user_id: str) -> str:
        role = self.users.get(user_id)
        if role is None:
            raise BizError(CODE_UNAUTHORIZED, "未登录或登录已过期")
        return role

    def _fmt(self, dt: datetime) -> str:
        return dt.strftime(TIME_FMT)

    def _next_ticket_id(self) -> str:
        """TK + yyyyMMdd + 当日4位序号；seq 表 ON CONFLICT 原子自增（SPEC §1.6）"""
        day = self.clock.now().strftime("%Y%m%d")
        self.store.execute(
            "INSERT INTO ticket_id_seq(seq_date, seq) VALUES (?, 1)"
            " ON CONFLICT(seq_date) DO UPDATE SET seq=seq+1", (day,))
        seq = self.store.query_one("SELECT seq FROM ticket_id_seq WHERE seq_date=?", (day,))["seq"]
        return f"TK{day}{seq:04d}"

    def _acquire_lock(self, lock_key: str, ttl_seconds: int) -> bool:
        """dedup_lock 获取语义：INSERT IGNORE 占位；已存在仅允许过期后抢占续期（SPEC §1.6）"""
        now_s = self._fmt(self.clock.now())
        expires = self._fmt(self.clock.now() + timedelta(seconds=ttl_seconds))
        try:
            self.store.execute(
                "INSERT INTO dedup_lock(lock_key, expires_at, create_time) VALUES (?,?,?)",
                (lock_key, expires, now_s))
            return True
        except Exception:
            row = self.store.query_one(
                "SELECT expires_at FROM dedup_lock WHERE lock_key=?", (lock_key,))
            if row is None or row["expires_at"] > now_s:
                return False
            self.store.execute(
                "UPDATE dedup_lock SET expires_at=?, create_time=? WHERE lock_key=?",
                (expires, now_s, lock_key))
            return True

    def _log(self, ticket_id, operator_id, action, from_status, to_status, remark, urls):
        self.store.execute(
            "INSERT INTO ticket_log(ticket_id,operator_id,operator_name,action,from_status,"
            "to_status,remark,attachment_urls,create_time) VALUES (?,?,?,?,?,?,?,?,?)",
            (ticket_id, operator_id, operator_id, action, from_status, to_status, remark,
             json.dumps(urls, ensure_ascii=False) if urls else None, self._fmt(self.clock.now())))

    def _receivers(self, kind: str, ticket: dict) -> list:
        creator, assignee = ticket["creator_id"], ticket["assignee_id"]
        if kind == "CREATOR":
            return [creator]
        if kind == "ASSIGNEE":
            return [assignee] if assignee else []
        if kind == "CREATOR_ASSIGNEE":
            seen = [creator] + ([assignee] if assignee and assignee != creator else [])
            return seen
        if kind == "SUPERVISOR":
            return [SUPERVISOR_ID]
        return []

    def _notify_safe(self, ticket: dict, event_type: str, receivers: list) -> int:
        """SPEC §2.4：60s 幂等抢锁 → 落 notify_record；任何异常仅记日志，返回成功落库条数"""
        inserted = 0
        title_t, content_t = NOTIFY_TEMPLATES[event_type]
        content = content_t.format(ticketId=ticket["ticket_id"], title=ticket["title"])
        for rid in receivers:
            try:
                key = f"notify:{ticket['ticket_id']}:{event_type}:{rid}"
                if not self._acquire_lock(key, NOTIFY_DEDUP_TTL_SECONDS):
                    continue  # 60s 幂等：跳过该接收人本次记录
                self.store.execute(
                    "INSERT INTO notify_record(ticket_id,event_type,receiver_id,channel_used,"
                    "is_fallback,delivery_status,title,content,dedup_key,create_time)"
                    " VALUES (?,?,?,?,0,?,?,?,?,?)",
                    (ticket["ticket_id"], event_type, rid, "LOG", "SUCCESS",
                     title_t, content, key, self._fmt(self.clock.now())))
                inserted += 1
            except Exception:
                pass  # 降级要点：事件全丢也不阻塞工单闭环
        return inserted
