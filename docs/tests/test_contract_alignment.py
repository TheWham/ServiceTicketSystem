"""Executable document contract: PRD business fields must survive DM/SQL/API mapping.

Run: python -m unittest discover -s docs/tests -p 'test_*.py'
Requires PyYAML for parsing the existing OpenAPI artifact.
"""
from pathlib import Path
import json
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / 'docs/specs'
PRD = (ROOT / 'docs/IT服务工单系统PRD-Ultimate.md').read_text(encoding='utf-8')
SQL = (SPECS / '06-mysql-ddl-and-migrations.md').read_text(encoding='utf-8')


class ContractAlignmentTest(unittest.TestCase):
    def test_prd_business_fields_exist_in_both_executable_entrypoints(self):
        core = PRD.split('## 20. ')[1].split('## 21. ')[0]
        entities = re.findall(r'^\|[^|]*`(\w+)`[^|]*\|\s*`([^`]+)`', core, re.M)
        for path in ('db/it_ticket_system_init_v2.sql', 'it-ticket-cloud/db/init/00-schema.sql'):
            sql = (ROOT/path).read_text(encoding='utf-8')
            tables = {m.group(1): m.group(2) for m in re.finditer(
                r'CREATE TABLE\s+`?(\w+)`?\s*\(([\s\S]+?)\) ENGINE=', sql)}
            for table, fields in entities:
                with self.subTest(path=path, table=table):
                    self.assertIn(table,tables)
                    for field in fields.split(','):
                        self.assertRegex(tables[table],rf'(?i)\b{field.strip()}`?\s+(?:VARCHAR|CHAR|TEXT|MEDIUMTEXT|JSON|BIGINT|INT|DATETIME|DECIMAL|TINYINT|SMALLINT)\b')

    def test_dm_entities_preserve_prd_business_fields(self):
        dm = (SPECS / '01-data-model-strong-types.md').read_text(encoding='utf-8')
        classes = {m.group(1): m.group(2) for m in re.finditer(r'class (\w+)\s*\{([^}]+)\}', dm)}
        core = PRD.split('## 20. ')[1].split('## 21. ')[0]
        for table, fields in re.findall(r'^\|[^|]*`(\w+)`[^|]*\|\s*`([^`]+)`', core, re.M):
            name = ''.join(part.title() for part in table.split('_'))
            with self.subTest(entity=name):
                self.assertIn(name, classes)
                for field in fields.split(','):
                    parts = field.strip().split('_')
                    java_field = parts[0] + ''.join(part.title() for part in parts[1:])
                    self.assertRegex(classes[name], rf'\b{java_field}\s*[;=]')

    def test_every_prd_business_field_exists_in_sql_contract(self):
        core = PRD.split('## 20. ')[1].split('## 21. ')[0]
        entities = re.findall(r'^\|[^|]*`(\w+)`[^|]*\|\s*`([^`]+)`', core, re.M)
        tables = {m.group(1): m.group(2) for m in re.finditer(
            r'CREATE TABLE\s+`?(\w+)`?\s*\(([\s\S]+?)\) ENGINE=', SQL)}
        self.assertGreaterEqual(len(entities), 20)
        for table, fields in entities:
            with self.subTest(table=table):
                self.assertIn(table, tables)
                for field in [f.strip() for f in fields.split(',')]:
                    self.assertRegex(tables[table], rf'\b{field}\s+(?:VARCHAR|CHAR|TEXT|MEDIUMTEXT|JSON|BIGINT|INT|DATETIME|DECIMAL|TINYINT|SMALLINT)\b')

    def test_api_business_names_match_prd_and_updated_spec(self):
        api = yaml.safe_load((SPECS / '05-http-api-openapi.yaml').read_text(encoding='utf-8'))
        schemas = api['components']['schemas']
        self.assertIn('nature', schemas['TicketCreate']['required'])
        self.assertNotIn('ticket_nature', schemas['TicketCreate']['properties'])
        self.assertIn('event', schemas['TransitionProjection']['required'])
        self.assertEqual(set(schemas['UserProjection']['required']),
            {'user_id', 'employee_no', 'name', 'department_id', 'status', 'identity_source'})
        self.assertNotIn('display_name', schemas['UserProjection']['properties'])
        self.assertNotIn('enabled', schemas['UserProjection']['properties'])
        self.assertIn('status', schemas['TeamProjection']['required'])
        self.assertIn('status', schemas['CategoryProjection']['required'])
        self.assertIn('ticket_nature', schemas['CategoryProjection']['required'])

    def test_authoritative_specs_do_not_reintroduce_replaced_identifiers(self):
        # Historical migration reports are deliberately excluded.
        forbidden = [r'\bevent_code\b', r'\bresolution_type\b', r'\bbreached_at\b',
                     r'\bbefore_json\b', r'\bafter_json\b', r'\bcontent_json\b',
                     r'\bretrieved_versions_json\b', r'\blatency_ms\b', r'\bfield_snapshot_json\b']
        for file in sorted(SPECS.glob('*')):
            if not re.match(r'(0[1-9]|10)-', file.name):
                continue
            content = file.read_text(encoding='utf-8')
            for pattern in forbidden:
                with self.subTest(file=file.name, pattern=pattern):
                    self.assertNotRegex(content, pattern)

    def test_all_json_examples_are_parseable(self):
        count = 0
        for file in SPECS.glob('*.md'):
            if not re.match(r'(0[1-9]|10)-', file.name):
                continue
            for snippet in re.findall(r'(?:```|~~~)json\s+([\s\S]*?)(?:```|~~~)', file.read_text(encoding='utf-8')):
                json.loads(snippet)
                count += 1
        self.assertGreater(count, 10)


if __name__ == '__main__':
    unittest.main()
