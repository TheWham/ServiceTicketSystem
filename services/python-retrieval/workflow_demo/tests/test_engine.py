# -*- coding: utf-8 -*-
"""工作流端到端单测：六个用例的裁决、短路分支、门禁零副作用、模型双模。"""

import json

import pytest

from workflow_demo.cases import DEMO_CASES
from workflow_demo.data_source import SqliteDataSource
from workflow_demo.engine import DeterministicWorkflow
from workflow_demo.model_client import ModelClient, ModelReply, ModelUnavailable, estimate_tokens
from workflow_demo.tracer import TOKENS_ESTIMATED, TOKENS_REPORTED


class FakeModel(ModelClient):
    """离线假模型：返回固定 JSON，但带真实的 usage 形状。"""

    def __init__(self, intent_label="KNOWLEDGE_QA", synthesis=None, raw_synthesis=None,
                 prompt_tokens=120, completion_tokens=30, finish_reason="stop", fail=False):
        super().__init__(base_url="http://fake", api_key="k")
        self.intent_label = intent_label
        self.synthesis = synthesis
        self.raw_synthesis = raw_synthesis  # 直接给原始文本，用于模拟截断/空输出
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.finish_reason = finish_reason  # "length" 用于模拟撞上 max_tokens 被截断
        self.fail = fail
        self.calls = 0

    def complete(self, messages, max_tokens=None, temperature=None, trace_id=None):
        self.calls += 1
        if self.fail:
            raise ModelUnavailable("模拟模型故障")
        prompt = "".join(m.get("content") or "" for m in messages)
        if "意图分类器" in prompt:
            content = self.intent_label
        elif self.raw_synthesis is not None:
            content = self.raw_synthesis
        else:
            content = json.dumps(self.synthesis or {"answerText": "模型写的答复", "usedVersionIds": []},
                                 ensure_ascii=False)
        return ModelReply(content, self.prompt_tokens, self.completion_tokens, TOKENS_REPORTED,
                          self.finish_reason)


@pytest.fixture()
def ds(tmp_path):
    return SqliteDataSource(db_path=str(tmp_path / "demo.db"))


def _wf(ds, model=None):
    return DeterministicWorkflow(ds=ds, model=model if model is not None else _NoModel())


class _NoModel(ModelClient):
    """显式未配置模型：走确定性兜底。"""

    def __init__(self):
        super().__init__(base_url="", api_key="")


# ---------------------------------------------------------------- 用例矩阵

@pytest.mark.parametrize("case", DEMO_CASES, ids=[c.case_id for c in DEMO_CASES])
def test_用例裁决与预期一致(ds, case):
    result = _wf(ds).run_case(case.case_id)
    assert result["matched"], f"{case.case_id}: 预期 {case.expect}，实际 {result['verdict']}"


def test_短路分支不进入并行扇出(ds):
    """越界拒答必须在 Node 1 就地返回，省掉检索与建单开销。"""
    result = _wf(ds).run_case("off-topic")
    kinds = [s["kind"] for s in result["trace"]["spans"]]
    assert result["refusalReason"] == "OFF_TOPIC"
    assert "PARALLEL_TASK" not in kinds
    assert result["trace"]["spanCount"] == 2


def test_敏感操作短路且不给模型翻案(ds):
    """模型硬说这是知识问答，也必须被规则拦下。"""
    model = FakeModel(intent_label="KNOWLEDGE_QA")
    result = _wf(ds, model).run_case("sensitive")
    assert result["verdict"] == "REFUSED"
    assert result["refusalReason"] == "HIGH_RISK_TOPIC"
    assert "PARALLEL_TASK" not in [s["kind"] for s in result["trace"]["spans"]]


# ---------------------------------------------------------------- 门禁与副作用

def test_建单放行只产草稿不落库(ds):
    result = _wf(ds).run_case("create-ok")
    assert result["verdict"] == "DRAFT_READY"
    assert result["ticketDraft"]["status"] == "PENDING_EMPLOYEE_CONFIRM"

    # 草稿只在内存；重建数据源看不到它 —— 工单表也没多出一条
    assert len(ds.drafts()) == 1
    assert len(SqliteDataSource(db_path=ds.db_path).list_my_tickets("U_EMP01")) == 3


