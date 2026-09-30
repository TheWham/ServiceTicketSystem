import hashlib
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_schema import validate, DB


class SchemaContractTest(unittest.TestCase):
    def test_baseline_covers_all_canonical_columns_and_indexes(self):
        self.assertEqual(len(validate()),41)

    def test_latest_identity_status_and_snapshot_contract(self):
        from build_schema import tables, columns
        actual = tables((DB/'init/00-schema.sql').read_text(encoding='utf-8'))
        self.assertIn('user', actual)
        self.assertNotIn('user_account', actual)
        for table in ('user', 'support_team', 'team_member', 'category'):
            self.assertIn('status', columns(actual[table]))
            self.assertNotIn('enabled', columns(actual[table]))
        self.assertIn('name', columns(actual['user']))
        for table in ('category', 'ticket_draft'):
            self.assertIn('ticket_nature', columns(actual[table]))
        self.assertIn('field_definition_snapshot', columns(actual['ticket']))

    def test_prd_business_field_names(self):
        from build_schema import tables, columns
        actual = tables((DB/'init/00-schema.sql').read_text(encoding='utf-8'))
        for table, names in {'ticket':['nature'], 'consultation':['resolved_type'],
                'ticket_transition':['event'], 'sla_instance':['ticket_id','breach_at'],
                'knowledge_version':['content'], 'ai_interaction':['retrieved_versions','latency'],
                'audit_log':['before_value','after_value']}.items():
            for name in names:
                self.assertIn(name, columns(actual[table]), f'{table}.{name}')

    def test_published_migrations_remain_immutable(self):
        expected = {'V2_0__stage_main_canonical.sql': '879ec56a246664d373808d9286e0550bfb28a2641856705a39243da5f3c70848', 'V2_1__cutover_main_canonical.sql': '59a2dc7690f507ab9a1ad1746bbb00d2044e8fcbf65047537d4c3bd429bfe308'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((DB/'migration'/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((DB/'migration/V2_2__align_prd_field_names.sql').read_bytes()).hexdigest(),
                         '51ba471d119b0155006fc31f55f8f109db8105263fa1485c54bd089388921200')
        self.assertEqual(hashlib.sha256((DB/'tests/fixtures/canonical-prd22-34-schema.sql').read_bytes()).hexdigest(),
                         'a927ba1ae0b184d373d46568361fe4d1657feeb492cb292b1d7292c8fb940da0')

    def test_gate_rejects_missing_table(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('CREATE TABLE ticket_transition','CREATE TABLE missing_ticket_transition'))

    def test_gate_rejects_old_ticket_field(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('nature VARCHAR(32) NOT NULL, category_id','ticket_nature VARCHAR(32) NOT NULL, category_id'))

    def test_gate_rejects_lost_draft_unique_key(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('UNIQUE KEY uk_active_draft','KEY uk_active_draft'))

    def test_gate_rejects_wrong_precision(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('confidence DECIMAL(8,4)','confidence DECIMAL(4,3)'))

    def test_gate_rejects_case_payload_renamed_away_from_prd(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('structured_content JSON','structured_content_json JSON'))

    def test_full_contract_includes_previously_deferred_tables(self):
        schema = validate()
        for table in ('field_definition','supplement_request','external_wait','ticket_resolution',
                      'ticket_acceptance','ticket_duplicate','attachment_access','outbox_delivery',
                      'ai_provider_config','rag_index_pointer'):
            self.assertIn(table,schema)
        for table in ('category_field_def','engineer_status_log','work_calendar'):
            self.assertNotIn(table,schema)

    def test_root_entrypoint_contains_the_same_schema_and_seeds(self):
        from build_schema import ROOT, tables
        root_sql = (ROOT/'db/it_ticket_system_init_v2.sql').read_text(encoding='utf-8')
        self.assertNotIn('\ufeff',root_sql)
        self.assertEqual(tables(root_sql), validate())
        for name in ('10-seed.sql','11-knowledge-seed.sql'):
            self.assertIn((DB/'init'/name).read_text(encoding='utf-8-sig').strip(), root_sql)

    def test_formerly_deferred_json_and_message_contract(self):
        from build_schema import columns
        schema = validate()
        for table, field in [('case_candidate','structured_content'),('knowledge_cluster','similarity_basis'),
                             ('ticket_field_value','field_definition_snapshot'),('ticket_field_value','field_value')]:
            self.assertIn('JSON NOT NULL', columns(schema[table])[field])
        for field in ('object_key','content_type','uploaded_at','updated_at'):
            self.assertIn(field, columns(schema['attachment']))
        for field in ('sender_type','client_message_id','sent_at','withdraw_reason','updated_at'):
            self.assertIn(field, columns(schema['ticket_message']))

    def test_all_tables_have_prd_creation_and_update_metadata(self):
        from build_schema import columns
        for table, ddl in validate().items():
            with self.subTest(table=table):
                self.assertIn('created_at',columns(ddl))
                self.assertIn('updated_at',columns(ddl))

    def test_gate_rejects_extra_not_null_on_consultation_sla_ticket_id(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('ticket_id VARCHAR(32), biz_type', 'ticket_id VARCHAR(32) NOT NULL, biz_type'))

    def test_gate_rejects_missing_enum_or_sla_link_constraint(self):
        from build_schema import parts, tables
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        schema = tables(sql)
        for table, name in [('attachment','ck_attachment_scan_status'),('sla_instance','ck_sla_business_link')]:
            constraint = next(p for p in parts(schema[table]) if p.startswith('CONSTRAINT '+name+' '))
            with self.subTest(constraint=name), self.assertRaises(AssertionError):
                validate(sql.replace(constraint, 'CONSTRAINT placeholder CHECK (1=1)'))


if __name__=='__main__':
    unittest.main()
