"""Build an explicit, reviewed main-388f51d -> canonical staging/cutover migration.

This generator is offline. It neither discovers database servers nor executes SQL.
"""
from build_schema import DB, tables, columns
import hashlib
import re

OLD = tables((DB / 'tests/fixtures/main-388f51d-schema.sql').read_text(encoding='utf-8'))
# Published V2_0/V2_1 target is frozen at 470ce57, never current specs.
DEFERRED = set('attachment case_candidate category_field_def engineer_status_log knowledge_cluster ticket_field_value ticket_message work_calendar'.split())
NEW = {name: ddl for name, ddl in tables((DB/'tests/fixtures/canonical-470ce57-schema.sql').read_text(encoding='utf-8')).items() if name not in DEFERRED}
SOURCE = {name: name for name in NEW if name in OLD}
SOURCE.update(user_account='user')
Q = lambda name: '`' + name + '`'


def utc(expr):
    return f"CONVERT_TZ({expr}, @main_source_utc_offset, '+00:00')"


MAP = {
 'user_account': {'display_name':'s.name', 'enabled':"s.status='ACTIVE'"},
 'user_role': {'role_code':"CASE s.role_code WHEN 'KB_ADMIN' THEN 'KNOWLEDGE_ADMIN' ELSE s.role_code END", 'granted_by':"COALESCE(s.granted_by,'SYSTEM')"},
 'support_team': {'enabled':"s.status='ACTIVE'"},
 'team_member': {'enabled':"s.status='ACTIVE'"},
 'category': {'nature':'s.ticket_nature', 'enabled':"s.status='ACTIVE'", 'definition_version':"'legacy-main-v1'"},
 'field_definition': {'field_definition_id':'s.field_id', 'field_key':'s.field_id', 'field_type':"CASE s.field_type WHEN 'RADIO' THEN 'SINGLE_SELECT' WHEN 'CHECKBOX' THEN 'MULTI_SELECT' ELSE s.field_type END", 'options_json':'CAST(s.options AS JSON)', 'display_order':'s.sort_order', 'enabled':'1', 'definition_version':"'legacy-main-v1'"},
 'consultation': {'source':"CASE s.source WHEN 'DIRECT_HUMAN' THEN 'HUMAN_DIRECT' ELSE s.source END", 'resolution_type':"CASE s.resolved_type WHEN 'CONFIRMED' THEN 'EMPLOYEE_CONFIRMED' WHEN 'AUTO' THEN 'AUTO_RESOLVED' ELSE NULL END", 'converted_ticket_id':'s.ticket_id', 'closed_at':utc("CASE WHEN s.status='CLOSED' THEN s.updated_at END")},
 'consultation_message': {'client_message_id':"CONCAT('legacy-',s.message_id)", 'sent_at':utc('s.created_at')},
 'ticket': {'ticket_nature':'s.nature', 'completed_at':utc('s.solved_at')},
 'ticket_draft': {'creator_id':'s.user_id', 'nature':"CASE s.nature WHEN 'REQUEST' THEN 'SERVICE_REQUEST' ELSE s.nature END", 'payload_json':"JSON_OBJECT('ticketNature', CASE s.nature WHEN 'REQUEST' THEN 'SERVICE_REQUEST' ELSE s.nature END, 'categoryId',s.category_id,'title',s.title,'description',s.description,'impactDescription',s.impact_description,'urgencyDescription',s.urgency_description,'location',s.location,'contact',s.contact,'assetId',s.asset_id)", 'last_saved_at':utc('s.updated_at'), 'expires_at':f"DATE_ADD({utc('s.updated_at')}, INTERVAL 7 DAY)", 'created_at':utc('s.updated_at')},
 'ticket_message': {'client_message_id':"CONCAT('legacy-',s.message_id)", 'sender_type':"CASE WHEN s.sender_id='SYSTEM' THEN 'SYSTEM' WHEN EXISTS (SELECT 1 FROM user_role r WHERE r.user_id=s.sender_id AND r.role_code='ENGINEER' AND r.granted_at<=s.created_at AND (r.revoked_at IS NULL OR r.revoked_at>s.created_at)) THEN 'ENGINEER' ELSE 'EMPLOYEE' END", 'sent_at':utc('s.created_at')},
 # Legacy event strings were status projections, not reliable domain action codes.
 'ticket_transition': {'event_code':"CONCAT('LEGACY_',UPPER(s.event))"},
 'assignment': {'end_reason':"CASE s.end_reason WHEN 'TIMEOUT_TRANSFER' THEN 'TIMEOUT' WHEN 'TRANSFER_APPLY' THEN 'TRANSFERRED' ELSE s.end_reason END"},
 'sla_pause': {'reason_type':"CASE s.reason_type WHEN 'SUPPLEMENT' THEN 'PENDING_SUPPLEMENT' WHEN 'EXTERNAL' THEN 'PENDING_EXTERNAL' ELSE s.reason_type END", 'created_at':utc('s.started_at'), 'updated_at':utc('COALESCE(s.ended_at,s.started_at)')},
 'notification': {'channel':"CASE s.channel WHEN 'INBOX' THEN 'IN_APP' ELSE s.channel END"},
 'exception_queue': {'object_type':'s.biz_type','object_id':'s.biz_id','reason_code':'s.exception_type','reason':'s.resolution'},
 'audit_log': {'audit_id':'CAST(s.audit_id AS CHAR)', 'before_json':"CASE WHEN s.before_value IS NULL THEN NULL WHEN JSON_VALID(s.before_value) THEN CAST(s.before_value AS JSON) ELSE JSON_OBJECT('legacyText',s.before_value) END", 'after_json':"CASE WHEN s.after_value IS NULL THEN NULL WHEN JSON_VALID(s.after_value) THEN CAST(s.after_value AS JSON) ELSE JSON_OBJECT('legacyText',s.after_value) END", 'request_id':"COALESCE(s.request_id,CONCAT('legacy-main-audit-',s.audit_id))", 'created_at':utc('s.occurred_at'),'updated_at':utc('s.occurred_at')},
 'knowledge_version': {'content_json':"JSON_OBJECT('title',s.title,'body',s.content)", 'platform_reviewer_id':'s.recheck_by'},
 'knowledge_cluster': {'similarity_basis':"CASE WHEN JSON_VALID(s.similarity_basis) THEN CAST(s.similarity_basis AS JSON) ELSE JSON_OBJECT('legacyText',s.similarity_basis) END"},
 'case_candidate': {'structured_content_json':"CASE WHEN JSON_VALID(s.structured_content) THEN CAST(s.structured_content AS JSON) ELSE JSON_OBJECT('legacyText',s.structured_content) END"},
 'ai_interaction': {'retrieved_versions_json':"COALESCE(CAST(s.retrieved_versions AS JSON),JSON_ARRAY())", 'latency_ms':'COALESCE(s.latency,0)', 'occurred_at':utc('s.created_at'), 'feedback':"CASE s.feedback WHEN 'UNHELPFUL' THEN 'NOT_HELPFUL' WHEN 'WRONG' THEN 'INCORRECT' ELSE s.feedback END"},
}

