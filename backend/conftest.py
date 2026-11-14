"""Make the backend package importable no matter which directory pytest is run from."""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Keep the test database out of the real cache and start from a clean file.
TEST_DB = Path(tempfile.gettempdir()) / "rootshift_test.sqlite3"
os.environ.setdefault("ROOTSHIFT_DB", str(TEST_DB))
if TEST_DB.exists():
    try:
        TEST_DB.unlink()
    except OSError:
        pass
