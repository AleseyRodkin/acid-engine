#!/usr/bin/env python3
"""
Запуск самоописания AcidEngine.
"""
import json

from acid_engine.self_describe import build_self_contract


def main():
    iface = build_self_contract()
    d = iface.to_canonical_dict()
    print(json.dumps(d, indent=2, ensure_ascii=False))
    print(f"\nInterface contract hash: {iface.content_hash}")


if __name__ == "__main__":
    main()