# These old tables lack essential provenance. They require a separate reviewed adapter,
# not invented object keys, SLA targets or field-definition identifiers.
BLOCKED = {
 'sla_instance':'Original target work seconds/calendar version/STOPPED meaning cannot be recovered; supply reviewed SLA adapter.',
 'work_calendar':'Per-date working intervals require reviewed conversion to versioned service calendar.',
}


def copy_sql(name):
    source = SOURCE[name]
    if source in BLOCKED:
        return ''
    oldcols, newcols = columns(OLD[source]), columns(NEW[name])
    expressions = {}
    for col, definition in newcols.items():
        if 'GENERATED ALWAYS' in definition:
            continue
        if col in MAP.get(name, {}):
            expr = MAP[name][col]
        elif col in oldcols:
            expr = 's.' + Q(col)
            if 'DATETIME' in definition.upper():
                expr = utc(expr)
        elif col == 'version':
            expr = '0'
        elif col == 'updated_at' and 'created_at' in oldcols:
            expr = utc('s.created_at')
        elif 'NOT NULL' not in definition.upper():
            expr = 'NULL'
        elif 'DEFAULT' in definition.upper():
            continue
        else:
            raise ValueError(f'Unmapped required column {name}.{col}')
        expressions[col] = expr
    return f"INSERT INTO {Q('v2_stage_'+name)} ({','.join(map(Q,expressions))})\nSELECT {', '.join(expressions.values())}\nFROM {Q(source)} s;\n"


def guard(table, key, condition, code, detail):
    return f"INSERT INTO migration_v2_issue (entity_type,legacy_id,issue_code,detail) SELECT '{table}',CAST({key} AS CHAR),'{code}','{detail}' FROM {Q(table)} WHERE {condition};\n"


def enum_guard(table, column, values):
    key = next(iter(columns(OLD[table])))
    vals = ','.join("'" + v + "'" for v in values.split())
    return guard(table, Q(key), f'{Q(column)} IS NOT NULL AND {Q(column)} NOT IN ({vals})', 'UNKNOWN_'+column.upper(), f'Unsupported {column}; explicit reviewed mapping required')


