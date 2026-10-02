from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from my_ai.audit_tools import run_audit

def main() -> int:
    report=run_audit(ROOT)
    out=ROOT/"audit-report.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"silent_failure_count":len(report["silent_failures"]),"module_count":len(report["architecture"])},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
