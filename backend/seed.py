from __future__ import annotations

import argparse
import json
from pathlib import Path

from .database import Database
from .service import ConflictError, QualityOpsService


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="初始化 Agent QualityOps 数据库和评测用例")
    parser.add_argument("--db", default=str(root / "backend" / "qualityops.db"), help="SQLite 数据库路径")
    parser.add_argument("--file", default=str(root / "data" / "eval_cases.json"), help="评测用例 JSON 路径")
    parser.add_argument("--skip-cases", action="store_true", help="只初始化数据库和种子 Prompt 版本")
    args = parser.parse_args()

    database = Database(args.db)
    database.initialize()
    service = QualityOpsService(database)
    seeded_versions = service.seed_versions()
    imported = 0
    if not args.skip_cases:
        path = Path(args.file)
        if not path.exists():
            parser.error(f"评测用例文件不存在：{path}")
        try:
            imported = service.import_cases_file(path)["imported"]
        except ConflictError:
            # 幂等执行：已有数据不覆盖、不静默改写。
            imported = 0
    print(json.dumps({"database": args.db, "seeded_versions": seeded_versions, "imported_cases": imported}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