def render():
    checksum = hashlib.sha256('\n'.join(NEW.values()).encode()).hexdigest()
    header = "-- Generated by db/tools/build_migration.py; reviewed main 388f51d only.\n-- Execute with a fail-fast versioned runner; never mysql --force. See db/README.md.\nUSE it_ticket_system;\nSET NAMES utf8mb4;\nSET time_zone = '+00:00';\nSET SESSION sql_mode = 'STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';\n"
    stage = header + """
CREATE TABLE IF NOT EXISTS schema_migration_audit (
 version VARCHAR(32) PRIMARY KEY, checksum CHAR(64) NOT NULL,
 operator_id VARCHAR(128) NOT NULL, source_timezone VARCHAR(64) NOT NULL,
 started_at DATETIME(6) NOT NULL, completed_at DATETIME(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS migration_v2_issue (
 issue_id BIGINT AUTO_INCREMENT PRIMARY KEY, entity_type VARCHAR(64) NOT NULL,
 legacy_id VARCHAR(128) NOT NULL, issue_code VARCHAR(128) NOT NULL,
 detail VARCHAR(2000) NOT NULL, created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS migration_v2_counts (
 source_table VARCHAR(64) PRIMARY KEY, target_table VARCHAR(64) NOT NULL,
 source_rows BIGINT NOT NULL, staged_rows BIGINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
DELIMITER $$
CREATE PROCEDURE migration_v2_preflight()
BEGIN
 IF COALESCE(GET_LOCK(CONCAT(DATABASE(),'.schema_v2'),0),0)<>1 THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Another schema migration owns the advisory lock';
 END IF;
 IF COALESCE(@main_writes_stopped,0)<>1 OR COALESCE(@migration_operator,'')='' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Require stopped writers and named migration operator';
 END IF;
 IF @main_source_utc_offset IS NULL OR CONVERT_TZ('2026-01-01 00:00:00',@main_source_utc_offset,'+00:00') IS NULL THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Set explicit verified main source UTC offset; timezone must not be guessed';
 END IF;
 IF EXISTS (SELECT 1 FROM schema_migration_audit WHERE version='V2_0') THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='V2_0 already applied; do not replay';
 END IF;
END$$
DELIMITER ;
CALL migration_v2_preflight();
DROP PROCEDURE migration_v2_preflight;
"""
    guards = []
    for table, detail in BLOCKED.items():
        guards.append(guard(table, Q(next(iter(columns(OLD[table])))), '1=1', 'REQUIRES_REVIEWED_ADAPTER', detail))
    for table, col, vals in [
      ('user','status','ACTIVE DISABLED'),('user_role','role_code','EMPLOYEE ENGINEER PLATFORM_ADMIN KB_ADMIN KNOWLEDGE_ADMIN'),
      ('support_team','status','ACTIVE DISABLED'),('team_member','status','ACTIVE DISABLED'),('category','status','ACTIVE DISABLED'),
      ('category','ticket_nature','INCIDENT SERVICE_REQUEST'),
      ('ticket','nature','INCIDENT SERVICE_REQUEST'),('ticket','status','NEW ASSIGNED IN_PROGRESS PENDING_SUPPLEMENT PENDING_EXTERNAL PENDING_ACCEPTANCE COMPLETED CANCELLED CLOSED'),
      ('ticket','priority','HIGH MEDIUM LOW'),('ticket_draft','nature','INCIDENT REQUEST SERVICE_REQUEST'),
      ('consultation','source','AI DIRECT_HUMAN HUMAN_DIRECT TICKET_FOLLOW_UP'),
      ('consultation','resolved_type','CONFIRMED AUTO'),
      ('consultation','status','AI_ACTIVE WAITING_ENGINEER HUMAN_ACTIVE PENDING_CONFIRMATION RESOLVED CONVERTED_TO_TICKET CLOSED'),
      ('consultation_message','sender_type','EMPLOYEE ENGINEER AI SYSTEM'),
      ('assignment','end_reason','RESPONDED TIMEOUT_TRANSFER TRANSFER_APPLY TIMEOUT TRANSFERRED CANCELLED COMPLETED'),
      ('sla_pause','reason_type','SUPPLEMENT EXTERNAL PENDING_SUPPLEMENT PENDING_EXTERNAL'),
      ('notification','channel','INBOX IN_APP EMAIL'),('notification','status','PENDING SENT FAILED DEAD_LETTER'),
      ('knowledge_article','status','DRAFT PENDING_REVIEW PUBLISHED OFFLINE'),('knowledge_article','risk_level','NORMAL HIGH'),
      ('ai_interaction','feedback','HELPFUL UNHELPFUL WRONG NOT_HELPFUL INCORRECT')]:
        guards.append(enum_guard(table,col,vals))
    guards += [
      guard('user','user_id','department_id IS NULL','MISSING_DEPARTMENT','Identity source must supply department'),
      guard('knowledge_article','article_id','category_id IS NULL','MISSING_CATEGORY','Knowledge category must be reviewed'),
      guard('ai_interaction','interaction_id','retrieved_versions IS NOT NULL AND NOT JSON_VALID(retrieved_versions)','INVALID_JSON','Retrieved versions are invalid JSON'),
      guard('ticket_draft','draft_id','user_id IN (SELECT user_id FROM ticket_draft GROUP BY user_id HAVING COUNT(*)>1)','DUPLICATE_ACTIVE_DRAFT','Explicitly select/archive drafts; never silently discard drafts'),
      guard('user_role','CAST(id AS CHAR)',"user_id IN (SELECT user_id FROM user_role GROUP BY user_id,CASE role_code WHEN 'KB_ADMIN' THEN 'KNOWLEDGE_ADMIN' ELSE role_code END HAVING COUNT(*)>1)",'DUPLICATE_ROLE','Grant history needs reviewed canonical representation'),
      guard('ticket','ticket_id','creator_id NOT IN (SELECT user_id FROM user)','ORPHAN_CREATOR','Ticket creator is absent'),
      guard('ticket','ticket_id','category_id NOT IN (SELECT category_id FROM category)','ORPHAN_CATEGORY','Ticket category is absent'),
      guard('ticket','ticket_id','assignee_id IS NOT NULL AND assignee_id NOT IN (SELECT user_id FROM user)','ORPHAN_ASSIGNEE','Ticket assignee is absent'),
    ]
    # Logical foreign keys are checked before staging because SQL-010 deliberately
    # avoids physical foreign keys. No orphan is repaired by inventing an identity.
    for table,key,column,parent,parent_key in [
      ('user_role','id','user_id','user','user_id'),
      ('team_member','id','team_id','support_team','team_id'),
      ('team_member','id','engineer_id','user','user_id'),
      ('category','category_id','parent_id','category','category_id'),
      ('category_route','id','category_id','category','category_id'),
      ('category_route','id','team_id','support_team','team_id'),
      ('consultation','session_id','creator_id','user','user_id'),
      ('consultation','session_id','category_id','category','category_id'),
      ('consultation','session_id','current_engineer_id','user','user_id'),
      ('consultation','session_id','ticket_id','ticket','ticket_id'),
      ('consultation_message','message_id','session_id','consultation','session_id'),
      ('ticket_transition','transition_id','ticket_id','ticket','ticket_id'),
      ('ticket_draft','draft_id','user_id','user','user_id'),
      ('assignment','assignment_id','engineer_id','user','user_id'),
      ('sla_pause','pause_id','sla_id','sla_instance','sla_id'),
      ('notification','notification_id','receiver_id','user','user_id'),
      ('knowledge_article','article_id','category_id','category','category_id'),
      ('knowledge_article','article_id','current_version_id','knowledge_version','version_id'),
      ('knowledge_version','version_id','article_id','knowledge_article','article_id'),
      ('knowledge_version','version_id','author_id','user','user_id'),
      ('knowledge_version','version_id','reviewer_id','user','user_id'),
      ('ai_interaction','interaction_id','session_id','consultation','session_id'),
    ]:
        guards.append(guard(table,Q(key),f'{Q(column)} IS NOT NULL AND {Q(column)} NOT IN (SELECT {Q(parent_key)} FROM {Q(parent)})','ORPHAN_'+column.upper(),f'{column} has no matching {parent} record'))
    stage += '\n'.join(guards)
    stage += """
SELECT entity_type,legacy_id,issue_code,detail FROM migration_v2_issue ORDER BY issue_id;
DELIMITER $$
CREATE PROCEDURE migration_v2_assert_clean()
BEGIN
 IF EXISTS (SELECT 1 FROM migration_v2_issue) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Migration issues block staging; archive/review the report and provide a reviewed adapter';
 END IF;
END$$
DELIMITER ;
CALL migration_v2_assert_clean();
DROP PROCEDURE migration_v2_assert_clean;
"""
    for name, ddl in NEW.items():
        stage += '\n' + ddl.replace('CREATE TABLE '+name+' (','CREATE TABLE IF NOT EXISTS v2_stage_'+name+' (',1) + '\n'
    stage += "\nDELIMITER $$\nCREATE PROCEDURE migration_v2_copy()\nBEGIN\n DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;\n START TRANSACTION;\n"
    for name, source in SOURCE.items():
        stage += copy_sql(name)
        stage += f"INSERT INTO migration_v2_counts (source_table,target_table,source_rows,staged_rows) SELECT '{source}','{name}',(SELECT COUNT(*) FROM {Q(source)}),(SELECT COUNT(*) FROM {Q('v2_stage_'+name)});\n"
    # Runtime presence must not pretend historical engineers are online after deployment.
    stage += "INSERT INTO v2_stage_engineer_runtime_state (engineer_id,presence,version,created_at,updated_at) SELECT DISTINCT user_id,'OFFLINE',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6) FROM v2_stage_user_role WHERE role_code='ENGINEER' AND revoked_at IS NULL;\n"
    stage += "INSERT INTO v2_stage_service_calendar (calendar_id,timezone,work_week_json,work_intervals_json,lunch_pauses,version,effective_from,created_at,updated_at) VALUES ('DEFAULT','Asia/Shanghai','[1,2,3,4,5]','[{\"start\":\"09:00\",\"end\":\"12:00\"},{\"start\":\"13:00\",\"end\":\"18:00\"}]',1,1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));\n"
    stage += f"INSERT INTO schema_migration_audit (version,checksum,operator_id,source_timezone,started_at,completed_at) VALUES ('V2_0','{checksum}',@migration_operator,@main_source_utc_offset,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));\n COMMIT;\nEND$$\nDELIMITER ;\nCALL migration_v2_copy();\nDROP PROCEDURE migration_v2_copy;\nDO RELEASE_LOCK(CONCAT(DATABASE(),'.schema_v2'));\n"
    (DB / 'migration/V2_0__stage_main_canonical.sql').write_text(stage,encoding='utf-8')

    cutover = header + """
-- Keep the same application maintenance/read-only window through this entire file.
DELIMITER $$
CREATE PROCEDURE migration_v2_cutover_guard()
BEGIN
 IF COALESCE(GET_LOCK(CONCAT(DATABASE(),'.schema_v2'),0),0)<>1 THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Another schema migration owns the advisory lock';
 END IF;
 IF COALESCE(@main_writes_stopped,0)<>1 OR COALESCE(@migration_operator,'')='' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Require stopped writers and named migration operator';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM schema_migration_audit WHERE version='V2_0') OR EXISTS (SELECT 1 FROM schema_migration_audit WHERE version='V2_1') THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Require completed V2_0 and unapplied V2_1';
 END IF;
 IF EXISTS (SELECT 1 FROM migration_v2_issue) OR EXISTS (SELECT 1 FROM migration_v2_counts WHERE source_rows<>staged_rows) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Unresolved migration issues or row-count mismatch';
 END IF;
"""
    for name, source in SOURCE.items():
        cutover += f" IF (SELECT COUNT(*) FROM {Q(source)})<>(SELECT source_rows FROM migration_v2_counts WHERE source_table='{source}') OR (SELECT COUNT(*) FROM {Q('v2_stage_'+name)})<>(SELECT staged_rows FROM migration_v2_counts WHERE source_table='{source}') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Row-count drift: {source}'; END IF;\n"
    cutover += f" IF NOT EXISTS (SELECT 1 FROM schema_migration_audit WHERE version='V2_0' AND checksum='{checksum}') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Staged schema checksum differs from cutover version'; END IF;\n"
    cutover += "END$$\nDELIMITER ;\nCALL migration_v2_cutover_guard();\nDROP PROCEDURE migration_v2_cutover_guard;\n"
    renames = [f'{Q(name)} TO {Q("legacy_v1_"+name)}' for name in SOURCE.values()]
    renames += [f'{Q("v2_stage_"+name)} TO {Q(name)}' for name in NEW]
    cutover += '\n-- One atomic metadata switch. Changed source tables remain available; deferred tables stay untouched.\nRENAME TABLE\n '+',\n '.join(renames)+';\n'
    cutover += f"INSERT INTO schema_migration_audit (version,checksum,operator_id,source_timezone,started_at,completed_at) SELECT 'V2_1','{checksum}',@migration_operator,source_timezone,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6) FROM schema_migration_audit WHERE version='V2_0';\n"
    cutover += "DO RELEASE_LOCK(CONCAT(DATABASE(),'.schema_v2'));\n"
    (DB / 'migration/V2_1__cutover_main_canonical.sql').write_text(cutover,encoding='utf-8')


if __name__ == '__main__':
    render()
