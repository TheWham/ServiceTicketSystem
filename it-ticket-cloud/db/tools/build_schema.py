"""Render the reviewed SQL-007/010 baseline; never connects to a database.

Run from any directory: python it-ticket-cloud/db/tools/build_schema.py
The compatibility fields below are documented in specs/11-main-schema-alignment.md.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
DB = ROOT / 'it-ticket-cloud/db'

# Historical V2_0/1/2 scope, retained for migration verification only.
# Current initialization always renders the complete SQL-009 contract.
IMPLEMENTED = set('user user_role support_team team_member engineer_runtime_state engineer_category_capability category category_route consultation consultation_message ticket ticket_transition ticket_draft assignment sla_instance sla_pause service_calendar calendar_holiday exception_queue notification audit_log idempotency_record outbox_event knowledge_article knowledge_version ai_interaction'.split())


def tables(sql):
    return {m.group(1): m.group(0) for m in re.finditer(
        r'CREATE TABLE\s+`?(\w+)`?\s*\([\s\S]+?\) ENGINE=[^;]+;', sql, re.I)}


def parts(ddl):
    body = ddl[ddl.index('(') + 1:ddl.rindex(') ENGINE=')]
    result, start, depth, quote = [], 0, 0, None
    for i, c in enumerate(body):
        if quote:
            if c == quote and (i == 0 or body[i - 1] != '\\'):
                quote = None
        elif c in "'\"`":
            quote = c
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ',' and depth == 0:
            result.append(body[start:i].strip())
            start = i + 1
    result.append(body[start:].strip())
    return result


def columns(ddl):
    return {p.split()[0].strip('`'): p for p in parts(ddl)
            if not re.match(r'^(PRIMARY|UNIQUE|KEY|INDEX|FULLTEXT|CONSTRAINT|CHECK)\b', p, re.I)}


EXTRAS = {
    'user': ["password_hash VARCHAR(100) COMMENT 'Compatibility: local BCrypt authentication; remove after SSO rollout'"],
    'ticket': [
        'category_snapshot VARCHAR(500)', 'asset_check_status VARCHAR(32)',
        'impact_scope VARCHAR(32)', 'urgency_level VARCHAR(32)',
        'auto_accepted TINYINT(1) NOT NULL DEFAULT 0', 'reopen_count INT NOT NULL DEFAULT 0',
        'idempotency_key VARCHAR(128)', 'first_response_at DATETIME(6)',
        'solved_at DATETIME(6)', 'rating_score INT', 'rating_comment VARCHAR(2000)',
        'rated_at DATETIME(6)', 'KEY idx_ticket_title_category(title,category_id,created_at)',
        'KEY idx_ticket_source_session(source_session_id)',
    ],
    'ticket_draft': ['title VARCHAR(100)', 'description TEXT', 'impact_description TEXT',
                     'urgency_description TEXT', 'location VARCHAR(255)', 'contact VARCHAR(255)', 'asset_id VARCHAR(64)'],
    'sla_instance': ['priority_snapshot VARCHAR(32)', 'near_breach_notified TINYINT(1) NOT NULL DEFAULT 0'],
    'notification': ['title VARCHAR(100)', 'content VARCHAR(500)', 'action_url VARCHAR(200)'],
    'exception_queue': ['title VARCHAR(100)', 'detail VARCHAR(1000)', 'priority VARCHAR(32)'],
    'knowledge_version': ["search_text TEXT GENERATED ALWAYS AS (CONCAT_WS(' ', JSON_UNQUOTE(JSON_EXTRACT(content, '$.title')), JSON_UNQUOTE(JSON_EXTRACT(content, '$.summary')), JSON_UNQUOTE(JSON_EXTRACT(content, '$.keywords')), JSON_UNQUOTE(JSON_EXTRACT(content, '$.body')))) STORED", 'FULLTEXT KEY ft_knowledge_search(search_text) WITH PARSER ngram'],
}


def contract():
    spec = (ROOT / 'docs/specs/06-mysql-ddl-and-migrations.md').read_text(encoding='utf-8')
    section7 = spec.split('## SQL-007 ')[1].split('## SQL-008 ')[0]
    section10 = spec.split('## SQL-010 ')[1]
    definitions = tables(section10 + '\n' + section7)
    assert len(definitions) == 41, len(definitions)
    return definitions


def enum_checks():
    """Map DM enum-typed entity attributes to SQL CHECK expressions."""
    dm = (ROOT / 'docs/specs/01-data-model-strong-types.md').read_text(encoding='utf-8')
    enums = {name: re.findall(r'\b[A-Z][A-Z_]+\b', body)
             for name, body in re.findall(r'public enum (\w+)\s*\{([^}]+)\}', dm)}
    checks = {}
    snake = lambda name: re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    for name, body in re.findall(r'class (\w+)\s*\{([^}]+)\}', dm):
        table = snake(name)
        for typ, attr in re.findall(r'\b(\w+)\s+(\w+)\s*;', body):
            if typ in enums:
                col = snake(attr)
                values = ','.join("'" + value + "'" for value in enums[typ])
                checks.setdefault(table, []).append(
                    f'CONSTRAINT ck_{table}_{col} CHECK ({col} IN ({values}))')
    checks.setdefault('sla_instance', []).append(
        "CONSTRAINT ck_sla_business_link CHECK ((biz_type='TICKET' AND ticket_id IS NOT NULL AND ticket_id=biz_id) OR (biz_type='CONSULTATION' AND ticket_id IS NULL))")
    return checks


def canonical():
    definitions = contract()
    additions_by_table = {name:list(additions) for name,additions in EXTRAS.items()}
    for name, checks in enum_checks().items():
        additions_by_table.setdefault(name, []).extend(checks)
    for name, additions in additions_by_table.items():
        ddl = definitions[name]
        pos = ddl.rindex(') ENGINE=')
        definitions[name] = ddl[:pos].rstrip() + ',\n -- Reviewed compatibility/projection fields; see specs/11.\n ' + ',\n '.join(additions) + '\n' + ddl[pos:]
    # Emit all columns as separate lines, making the reviewed baseline easy to compare.
    definitions = {name: re.sub(r'--[^\n]*\n', '', ddl) for name, ddl in definitions.items()}
    # Explicit contract execution order; no legacy tables or migration helpers.
    order = ('user user_role support_team team_member engineer_runtime_state engineer_category_capability '
             'category category_route field_definition ai_provider_config consultation consultation_message '
             'ticket ticket_field_value ticket_transition ticket_duplicate attachment_access '
             'service_calendar calendar_holiday exception_queue outbox_delivery '
             'ticket_message ticket_draft supplement_request external_wait ticket_resolution ticket_acceptance '
             'attachment assignment sla_instance sla_pause notification audit_log idempotency_record outbox_event '
             'case_candidate knowledge_article knowledge_version knowledge_cluster ai_interaction rag_index_pointer').split()
    assert set(order) == set(definitions)
    return {name: definitions[name] for name in order}


def write_baseline():
    header = "-- Generated by it-ticket-cloud/db/tools/build_schema.py from PRD 2.2 / DM / SQL-007 + SQL-010.\n-- Complete 41-table contract. Fresh empty database only; not an existing-data migration.\n-- Published V2_0/1/2 target the historical 34-table model only.\nCREATE DATABASE IF NOT EXISTS it_ticket_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\nUSE it_ticket_system;\nSET NAMES utf8mb4;\nSET time_zone = '+00:00';\n\n"
    schema = header + '\n\n'.join(canonical().values()) + '\n'
    (DB / 'init/00-schema.sql').write_text(schema, encoding='utf-8')
    seeds = [(DB/'init'/name).read_text(encoding='utf-8-sig').strip()
             for name in ('10-seed.sql', '11-knowledge-seed.sql')]
    (ROOT/'db/it_ticket_system_init_v2.sql').write_text(
        '-- Single-file entrypoint: schema + the same runtime seeds. Do not also run db/init.\n'
        + schema + '\n' + '\n\n'.join(seeds) + '\n', encoding='utf-8')


if __name__ == '__main__':
    write_baseline()
