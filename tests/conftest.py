import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

for sub in ["core", "ml", "security", "api", "privacy", "deception", "retraining"]:
    sub_path = os.path.join(_PROJECT_ROOT, sub)
    if os.path.exists(sub_path) and sub_path not in sys.path:
        sys.path.insert(0, sub_path)
