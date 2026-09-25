#!/usr/bin/env python3
"""Create the dup_dismissals table (2026-09-25) and confirm it exists.

create_all only adds missing tables, never alters existing ones, so this is
safe to re-run. Run from Actions, not app startup: schema changes made from
the Railway app have failed silently before (see memory: turso-schema-migrations).

    gh workflow run migrate.yml -f script=migrate_dup_dismissals.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect

from src.database.models import get_engine, Base, DupDismissal

engine = get_engine()
Base.metadata.create_all(engine, tables=[DupDismissal.__table__])
present = 'dup_dismissals' in inspect(engine).get_table_names()
print(f"dup_dismissals table present: {present}")
sys.exit(0 if present else 1)
