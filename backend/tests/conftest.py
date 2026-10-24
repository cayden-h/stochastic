"""Tests run on the memory store, whatever the repo-root .env says. `test_postgres_store.py` opts in to Tiger Cloud."""
import os

os.environ["STORE"] = "memory"
