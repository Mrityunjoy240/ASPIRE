#!/usr/bin/env python3
# scripts/generate_openapi.py
# OpenAPI Contract Generator (DM-API01)
# Imports app.main:app and dumps clean JSON to contracts/openapi.json

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def generate_openapi() -> dict:
    """Generate OpenAPI schema from FastAPI app."""
    return app.openapi()


def write_contract(schema: dict, output_path: Path) -> None:
    """Write OpenAPI contract to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"OpenAPI contract written to {output_path}")


def main() -> int:
    try:
        schema = generate_openapi()
        output_path = Path(__file__).parent.parent / "contracts" / "openapi.json"
        write_contract(schema, output_path)
        print(f"Generated OpenAPI spec with {len(schema.get('paths', {}))} paths")
        return 0
    except Exception as e:
        print(f"Error generating OpenAPI contract: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())