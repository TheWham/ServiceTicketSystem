"""Execute the baseline/migration in disposable schemas on an isolated local MySQL.

Never reads application credentials. Never selects it_ticket_system or drops a schema.
The caller owns the isolated server lifecycle; generated schema names are printed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid

DB = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DB/'tools'))
from validate_schema import metadata_sql
from build_schema import tables, IMPLEMENTED

ARGS = None
PREFIX = 'schema_test_' + uuid.uuid4().hex[:10]
SCHEMAS = []
RESULTS = []
PARAMS = "SET @main_writes_stopped=1; SET @migration_operator='isolated-schema-test'; SET @main_source_utc_offset='+08:00';\n"


def run(sql, db=None, fail_contains=None):
    args = [ARGS.mysql,'--no-defaults','--protocol=TCP','--host=127.0.0.1',f'--port={ARGS.port}',
            '--user=root','--default-character-set=utf8mb4','--batch','--skip-column-names']
    if db:
        args.append('--database='+db)
    result = subprocess.run(args,input=sql.encode('utf-8'),capture_output=True)
    stdout, stderr = result.stdout.decode('utf-8','replace'), result.stderr.decode('utf-8','replace')
    if fail_contains:
        assert result.returncode != 0 and fail_contains in stderr, (stdout,stderr)
    else:
        assert result.returncode == 0, (stdout,stderr)
    return stdout.strip()


def script(relative, database):
    return (DB/relative).read_text(encoding='utf-8-sig').replace('it_ticket_system',database)


def schema(suffix, legacy=True):
    name = PREFIX+'_'+suffix
    SCHEMAS.append(name)
    run(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    if legacy:
        run(script('tests/fixtures/main-388f51d-schema.sql',name),name)
        run(script('tests/fixtures/main-388f51d-seed.sql',name),name)
    return name


def stage(db):
    return PARAMS + script('migration/V2_0__stage_main_canonical.sql',db)


def cutover(db):
    return PARAMS + script('migration/V2_1__cutover_main_canonical.sql',db)


def latest(db):
    return PARAMS + "SET @canonical_source_revision='470ce57';\n" + script('migration/V2_2__align_prd_field_names.sql',db)


def deferred_definitions(db):
    names = set(tables((DB/'tests/fixtures/main-388f51d-schema.sql').read_text(encoding='utf-8'))) - IMPLEMENTED
    return {name: run(f'SHOW CREATE TABLE `{name}`;', db) for name in sorted(names)}


def assert_query(db,sql,expected):
    actual = run(sql,db)
    assert actual == expected, (sql,expected,actual)


def record(name):
    RESULTS.append(name)
    print('PASS: '+name,flush=True)


def validate():
    fresh = schema('fresh',False)
    for file in sorted((DB/'init').glob('*.sql')):
        run(script(str(file.relative_to(DB)),fresh),fresh)
    assert_query(fresh,metadata_sql(),'')
    assert_query(fresh,'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();','34')
    assert_query(fresh,"SELECT COUNT(*) FROM category WHERE status='ACTIVE' AND category_id IN ('C_HW_PC','C_HW_PR','C_SW','C_NET','C_ACC','C_OTH');",'6')
    assert_query(fresh,"SELECT COUNT(*) FROM `user` WHERE user_id IN ('U_EMP01','U_ENG01','U_ADM01','U_KBA01');",'4')
    assert_query(fresh,"SELECT COUNT(*) FROM user_role WHERE role_code='KNOWLEDGE_ADMIN';",'1')
    assert_query(fresh,"SELECT COUNT(*) FROM knowledge_version WHERE MATCH(search_text) AGAINST('打印机' IN NATURAL LANGUAGE MODE);",'1')
    record('fresh baseline: 26 implemented canonical + 8 unchanged main tables, metadata, shared identities/categories and ngram search')

    main = schema('upgrade')
    run("""
