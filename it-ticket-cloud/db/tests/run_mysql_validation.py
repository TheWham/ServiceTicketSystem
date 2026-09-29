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
    assert_query(fresh,"SELECT COUNT(*) FROM category WHERE enabled=1 AND category_id IN ('C_HW_PC','C_HW_PR','C_SW','C_NET','C_ACC','C_OTH');",'6')
    assert_query(fresh,"SELECT COUNT(*) FROM user_account WHERE user_id IN ('U_EMP01','U_ENG01','U_ADM01','U_KBA01');",'4')
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
    run(stage(main),main)
    run(cutover(main),main)
    assert_query(main,metadata_sql(),'')
    assert_query(main,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name LIKE 'legacy_v1_%';",'20')
    assert_query(main,"SELECT ticket_nature,DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s') FROM ticket WHERE ticket_id='TK-LEGACY-1';",'INCIDENT\t2026-09-29 00:00:00')
    assert_query(main,"SELECT creator_id,JSON_UNQUOTE(JSON_EXTRACT(payload_json,'$.ticketNature')) FROM ticket_draft;",'U_EMP01\tSERVICE_REQUEST')
    assert_query(main,"SELECT source FROM consultation;",'HUMAN_DIRECT')
    assert_query(main,"SELECT JSON_UNQUOTE(JSON_EXTRACT(before_json,'$.legacyText')) FROM audit_log;",'plain old text')
    assert_query(main,"SELECT JSON_UNQUOTE(JSON_EXTRACT(content_json,'$.title')) FROM knowledge_version;",'Legacy title')
    assert_query(main,"SELECT file_name,scan_status FROM attachment;",'unchanged.txt\tCLEAN')
    assert_query(main,"SELECT masking_status,status,structured_content FROM case_candidate;",'PENDING\tPENDING\tmain plain text')
    assert_query(main,"SELECT status,similarity_basis FROM knowledge_cluster;",'PENDING\tmain plain text')
    assert_query(main,"SELECT options FROM category_field_def;",'legacy non-JSON')
    assert_query(main,"SELECT field_definition_snapshot,field_value FROM ticket_field_value;",'legacy non-JSON\told value')
    assert_query(main,"SELECT content FROM ticket_message;",'Original ticket message')
    assert_query(main,"SELECT COUNT(*) FROM migration_v2_counts WHERE source_rows<>staged_rows;",'0')
    record('main snapshot upgrade: rows retained, source tables preserved, draft/source/role mapping, explicit UTC conversion')
    record('deferred modules retain original fields, legacy enums, non-JSON text and attachment CLEAN status')

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
