from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_project() -> Path:
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from app.env_loader import load_app_env

    load_app_env(force=True, project_root=root)
    return root


PROJECT_ROOT = bootstrap_project()