INSERT INTO ticket (ticket_id,creator_id,nature,category_id,title,description,impact_description,urgency_description,status,priority,created_at,updated_at)
VALUES ('TK-LEGACY-1','U_EMP01','INCIDENT','C_HW_PC','Legacy ticket','Retain the complete historical description','One employee','Work blocked','NEW','MEDIUM','2026-09-29 08:00:00','2026-09-29 08:00:00');
INSERT INTO ticket_draft (draft_id,user_id,nature,title,description,updated_at) VALUES ('DRAFT-LEGACY','U_EMP01','REQUEST','Partial draft','Unsaved payload','2026-09-29 08:00:00');
INSERT INTO consultation (session_id,creator_id,category_id,status,source,created_at,updated_at) VALUES ('CS-LEGACY','U_EMP01','C_NET','AI_ACTIVE','DIRECT_HUMAN','2026-09-29 08:00:00','2026-09-29 08:00:00');
INSERT INTO consultation_message (message_id,session_id,sender_id,sender_type,content,created_at) VALUES ('MSG-LEGACY','CS-LEGACY','U_EMP01','EMPLOYEE','Original message remains intact','2026-09-29 08:00:00');
INSERT INTO audit_log (actor_id,action,object_type,object_id,before_value,after_value,occurred_at) VALUES ('U_EMP01','LEGACY_ACTION','TICKET','TK-LEGACY-1','plain old text','{"status":"NEW"}','2026-09-29 08:00:00');
INSERT INTO knowledge_article (article_id,category_id,status,current_version_id) VALUES ('KA-LEGACY','C_NET','PUBLISHED','KV-LEGACY');
INSERT INTO knowledge_version (version_id,article_id,version_no,title,content,author_id) VALUES ('KV-LEGACY','KA-LEGACY',1,'Legacy title','Legacy body','U_ENG01');
INSERT INTO attachment (attachment_id,biz_type,biz_id,uploader_id,file_name,size,hash,scan_status) VALUES ('ATT-KEEP','TICKET','TK-LEGACY-1','U_EMP01','unchanged.txt',3,REPEAT('a',64),'CLEAN');
INSERT INTO case_candidate (case_id,source_type,source_id,structured_content) VALUES ('CASE-KEEP','TICKET','TK-LEGACY-1','main plain text');
INSERT INTO knowledge_cluster (cluster_id,similarity_basis) VALUES ('CLUSTER-KEEP','main plain text');
INSERT INTO category_field_def (field_id,category_id,name,field_type,options) VALUES ('FIELD-KEEP','C_NET','Legacy field','RADIO','legacy non-JSON');
INSERT INTO engineer_status_log (engineer_id,status,source) VALUES ('U_ENG01','AVAILABLE','MANUAL');
INSERT INTO ticket_field_value (ticket_id,field_definition_snapshot,field_value) VALUES ('TK-LEGACY-1','legacy non-JSON','old value');
INSERT INTO ticket_message (message_id,ticket_id,sender_id,content) VALUES ('TM-KEEP','TK-LEGACY-1','U_EMP01','Original ticket message');
""",main)
    deferred_before = deferred_definitions(main)
    run(stage(main),main)
    run(cutover(main),main)
    run(latest(main),main)
    assert deferred_definitions(main) == deferred_before
    assert_query(main,metadata_sql(),'')
    assert_query(main,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name LIKE 'legacy_v1_%';",'20')
    assert_query(main,"SELECT nature,DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s') FROM ticket WHERE ticket_id='TK-LEGACY-1';",'INCIDENT\t2026-09-29 00:00:00')
    assert_query(main,"SELECT creator_id,JSON_UNQUOTE(JSON_EXTRACT(payload_json,'$.ticketNature')) FROM ticket_draft;",'U_EMP01\tSERVICE_REQUEST')
    assert_query(main,"SELECT source FROM consultation;",'HUMAN_DIRECT')
    assert_query(main,"SELECT JSON_UNQUOTE(JSON_EXTRACT(before_value,'$.legacyText')) FROM audit_log;",'plain old text')
    assert_query(main,"SELECT JSON_UNQUOTE(JSON_EXTRACT(content,'$.title')) FROM knowledge_version;",'Legacy title')
    assert_query(main,"SELECT file_name,scan_status FROM attachment;",'unchanged.txt\tCLEAN')
    assert_query(main,"SELECT masking_status,status,structured_content FROM case_candidate;",'PENDING\tPENDING\tmain plain text')
    assert_query(main,"SELECT status,similarity_basis FROM knowledge_cluster;",'PENDING\tmain plain text')
    assert_query(main,"SELECT options FROM category_field_def;",'legacy non-JSON')
    assert_query(main,"SELECT field_definition_snapshot,field_value FROM ticket_field_value;",'legacy non-JSON\told value')
    assert_query(main,"SELECT content FROM ticket_message;",'Original ticket message')
    assert_query(main,"SELECT COUNT(*) FROM migration_v2_counts WHERE source_rows<>staged_rows;",'0')
    record('main snapshot upgrade: rows retained, source tables preserved, draft/source/role mapping, explicit UTC conversion')
    record('deferred modules retain original fields, legacy enums, non-JSON text and attachment CLEAN status')

    canonical = schema('canonical470',False)
    run(script('tests/fixtures/canonical-470ce57-schema.sql',canonical),canonical)
    run(script('tests/fixtures/canonical-470ce57-seed.sql',canonical),canonical)
    run("""
