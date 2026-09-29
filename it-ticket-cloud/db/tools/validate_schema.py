"""Offline SQL contract gate; optionally emit read-only MySQL metadata checks.

python db/tools/validate_schema.py [--emit-sql path.sql]
No database credentials, network connections or DDL execution are performed.
"""
import argparse
from pathlib import Path
import re
from build_schema import ROOT, DB, tables, columns, parts, EXTRAS, IMPLEMENTED


def expected():
    spec = (ROOT / 'docs/specs/06-mysql-ddl-and-migrations.md').read_text(encoding='utf-8')
    desired = tables(spec.split('## SQL-007 ')[1].split('## SQL-008 ')[0] + spec.split('## SQL-010 ')[1])
    desired = {name:ddl for name,ddl in desired.items() if name in IMPLEMENTED}
    old = tables((DB/'tests/fixtures/main-388f51d-schema.sql').read_text(encoding='utf-8'))
    desired.update({name:ddl for name,ddl in old.items() if name not in IMPLEMENTED and name != 'user'})
    return desired


def type_of(definition):
    return re.match(r'`?\w+`?\s+(\w+(?:\([0-9,]+\))?)', definition).group(1).upper()


def validate(sql=None):
    sql = sql or (DB / 'init/00-schema.sql').read_text(encoding='utf-8-sig')
    actual, desired = tables(sql), expected()
    assert set(actual) == set(desired), f'Table set mismatch: {set(actual)^set(desired)}'
    assert len(re.findall(r'\bCREATE TABLE\b',sql,re.I)) == len(desired), 'Duplicate table definition'
    errors = []
    for name, ddl in desired.items():
        if name not in IMPLEMENTED and actual[name] != ddl:
            errors.append(f'{name}: deferred schema must stay byte-for-byte identical to main')
        ac, ec = columns(actual[name]), columns(ddl)
        extras = {p.split()[0] for p in EXTRAS.get(name,[]) if not re.match(r'^(KEY|UNIQUE|FULLTEXT)\b',p)}
        if set(ac) != set(ec) | extras:
            errors.append(f'{name}: undeclared/missing columns {set(ac) ^ (set(ec)|extras)}')
        for column, definition in ec.items():
            if column not in ac:
                continue
            if type_of(ac[column]) != type_of(definition):
                errors.append(f'{name}.{column}: type mismatch')
            if 'NOT NULL' in definition and 'NOT NULL' not in ac[column]:
                errors.append(f'{name}.{column}: lost NOT NULL')
        normalize = lambda text: re.sub(r'\s|`','',text).upper()
        for part in parts(ddl):
            if re.match(r'^(PRIMARY|UNIQUE|KEY)\b',part):
                if normalize(part) not in normalize(actual[name]):
                    errors.append(f'{name}: missing key {part}')
    for file in sorted((DB/'init').glob('*.sql')):
        content = re.sub(r'--[^\n]*','',file.read_text(encoding='utf-8-sig'))
        if re.search(r'\b(?:TRUNCATE|DROP|DELETE)\b',content,re.I):
            errors.append(f'{file.name}: destructive SQL in initialization')
        for db in re.findall(r'\bUSE\s+([\w`]+)',content,re.I):
            if db.strip('`') != 'it_ticket_system':
                errors.append(f'{file.name}: wrong database {db}')
        if re.search(r'INSERT\s+INTO\s+`?\w+`?\s+VALUES',content,re.I):
            errors.append(f'{file.name}: INSERT without explicit columns')
    assert not errors, '\n'.join(errors)
    return actual


def metadata_sql():
    """Zero rows means expected canonical columns/indexes are present."""
    checks = []
    for table, ddl in expected().items():
        for column, definition in columns(ddl).items():
            typ = type_of(definition).lower()
            condition = f"table_schema=DATABASE() AND table_name='{table}' AND column_name='{column}' AND LOWER(column_type)='{typ}'"
            if 'NOT NULL' in definition or 'PRIMARY KEY' in definition:
                condition += " AND is_nullable='NO'"
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
    print(f'PASS: {len(result)} tables ({len(IMPLEMENTED)} implemented canonical + {len(result)-len(IMPLEMENTED)} unchanged main); scoped columns/types/keys; safe single-database initialization')