def test_重复单被拦且零副作用(ds):
    result = _wf(ds).run_case("create-duplicate")
    assert result["verdict"] == "BLOCKED"
    assert result["refusalReason"] == "POLICY_BLOCKED"
    assert result["ticketDraft"] is None
    assert ds.drafts() == [], "被拦的请求不得留下任何草稿"


def test_信息不足回问而非拒答(ds):
    """字段不全不是违规：正解是把问题问清楚，replyType 应为 CLARIFY。"""
    result = _wf(ds).run_case("needs-info")
    assert result["verdict"] == "NEEDS_INFO"
    assert result["replyType"] == "CLARIFY"
    assert result["refusalReason"] is None
    assert result["ticketDraft"] is None
    assert ds.drafts() == []


def test_红线与越界请求不调用模型(ds):
    """Fast-Fail 的要点是「先判红线，再花钱」——注定被拦的请求不该产生推理费。"""
    for case_id in ("sensitive", "off-topic"):
        model = FakeModel()
        result = _wf(ds, model).run_case(case_id)
        assert result["verdict"] == "REFUSED", case_id
        assert model.calls == 0, f"{case_id} 不该调用模型，实际调用了 {model.calls} 次"
        assert result["trace"]["modelCallCount"] == 0
        assert result["trace"]["totalCostUsd"] == 0


def test_门禁节点标记为拦截(ds):
    spans = {s["spanName"]: s for s in _wf(ds).run_case("create-duplicate")["trace"]["spans"]}
    assert spans["4.Action_Gate"]["status"] == "INTERCEPTED"
    assert spans["4.Action_Gate"]["output"]["action"] == "ABORTED"


# ---------------------------------------------------------------- 业务规则落点

def test_建单走决策表定支持组与SLA(ds):
    result = _wf(ds).run_case("create-ok")
    assert (result["teamId"], result["teamName"]) == ("T_HW", "硬件支持组")
    assert result["priority"] == "HIGH"
    assert result["sla"]["completionTargetText"] == "4 个工作小时"


def test_知识问答只引用检索到的当前版本(ds):
    result = _wf(ds).run_case("kb-version")
    assert result["usedVersionIds"] == ["KV-VPN-CONNECT-2"]
    assert "KV-VPN-CONNECT-1" not in result["usedVersionIds"]


def test_查工单不会附带派单信息(ds):
    """非建单路径不应产出 SLA/支持组噪音。"""
    result = _wf(ds).run_case("my-tickets")
    assert result["sla"] == {} and result["teamId"] is None


# ---------------------------------------------------------------- 模型双模

def test_未配模型时token标记为估算(ds):
    result = _wf(ds).run_case("create-ok")
    sources = {s["tokensSource"] for s in result["trace"]["spans"] if s["tokensInput"] or s["tokensOutput"]}
    assert sources == {TOKENS_ESTIMATED}
    assert result["trace"]["estimatedSpans"] == 2


def test_配模型时token来源为reported(ds):
    result = _wf(ds, FakeModel()).run_case("create-ok")
    sources = {s["tokensSource"] for s in result["trace"]["spans"] if s["tokensInput"] or s["tokensOutput"]}
    assert sources == {TOKENS_REPORTED}
    assert result["trace"]["estimatedSpans"] == 0
    assert result["answerText"] == "模型写的答复"


def test_模型声称的版本号必须经引用守卫(ds):
    """模型编造的 versionId 会被剔除，只保留本次真正检索到的。"""
    fake = FakeModel(synthesis={
        "answerText": "根据《VPN 无法连接的排查步骤》……",
        "usedVersionIds": ["KV-VPN-CONNECT-2", "KV-编造的-版本"],
    })
    result = _wf(ds, fake).run_case("kb-version")
    assert result["usedVersionIds"] == ["KV-VPN-CONNECT-2"]
    assert any(f["code"] == "CITATION_REJECTED" for f in result["findings"])


