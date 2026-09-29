import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_schema import validate, DB


class SchemaContractTest(unittest.TestCase):
    def test_baseline_covers_all_canonical_columns_and_indexes(self):
        self.assertEqual(len(validate()),34)

    def test_gate_rejects_missing_table(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('CREATE TABLE ticket_transition','CREATE TABLE missing_ticket_transition'))

    def test_gate_rejects_old_ticket_field(self):
        sql = (DB/'init/00-schema.sql').read_text(encoding='utf-8')
        with self.assertRaises(AssertionError):
            validate(sql.replace('ticket_nature VARCHAR(32)','nature VARCHAR(32)'))

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
