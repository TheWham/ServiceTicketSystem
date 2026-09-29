import hashlib
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_schema import validate, DB


class SchemaContractTest(unittest.TestCase):
    def test_baseline_covers_all_canonical_columns_and_indexes(self):
        self.assertEqual(len(validate()),34)

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

    def test_deferred_case_fields_cannot_be_silently_canonicalized(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('`structured_content` text','`structured_content_json` JSON'))

    def test_unimplemented_tables_are_not_added(self):
        schema = validate()
        for table in ('field_definition','supplement_request','external_wait','ticket_resolution',
                      'ticket_acceptance','ticket_duplicate','attachment_access','outbox_delivery',
                      'ai_provider_config','rag_index_pointer'):
            self.assertNotIn(table,schema)


if __name__=='__main__':
    unittest.main()
