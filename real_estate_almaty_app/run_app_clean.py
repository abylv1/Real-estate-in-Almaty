# -*- coding: utf-8 -*-
"""
Clean launcher for the Almaty real estate app.

It redirects native QtWebEngine/Chromium GPU messages from terminal
to logs/qtwebengine_stderr.log and starts main.py.

Run:
python run_app_clean.py
"""

import os
import sys
from pathlib import Path
import traceback

# Must be set before importing main.py / PySide6 / QWebEngine
os.environ["QT_OPENGL"] = "software"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu "
    "--disable-gpu-compositing "
    "--disable-logging "
    "--log-level=3 "
    "--ignore-certificate-errors "
    "--no-sandbox "
    "--disable-features=VizDisplayCompositor"
)
os.environ["QT_LOGGING_RULES"] = (
    "qt.webenginecontext.debug=false;"
    "qt.webenginecontext.warning=false;"
    "qt.qpa.*=false"
)

Path("logs").mkdir(exist_ok=True)
log_path = Path("logs") / "qtwebengine_stderr.log"

# Redirect low-level stderr (file descriptor 2), where Chromium writes GPU messages.
try:
    _stderr_file = open(log_path, "ab", buffering=0)
    os.dup2(_stderr_file.fileno(), 2)
except Exception:
    _stderr_file = None

try:
    import main
    main.main()
except SystemExit:
    raise
except Exception:
    # Print real Python errors to stdout so user still sees them.
    print("\n[PYTHON ERROR]")
    traceback.print_exc(file=sys.stdout)
    print(f"\nQtWebEngine native logs are saved here: {log_path}")
    input("Press Enter to close...")
