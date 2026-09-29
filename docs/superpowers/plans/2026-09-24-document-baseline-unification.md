# IT Service Ticket Documentation Baseline Unification Plan

**Goal:** Unify all in-scope project documents around the approved architecture baseline without modifying the excluded AI customer-service design document or application code.

**Architecture:** Use a new baseline decision record as the source of truth, then align the PRD, technical SPEC, acceptance protocol, risk register, requirements attribution, roadmap, and repository READMEs. Keep design requirements distinct from current implementation status.

**Tech Stack:** Markdown, Mermaid, DOCX structured editing, Spring Boot 3.2.5, Java 17, MySQL 8.

## Global Constraints

- The excluded file `docs/superpowers/specs/2026-09-23-ai-customer-service-design.md` is not modified or used as an authority.
- P0 includes external notification delivery: WeCom first, SMS fallback for HIGH priority after a 3-second failure/timeout.
- Knowledge-base recommendation is a post-P0 enhancement and is not a required dependency of the core ticket flow.
- MySQL tables provide locking/idempotency; notification deduplication includes `receiver_id`.
- Attachments use local storage in the current baseline.
- Internal primary key `id` uses Snowflake; external business number `ticket_id` remains `TKyyyyMMddNNNN`.
- Draft autosave interval is 20 seconds.
- Error contracts follow the technical SPEC: `40000`, `40100`, `40300`, `40400`, `40401`, `40900`, `500`; business errors use HTTP 200 except authentication HTTP 401.
- Runtime baseline is Spring Boot 3.2.5, Spring Cloud 2023.0.1, Java 17, MySQL 8.

### Task 1: Create the authoritative baseline record

**Files:**
- Create: `docs/IT服务工单系统-基线定义.md`

- [ ] **Step 1: Record approved decisions and terminology**

Include scope, P0/P1/P2 interpretation, IDs, notification semantics, storage, locks, API/error conventions, version baseline, and implementation-status labels.

- [ ] **Step 2: Add a conflict-resolution table**

For each previously conflicting topic, record the selected rule and the superseded wording.

### Task 2: Align technical and acceptance specifications

**Files:**
- Modify: `docs/技术SPEC规格书.md`
- Modify: `docs/IT服务工单系统-验收评测协议书.md`

- [ ] **Step 1: Update technical SPEC architecture and data rules**

Use the approved notification, MySQL lock, receiver-aware dedup key, local attachment, Snowflake internal ID plus business ticket number, 20-second draft, error-code, and Spring Boot 3.2.5 rules.

- [ ] **Step 2: Reconcile P0 acceptance scope**

Keep knowledge recommendation explicitly post-P0. Keep notification delivery in P0 as a required target capability, while marking any not-yet-implemented channel as pending implementation rather than silently excluding it.

- [ ] **Step 3: Align endpoint prefixes and implementation paths**

Use `/api/v1/**` for public APIs and document compatibility aliases only where the PRD requires them.

### Task 3: Align PRD and supporting requirement documents

**Files:**
- Modify: `docs/IT服务工单系统PRD-0921.docx`
- Modify: `docs/IT服务工单系统-需求归因文档.md`
- Modify: `docs/IT服务工单系统-技术风险登记册.md`
- Modify: `docs/it工单系统-Qwen3-4B-算力与基础设施定盘表.md`

- [ ] **Step 1: Update PRD data/API wording**

Clarify the dual-ID model, local attachment storage for the current baseline, notification delivery and deduplication semantics, 20-second drafts, and post-P0 knowledge recommendation.

- [ ] **Step 2: Separate capability state from target requirements**

Mark F-01/F-02 and notification channels with explicit `implemented`, `partially implemented`, or `planned` status; do not claim a target channel is live unless the implementation documents support it.

- [ ] **Step 3: Align risk mitigations and Qwen scope**

Keep Qwen3-4B as optional enhancement capacity planning, not as a dependency of P0 ticket creation.

### Task 4: Align repository guides and roadmap

**Files:**
- Modify: `README.md`
- Modify: `it-ticket-cloud/README.md`
- Modify: `ROADMAP.md`
- Review: `acceptance/README.md`
- Review: `acceptance/reports/验收评测执行记录-实测.md`

- [ ] **Step 1: Align stack, API, state, and error-code descriptions**

Use Spring Boot 3.2.5, `/api/v1`, eight ticket states, SPEC error codes, and the dual-ID terminology.

- [ ] **Step 2: Mark implementation status accurately**

Keep roadmap entries that are not implemented, especially WeCom/SMS dispatch and knowledge recommendation, without contradicting the approved target baseline.

- [ ] **Step 3: Preserve historical execution evidence**

Do not rewrite old acceptance measurements; add a note when a report describes an earlier implementation snapshot.

### Task 5: Verify consistency

- [ ] **Step 1: Scan for superseded terms**

Search for `7 态`, `7 种通知`, `Redis`, `channel_used=LOG`, `20 秒`, `30 秒`, `/api/ticket`, `40001`, `40901`, `Spring Boot 3.3`, and conflicting attachment/ID wording.

- [ ] **Step 2: Re-read all in-scope documents**

Check each document against `docs/IT服务工单系统-基线定义.md` and confirm that the excluded AI design document is untouched.

- [ ] **Step 3: Run repository checks**

Run `git diff --check` and report any remaining historical or intentionally preserved references.
