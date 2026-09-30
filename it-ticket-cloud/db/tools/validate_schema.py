"""Offline SQL contract gate; optionally emit read-only MySQL metadata checks.

python db/tools/validate_schema.py [--emit-sql path.sql]
No database credentials, network connections or DDL execution are performed.
"""
import argparse
from pathlib import Path
import re
from build_schema import ROOT, DB, tables, columns, parts, EXTRAS, enum_checks


def expected(historical=False):
    if historical:
        return tables((DB/'tests/fixtures/canonical-prd22-34-schema.sql').read_text(encoding='utf-8'))
    spec = (ROOT / 'docs/specs/06-mysql-ddl-and-migrations.md').read_text(encoding='utf-8')
    desired = tables(spec.split('## SQL-007 ')[1].split('## SQL-008 ')[0] + spec.split('## SQL-010 ')[1])
    return desired


def type_of(definition):
    return re.match(r'`?\w+`?\s+(\w+(?:\([0-9,]+\))?)', definition).group(1).upper()


def validate(sql=None):
    check_entrypoints = sql is None
    sql = sql or (DB / 'init/00-schema.sql').read_text(encoding='utf-8-sig')
    actual, desired = tables(sql), expected()
    assert set(actual) == set(desired), f'Table set mismatch: {set(actual)^set(desired)}'
    assert len(re.findall(r'\bCREATE TABLE\b',sql,re.I)) == len(desired), 'Duplicate table definition'
    errors = []
    checks = enum_checks()
    for name, ddl in desired.items():
        ac, ec = columns(actual[name]), columns(ddl)
        extras = {p.split()[0]:p for p in EXTRAS.get(name,[]) if not re.match(r'^(KEY|UNIQUE|FULLTEXT)\b',p)}
        ec.update(extras)
        if set(ac) != set(ec):
            errors.append(f'{name}: undeclared/missing columns {set(ac) ^ set(ec)}')
        for column, definition in ec.items():
            if column not in ac:
                continue
            if type_of(ac[column]) != type_of(definition):
                errors.append(f'{name}.{column}: type mismatch')
            nullable = lambda value: not re.search(r'\b(?:NOT NULL|PRIMARY KEY)\b',value,re.I)
            if bool(nullable(definition)) != bool(nullable(ac[column])):
                errors.append(f'{name}.{column}: nullability mismatch')
            if 'GENERATED ALWAYS' in definition and re.sub(r'\s','',definition) != re.sub(r'\s','',ac[column]):
                errors.append(f'{name}.{column}: generated projection mismatch')
        normalize = lambda text: re.sub(r'\s|`','',text).upper()
        for part in parts(ddl) + EXTRAS.get(name,[]) + checks.get(name,[]):
            if re.match(r'^(PRIMARY|UNIQUE|KEY|FULLTEXT|CONSTRAINT|CHECK)\b',part):
                if normalize(part) not in normalize(actual[name]):
                    errors.append(f'{name}: missing key {part}')
    for file in sorted((DB/'init').glob('*.sql')) + [ROOT/'db/it_ticket_system_init_v2.sql']:
        content = re.sub(r'--[^\n]*','',file.read_text(encoding='utf-8-sig'))
        if re.search(r'\b(?:TRUNCATE|DROP|DELETE)\b',content,re.I):
            errors.append(f'{file.name}: destructive SQL in initialization')
        for db in re.findall(r'\bUSE\s+([\w`]+)',content,re.I):
            if db.strip('`') != 'it_ticket_system':
                errors.append(f'{file.name}: wrong database {db}')
        if re.search(r'INSERT\s+INTO\s+`?\w+`?\s+VALUES',content,re.I):
            errors.append(f'{file.name}: INSERT without explicit columns')
    if check_entrypoints:
        root_sql = (ROOT/'db/it_ticket_system_init_v2.sql').read_text(encoding='utf-8')
        if tables(root_sql) != actual:
            errors.append('Root SQL and runtime DDL differ; regenerate both entrypoints')
        if len(re.findall(r'\bCREATE TABLE\b',root_sql,re.I)) != len(desired):
            errors.append('Root SQL contains duplicate or missing table definitions')
        for seed in ('10-seed.sql','11-knowledge-seed.sql'):
            if (DB/'init'/seed).read_text(encoding='utf-8-sig').strip() not in root_sql:
                errors.append(f'Root SQL is missing current {seed}')
    assert not errors, '\n'.join(errors)
    return actual


def metadata_sql(historical=False):
    """Zero rows means expected canonical columns/indexes are present."""
    checks = []
    for table, ddl in expected(historical).items():
        for column, definition in columns(ddl).items():
            typ = type_of(definition).lower()
            condition = f"table_schema=DATABASE() AND table_name='{table}' AND column_name='{column}' AND LOWER(column_type)='{typ}'"
            condition += " AND is_nullable='" + ('NO' if 'NOT NULL' in definition or 'PRIMARY KEY' in definition else 'YES') + "'"
            checks.append(f"SELECT '{table}.{column}' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE {condition})")
        # Check index columns and uniqueness semantically, independent of naming.
        for part in parts(ddl):
            if not re.match(r'^(PRIMARY|UNIQUE|KEY)\b',part):
                continue
            match = re.search(r'\(([^)]+)\)',part)
            if not match:
                continue
            names = re.sub(r'\s|`','',match.group(1))
            unique = ' AND non_unique=0' if part.startswith(('PRIMARY','UNIQUE')) else ''
            checks.append(f"SELECT '{table}:index({names})' AS contract_violation WHERE NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='{table}'{unique} GROUP BY index_name HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')='{names}')")
    return "-- Read-only metadata gate. Select the intended test/target database explicitly.\n" + '\nUNION ALL\n'.join(checks) + ';\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit-sql',type=Path)
    args = parser.parse_args()
    result = validate()
    if args.emit_sql:
        args.emit_sql.write_text(metadata_sql(),encoding='utf-8')
    print(f'PASS: {len(result)} full-contract tables; columns/types/nullability/keys/checks; matching root/runtime initialization')
