#!/usr/bin/env python3
"""
dev_setup.py — Creates a .env file from .env.example if one doesn't exist.
Run: python scripts/dev_setup.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent / "backend"
example = ROOT / ".env.example"
target = ROOT / ".env"

if target.exists():
    print(f"[OK] .env already exists at {target}")
else:
    shutil.copy(example, target)
    print(f"[CREATED] {target}")
    print("[!] Edit backend/.env and set a real SECRET_KEY before production use.")

print("\nTo start the dev server:")
print("  cd backend && uvicorn app.main:app --reload")
