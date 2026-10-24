"""Time the Tiger read side against the plain-SQL way, read-only, on the live schema.

Server execution time from EXPLAIN ANALYZE, median of 25 runs, so the network is not in the figure.

    set -a; . .env; set +a
    backend/.venv/bin/python scripts/tiger_bench.py
"""
import os, statistics, time, psycopg
url = os.environ["DATABASE_URL"]  # read-only session below
Q = {
 "bm25 top 10 for 'lease'": "SELECT kind, id FROM record ORDER BY search_text <@> 'lease' LIMIT 10",
 "ILIKE scan, unranked, all matches": "SELECT kind, id FROM record WHERE search_text ILIKE '%lease%'",
 "audit_activity (continuous aggregate)": "SELECT * FROM audit_activity",
 "same rollup from raw audit_log": "SELECT time_bucket('1 minute', at) b, actor, result, count(*) FROM audit_log GROUP BY 1,2,3",
}
with psycopg.connect(url, options=f"-c search_path={os.getenv('DB_SCHEMA', 'stochastic')},public -c default_transaction_read_only=on") as c:
    cur = c.cursor()
    for t in ("record", "audit_log"):
        cur.execute(f"SELECT count(*) FROM {t}"); print(t, "rows", cur.fetchone()[0])
    for name, sql in Q.items():
        try:
            cur.execute(sql); cur.fetchall()
            ms = []
            for _ in range(25):
                t0 = time.perf_counter(); cur.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + sql); plan = cur.fetchone()[0][0]
                ms.append(plan["Execution Time"])
            print(f"{name}: server execution median {statistics.median(ms):.3f} ms, p90 {sorted(ms)[int(0.9*len(ms))-1]:.3f} ms; top node {plan['Plan']['Node Type']}")
        except Exception as e:
            c.rollback(); print(name, "ERROR", type(e).__name__, str(e)[:150])