UPDATE user_account SET enabled=0,display_name='Retained disabled identity',version=42,created_at='2026-09-29 00:00:00.123456',updated_at='2026-09-29 01:00:00.654321' WHERE user_id='U_EMP01';
UPDATE support_team SET enabled=0 WHERE team_id='T_HW';
UPDATE team_member SET enabled=0 WHERE team_id='T_HW';
UPDATE category SET enabled=0 WHERE category_id='C_HW_PC';
INSERT INTO ticket (ticket_id,creator_id,ticket_nature,category_id,title,description,impact_description,urgency_description,status,priority,field_snapshot_json,created_at,updated_at) VALUES ('TK470','U_EMP01','INCIDENT','C_HW_PC','Existing ticket','Full description','Single employee','Blocked','NEW','HIGH','{"legacyKey":[1,"text"]}','2026-09-29 00:00:00.123456','2026-09-29 01:00:00.654321');
INSERT INTO ticket_draft (draft_id,creator_id,nature,payload_json,last_saved_at,expires_at,created_at,updated_at) VALUES ('DR470','U_EMP01','SERVICE_REQUEST','{"ticketNature":"SERVICE_REQUEST"}','2026-09-29 00:00:00.123456','2026-10-06 00:00:00.123456','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
INSERT INTO work_calendar (cal_date,day_type,start_time,end_time) VALUES ('2026-09-29','WORKDAY','09:00:00','18:00:00');
INSERT INTO consultation (session_id,creator_id,status,source,resolution_type,created_at,updated_at) VALUES ('CS470','U_EMP01','RESOLVED','AI','EMPLOYEE_CONFIRMED','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
INSERT INTO ticket_transition (transition_id,ticket_id,to_status,event_code,operator_id,occurred_at) VALUES ('TR470','TK470','ASSIGNED','TICKET_ASSIGNED','U_ENG01','2026-09-29 00:00:00.123456');
INSERT INTO sla_instance (sla_id,biz_type,biz_id,sla_type,status,target_work_seconds,breached_at,calendar_id,calendar_version,created_at,updated_at) VALUES ('SLAT470','TICKET','TK470','TICKET_RESPONSE','BREACHED',1800,'2026-09-29 00:30:00.123456','DEFAULT',1,'2026-09-29 00:00:00.123456','2026-09-29 00:30:00.123456'),('SLAC470','CONSULTATION','CS470','CONSULTATION_RESPONSE','RUNNING',1800,NULL,'DEFAULT',1,'2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
INSERT INTO knowledge_version (version_id,article_id,version_no,content_json,author_id,created_at,updated_at) VALUES ('KV470','KA470',1,'{"title":"Retained knowledge","body":"printer workflow"}','U_ENG01','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
INSERT INTO ai_interaction (interaction_id,session_id,model_version,retrieved_versions_json,confidence,feedback,latency_ms,occurred_at,created_at,updated_at) VALUES ('AI470','CS470','MODEL470','["KV470"]',0.8123,'NOT_HELPFUL',2468,'2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
INSERT INTO audit_log (audit_id,actor_id,action,object_type,object_id,before_json,after_json,request_id,occurred_at,created_at,updated_at) VALUES ('AU470','U_ENG01','TICKET_ASSIGNED','TICKET','TK470','{"status":"NEW"}','{"status":"ASSIGNED"}','REQ470','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456','2026-09-29 00:00:00.123456');
""",canonical)
    before = deferred_definitions(canonical)
    run(latest(canonical),canonical)
    assert deferred_definitions(canonical) == before
    assert_query(canonical,metadata_sql(),'')
    assert_query(canonical,"SELECT name,status,version,DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s.%f'),DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s.%f') FROM `user` WHERE user_id='U_EMP01';",'Retained disabled identity\tDISABLED\t42\t2026-09-29 00:00:00.123456\t2026-09-29 01:00:00.654321')
    assert_query(canonical,"SELECT status FROM `user` WHERE user_id='U_ENG01';",'ACTIVE')
    for table in ('support_team','team_member'):
        assert_query(canonical,f"SELECT status FROM {table} WHERE team_id='T_HW';",'DISABLED')
    assert_query(canonical,"SELECT ticket_nature,status FROM category WHERE category_id='C_HW_PC';",'INCIDENT\tDISABLED')
    assert_query(canonical,"SELECT field_definition_snapshot=legacy_v2_ticket.field_snapshot_json FROM ticket JOIN legacy_v2_ticket USING(ticket_id);",'1')
    assert_query(canonical,"SELECT ticket_nature,DATE_FORMAT(last_saved_at,'%Y-%m-%d %H:%i:%s.%f') FROM ticket_draft;",'SERVICE_REQUEST\t2026-09-29 00:00:00.123456')
    assert_query(canonical,"SELECT day_type FROM work_calendar;",'WORKDAY')
    assert_query(canonical,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name LIKE 'legacy_v2_%';",'12')
    assert_query(canonical,"SELECT resolved_type FROM consultation WHERE session_id='CS470';",'EMPLOYEE_CONFIRMED')
    assert_query(canonical,"SELECT event FROM ticket_transition WHERE transition_id='TR470';",'TICKET_ASSIGNED')
    assert_query(canonical,"SELECT ticket_id,biz_id,DATE_FORMAT(breach_at,'%Y-%m-%d %H:%i:%s.%f') FROM sla_instance WHERE sla_id='SLAT470';",'TK470\tTK470\t2026-09-29 00:30:00.123456')
    assert_query(canonical,"SELECT ticket_id IS NULL,biz_id FROM sla_instance WHERE sla_id='SLAC470';",'1\tCS470')
    assert_query(canonical,"SELECT content=legacy_v2_knowledge_version.content_json FROM knowledge_version JOIN legacy_v2_knowledge_version USING(version_id);",'1')
    assert_query(canonical,"SELECT COUNT(*) FROM knowledge_version WHERE MATCH(search_text) AGAINST('printer' IN NATURAL LANGUAGE MODE);",'1')
    assert_query(canonical,"SELECT retrieved_versions=legacy_v2_ai_interaction.retrieved_versions_json,latency,ai_interaction.confidence,ai_interaction.feedback FROM ai_interaction JOIN legacy_v2_ai_interaction USING(interaction_id);",'1\t2468\t0.8123\tNOT_HELPFUL')
    assert_query(canonical,"SELECT before_value=legacy_v2_audit_log.before_json,after_value=legacy_v2_audit_log.after_json FROM audit_log JOIN legacy_v2_audit_log USING(audit_id);",'1\t1')
    record('470ce57 direct upgrade: ACTIVE/DISABLED, names, JSON snapshots, microsecond UTC, versions, indexes and all deferred definitions/data retained')
    record('PRD fields preserve SLA business links/breach instant, consultation result, transition action, knowledge JSON/fulltext, AI citation/latency/feedback, audit JSON')
    run(latest(canonical),canonical,'V2_2 already applied')
    record('V2_2 successful versions cannot be replayed')

    invalid470 = schema('invalid470',False)
    run(script('tests/fixtures/canonical-470ce57-schema.sql',invalid470),invalid470)
    run(script('tests/fixtures/canonical-470ce57-seed.sql',invalid470),invalid470)
    run("UPDATE user_account SET enabled=2 WHERE user_id='U_EMP01';",invalid470)
    run(latest(invalid470),invalid470,'Unknown enabled value: user_account')
    assert_query(invalid470,"SELECT enabled FROM user_account WHERE user_id='U_EMP01';",'2')
    record('V2_2 unknown boolean source blocks before copying without losing source value')

    extra470 = schema('extra_column470',False)
    run(script('tests/fixtures/canonical-470ce57-schema.sql',extra470),extra470)
    run(script('tests/fixtures/canonical-470ce57-seed.sql',extra470),extra470)
    run("ALTER TABLE user_account ADD COLUMN unknown_business_fact VARCHAR(64); UPDATE user_account SET unknown_business_fact='must-survive' WHERE user_id='U_EMP01';",extra470)
    run(latest(extra470),extra470,'Unexpected source columns: user_account')
    assert_query(extra470,"SELECT unknown_business_fact FROM user_account WHERE user_id='U_EMP01';",'must-survive')
    assert_query(extra470,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name LIKE 'v2_2_stage_%';",'0')
    record('V2_2 extra source column blocks before staging and preserves unknown business data')

    missing = schema('no_timezone')
    run("SET @main_writes_stopped=1; SET @migration_operator='test';\n"+script('migration/V2_0__stage_main_canonical.sql',missing),missing,'Set explicit verified main source UTC offset')
    assert_query(missing,'SELECT COUNT(*) FROM user;','4')
    record('missing source timezone blocks migration without changing source rows')

    invalid = schema('unknown_enum')
    run("UPDATE user_role SET role_code='UNKNOWN_ROLE' WHERE user_id='U_EMP01';",invalid)
    run(stage(invalid),invalid,'Migration issues block staging')
    assert_query(invalid,"SELECT issue_code FROM migration_v2_issue;",'UNKNOWN_ROLE_CODE')
    record('unknown enum is reported and blocks migration')

    unsafe = schema('ambiguous_sla')
    run("INSERT INTO sla_instance (sla_id,ticket_id,sla_type,priority_snapshot) VALUES ('SLA1','TK1','COMPLETION','HIGH');",unsafe)
    run(stage(unsafe),unsafe,'Migration issues block staging')
    assert_query(unsafe,'SELECT COUNT(*) FROM sla_instance;','1')
    record('unrecoverable SLA target/calendar provenance blocks migration and preserves source')

    drift = schema('row_drift')
    run(stage(drift),drift)
    run("INSERT INTO support_team (team_id,name) VALUES ('T-LATE','Late writer');",drift)
    run(cutover(drift),drift,'Row-count drift: support_team')
    assert_query(drift,'SELECT COUNT(*) FROM user;','4')
    record('post-staging row-count drift blocks atomic cutover')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mysql',required=True)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--report',type=Path)
    ARGS=parser.parse_args()
    try:
        validate()
    finally:
        report={'mysqlEndpoint':f'127.0.0.1:{ARGS.port}','schemas':SCHEMAS,'passed':RESULTS,
                'productionDatabaseAccessed':False}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if ARGS.report:
            ARGS.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
