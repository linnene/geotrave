"""
CLI 入口 — 一键运行 Newman API 集成测试。

Usage:
    uv run python scripts/run_api_tests.py                          # 自动启停服务
    uv run python scripts/run_api_tests.py --no-server              # 服务已运行
    uv run python scripts/run_api_tests.py --base-url http://localhost:8000
    uv run python scripts/run_api_tests.py --json --output report.json
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from newman_runner import NewmanReport, NewmanRunner

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COLLECTION = PROJECT_ROOT / "postman" / "GeoTrave-API-Tests.json"
ENV_PATH = PROJECT_ROOT / "postman" / "GeoTrave-Local.postman_environment.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GeoTrave API Integration Tests (Newman)")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start/stop server; assume it's already running",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for auto-started server (default: 8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Server start timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report to stdout (no human-readable output)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for structured run logs (default: postman/output)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Collection file path (default: postman/GeoTrave-API-Tests.json). "
             "Use 'TEST' for GeoTrave-TEST.json.",
    )
    return parser.parse_args()


def print_report(report: NewmanReport):
    """打印人类可读的测试报告。"""
    print()
    print("=" * 60)
    print("  GeoTrave API Integration Test Report")
    print("=" * 60)
    print(f"  Requests:   {report.passed}/{report.total} passed")
    print(f"  Assertions: {report.assertions_total - report.assertions_failed}/{report.assertions_total} passed")
    print(f"  Duration:   {report.duration_ms / 1000:.1f}s")
    print("-" * 60)

    if report.ok:
        print("  Status:     ALL PASSED")
    else:
        print(f"  Status:     {report.failed} REQUESTS FAILED, {report.assertions_failed} ASSERTIONS FAILED")
        print("-" * 60)
        for f in report.failures:
            print(f"  [{f['name']}]")
            print(f"    Assertion: {f['assertion']}")
            print(f"    Error:     {f['error']}")

    print("=" * 60)
    print()


async def main():
    args = parse_args()

    # Resolve collection path
    if args.collection:
        if args.collection.upper() == "TEST":
            collection_path = PROJECT_ROOT / "postman" / "GeoTrave-TEST.json"
        else:
            collection_path = Path(args.collection)
    else:
        collection_path = DEFAULT_COLLECTION

    if not collection_path.exists():
        print(f"ERROR: Collection not found: {collection_path}", file=sys.stderr)
        sys.exit(2)

    # 从 base_url 解析 host/port
    base = args.base_url.rstrip("/")
    host = "127.0.0.1"
    port = 8000
    if "://" in base:
        host_port = base.split("://")[1]
        if ":" in host_port:
            host, port_str = host_port.split(":")
            port = int(port_str)
        else:
            host = host_port

    # 为多对话测试生成唯一 session_ids（每次运行都不同）
    import random, string
    ts = str(int(time.time() * 1000))
    def _rand_suffix():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    env_vars = {"base_url": base}
    if collection_path.name == "GeoTrave-TEST.json":
        env_vars.update({
            "chat1_session": f"test-chat1-{ts}-{_rand_suffix()}",
            "chat2_session": f"test-chat2-{ts}-{_rand_suffix()}",
            "chat3_session": f"test-chat3-{ts}-{_rand_suffix()}",
            "safety_session": f"test-safety-{ts}-{_rand_suffix()}",
            "pii_session": f"test-pii-{ts}-{_rand_suffix()}",
        })
        print(f"[Session IDs] chat1={env_vars['chat1_session']}")

    runner = NewmanRunner(
        collection_path=str(collection_path),
        env_path=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_vars=env_vars,
        project_root=str(PROJECT_ROOT),
        output_dir=args.output_dir,
    )

    report = await runner.execute(
        start_server=not args.no_server,
        host=host,
        port=port,
        server_timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_report(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Report written to: {args.output}")

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