def test_模型故障时降级为模板文案而不中断(ds):
    result = _wf(ds, FakeModel(fail=True)).run_case("create-ok")
    assert result["verdict"] == "DRAFT_READY"
    assert result["answerText"]
    statuses = {s["spanName"]: s["status"] for s in result["trace"]["spans"]}
    assert statuses["3.Answer_Synthesis"] == "FAILED"


def test_模型答复为空时降级为模板而非裸JSON(ds):
    """模型没能写出正文时，员工不该收到空答复，更不该收到原始 JSON。"""
    fake = FakeModel(synthesis={"usedVersionIds": []})
    result = _wf(ds, fake).run_case("create-ok")
    assert result["answerText"].strip(), "不得把空答复交给员工"
    assert "usedVersionIds" not in result["answerText"], "不得把原始 JSON 当答复返回"


def test_模型输出被截断时不返回半截JSON(ds):
    """额度被思维链吃光时 JSON 会被拦腰截断 —— 残片绝不能当答复。"""
    fake = FakeModel(raw_synthesis='{"answerText": "您的建单请求未受理：24小时内已有同分类')
    result = _wf(ds, fake).run_case("create-duplicate")
    assert result["answerText"].strip()
    assert '{"answerText"' not in result["answerText"]
    assert "工单" in result["answerText"], "应回落到可读的拒绝理由"


def test_降级时在链路上留下真实原因(ds):
    """降级必须可区分、原因必须可查，不能悄悄换个答复了事。"""
    fake = FakeModel(raw_synthesis='{"answerText": "半截')
    trace = _wf(ds, fake).run_case("create-ok")["trace"]
    gen = {s["spanName"]: s for s in trace["spans"]}["3.Answer_Synthesis"]
    assert gen["status"] == "FAILED"
    assert gen["detail"]["mode"] == "template-fallback"
    assert gen["detail"]["degradedReason"] == "MODEL_OUTPUT_UNPARSABLE"
    assert "半截" in gen["detail"]["rawOutput"], "原始输出要留痕，便于事后定位"


def test_模型分类与规则不一致时采信模型(ds):
    """规则判知识问答，模型判建单 —— 非安全类分歧以模型为准。"""
    fake = FakeModel(intent_label="CREATE_TICKET")
    result = _wf(ds, fake).run("VPN 连不上，怎么排查？")
    assert result["intent"] == "CREATE_TICKET"


# ---------------------------------------------------------------- 追踪完整性

def test_每条链路都有唯一的traceId(ds):
    wf = _wf(ds)
    ids = {wf.run_case(c.case_id)["trace"]["traceId"] for c in DEMO_CASES}
    assert len(ids) == len(DEMO_CASES)


def test_完整路径的节点拓扑固定(ds):
    spans = [s["spanName"] for s in _wf(ds).run_case("create-ok")["trace"]["spans"]]
    assert spans == [
        "1.Intent_Router",
        "2.Parallel_Knowledge_RAG",
        "2.Parallel_My_Tickets",
        "2.Fork_Join_Reducer",
        "3.Deterministic_Evaluator",
        "3.Answer_Synthesis",
        "4.Action_Gate",
    ]


def test_汇总的token等于各节点之和(ds):
    trace = _wf(ds).run_case("create-ok")["trace"]
    assert trace["totalTokens"] == trace["totalInputTokens"] + trace["totalOutputTokens"]
    assert trace["totalTokens"] == sum(s["tokensInput"] + s["tokensOutput"] for s in trace["spans"])


def test_未知用例报错(ds):
    with pytest.raises(KeyError):
        _wf(ds).run_case("not-a-case")


# ---------------------------------------------------------------- token 估算

def test_估算函数对中文给出量级合理的值():
    # 中文约 0.9 token/字；只要求量级合理，不要求与具体分词器一致
    assert 3 <= estimate_tokens("你好世界") <= 8
    assert estimate_tokens("a" * 400) == pytest.approx(100, abs=3)
    assert estimate_tokens("") >= 1