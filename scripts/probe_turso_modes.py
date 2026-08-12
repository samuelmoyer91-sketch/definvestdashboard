#!/usr/bin/env python3
"""Try each libsql connection mode and report which ones work.

On 2026-08-12 both pipelines failed with

    Hrana: api error: status=502 Bad Gateway, body={"error":"upstream forward failed"}

while `turso db shell` queried the same database fine. Queries and embedded
replica sync use different Turso endpoints, so this establishes which of them
is actually broken — and whether connecting directly is a viable route around
it.

Read-only. Run via:
    gh workflow run migrate.yml -f script=probe_turso_modes.py
"""
import os
import sys
import traceback

URL = (os.environ.get('TURSO_DATABASE_URL') or '').strip()
TOKEN = (os.environ.get('TURSO_AUTH_TOKEN') or '').strip()

if not URL or not TOKEN:
    print("Turso env vars not set")
    sys.exit(1)

import libsql

print(f"libsql module: {getattr(libsql, '__version__', 'unknown')}")
print(f"url host     : {URL.split('//')[-1][:45]}")
print()


def attempt(label, fn):
    print(f"--- {label} ---")
    try:
        conn = fn()
        n = conn.execute("SELECT COUNT(*) FROM master_list").fetchone()[0]
        print(f"    OK — master_list has {n} rows\n")
        return True
    except BaseException as e:
        print(f"    FAILED: {type(e).__name__}: {e}")
        tb = traceback.format_exc().strip().splitlines()
        print(f"    {tb[-1]}\n")
        return False


results = {}

# 1. Remote only — no local file, no sync. What `turso db shell` effectively does.
results['remote'] = attempt(
    "remote only: libsql.connect(url, auth_token=...)",
    lambda: libsql.connect(URL, auth_token=TOKEN))

# 2. Embedded replica — what the app and pipeline use today.
results['replica'] = attempt(
    "embedded replica: libsql.connect(file, sync_url=..., auth_token=...)",
    lambda: libsql.connect('probe_replica.db', sync_url=URL, auth_token=TOKEN))

# 3. Embedded replica WITHOUT the initial sync, to separate "connect" from "sync".
def _no_sync():
    c = libsql.connect('probe_replica2.db', sync_url=URL, auth_token=TOKEN)
    return c
results['replica_nosync'] = attempt(
    "embedded replica, no explicit .sync() call", _no_sync)

print("=" * 60)
for k, v in results.items():
    print(f"  {k:16s} {'WORKS' if v else 'fails'}")

if results.get('remote') and not results.get('replica'):
    print("\n=> Sync is broken, queries are fine. Connecting directly routes "
          "around it, and is the right shape for one-shot Actions runs anyway.")
elif all(results.values()):
    print("\n=> Everything works now; the outage has cleared on its own.")
elif not any(results.values()):
    print("\n=> Nothing connects — the failure is not specific to sync.")
sys.exit(0)
