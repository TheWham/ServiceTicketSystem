# -*- coding: utf-8 -*-
"""
清理"响应超时转派"雪崩垃圾数据(与 cleanup_routing_timeout_spam.sql 等效,Python 便于分批/观察进度)
用法: 设置 DB_HOST/DB_USER/DB_PASSWORD/DB_NAME 后运行
      python cleanup_routing_timeout_spam.py

前置:
  1. 停掉所有 ticket-service 实例(旧代码每分钟还会再造垃圾);
  2. 确认 information_schema.innodb_trx 中没有大事务在跑/回滚(否则等它结束再跑)。

步骤(本脚本按顺序执行):
  1. CREATE ... LIKE 建新表;
  2. INSERT SELECT 只拷干净行(ticket_transition 去掉 TICKET_TIMEOUT_TRANSFER;
     assignment 去掉 open 垃圾与 TIMEOUT 关闭垃圾);
  3. RENAME 原子换名;旧表改名为 *_old 保留待人工核对后 DROP。
"""
import os
import sys
import time

import pymysql

password = os.environ.get("DB_PASSWORD")
if not password:
    print("[中止] 缺少必填环境变量 DB_PASSWORD", file=sys.stderr)
    sys.exit(2)

conn = pymysql.connect(
    host=os.environ.get("DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "it_ticket"),
    password=password,
    db=os.environ.get("DB_NAME", "it_ticket_system"),
    connect_timeout=10,
    read_timeout=None,
    charset="utf8mb4")
cur = conn.cursor()

def run(sql):
    print(f"--> {sql[:100]}")
    cur.execute(sql)
    print("    affected:", cur.rowcount, flush=True)

# 0) 安全检查:有大事务就不动手
cur.execute("SELECT COUNT(*), COALESCE(MAX(trx_rows_modified),0) FROM information_schema.innodb_trx")
cnt, maxmod = cur.fetchone()
if maxmod > 10000:
    print(f"[中止] 仍有事务修改了 {maxmod} 行(可能在回滚),等它结束后再跑。innodb_trx 行数: {cnt}")
    sys.exit(1)

t0 = time.time()
run("DROP TABLE IF EXISTS ticket_transition_new")
run("CREATE TABLE ticket_transition_new LIKE ticket_transition")
run("INSERT INTO ticket_transition_new SELECT * FROM ticket_transition WHERE event <> 'TICKET_TIMEOUT_TRANSFER'")

run("DROP TABLE IF EXISTS assignment_new")
run("CREATE TABLE assignment_new LIKE assignment")
run("""INSERT INTO assignment_new SELECT * FROM assignment
       WHERE biz_type <> 'TICKET' OR (end_reason IS NOT NULL AND end_reason <> 'TIMEOUT')""")

cur.execute("SELECT (SELECT COUNT(*) FROM ticket_transition), (SELECT COUNT(*) FROM ticket_transition_new), "
            "(SELECT COUNT(*) FROM assignment), (SELECT COUNT(*) FROM assignment_new)")
old_t, new_t, old_a, new_a = cur.fetchone()
print(f"ticket_transition: {old_t} -> {new_t}; assignment: {old_a} -> {new_a}")

run("RENAME TABLE ticket_transition TO ticket_transition_old, ticket_transition_new TO ticket_transition")
run("RENAME TABLE assignment TO assignment_old, assignment_new TO assignment")
print(f"完成,耗时 {time.time()-t0:.0f}s。核对无误后执行: DROP TABLE ticket_transition_old; DROP TABLE assignment_old;")
