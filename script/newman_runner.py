"""
NewmanRunner — Python 封装 Newman CLI。
管理 FastAPI 服务生命周期 + 执行 Postman Collection + 解析结果。
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class NewmanReport:
    """Newman 执行结果的结构化报告。"""

    total: int = 0
    failed: int = 0
    assertions_total: int = 0
    assertions_failed: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def passed(self) -> int:
        return self.total - self.failed

    @property
    def ok(self) -> bool:
        return self.total > 0 and self.failed == 0 and self.assertions_failed == 0

    @property
    def summary(self) -> str:
        if self.total == 0:
            return "No requests executed"
        return (
            f"{self.passed}/{self.total} requests passed, "
            f"{self.assertions_total - self.assertions_failed}/{self.assertions_total} assertions passed "
            f"({self.duration_ms / 1000:.1f}s)"
        )

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "failed": self.failed,
            "assertions_total": self.assertions_total,
            "assertions_failed": self.assertions_failed,
            "failures": self.failures,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
        }


class NewmanRunner:
    """封装 Newman CLI 调用，管理 FastAPI 服务生命周期。

    Usage:
        runner = NewmanRunner(
            collection_path="postman/GeoTrave-API-Tests.json",
            env_path="postman/GeoTrave-Local.postman_environment.json",
        )
        report = await runner.execute()
    """

    def __init__(
        self,
        collection_path: str,
        env_path: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        newman_bin: str = "npx newman",
        project_root: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.collection_path = Path(collection_path).resolve()
        self.env_path = Path(env_path).resolve() if env_path else None
        self.env_vars = env_vars or {}
        self.newman_cmd = newman_bin.split()
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self.output_dir = Path(output_dir).resolve() if output_dir else (self.project_root / "postman" / "output")
        self._server_process: Optional[subprocess.Popen] = None

    # ------------------------------------------------------------------
    # 顶层入口 — 一键执行完整流程
    # ------------------------------------------------------------------

    async def execute(
        self,
        start_server: bool = True,
        host: str = "127.0.0.1",
        port: int = 8000,
        server_timeout: int = 60,
    ) -> NewmanReport:
        """执行完整测试流程：启动服务 → 运行集合 → 停止服务 → 返回报告。"""
        overall_start = time.monotonic()

        if start_server:
            await self._start_server(host, port, server_timeout)

        try:
            collection_start = time.monotonic()
            raw = self._run_collection()
            collection_ms = int((time.monotonic() - collection_start) * 1000)
        finally:
            if start_server:
                await self._stop_server()

        report = self._parse_results(raw)
        report.duration_ms = int((time.monotonic() - overall_start) * 1000)

        run_log = self._build_run_log(raw, report)
        log_path = self._write_run_log(run_log)
        if log_path:
            print(f"[NewmanRunner] Run log written to: {log_path}")

        return report

    # ------------------------------------------------------------------
    # 服务生命周期
    # ------------------------------------------------------------------

    async def _start_server(self, host: str, port: int, timeout: int):
        """后台启动 uvicorn 并轮询等待就绪。"""
        self._server_process = subprocess.Popen(
            [sys.executable, "-m", "src.main"],
            cwd=str(self.project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        base_url = f"http://{host}:{port}"
        ready = await self._wait_for_server(f"{base_url}/docs", timeout)
        if not ready:
            self._server_process.terminate()
            self._server_process.wait()
            self._server_process = None
            raise RuntimeError(f"Server failed to start within {timeout}s")

        print(f"[NewmanRunner] Server ready on {base_url}")

    async def _stop_server(self, graceful_timeout: int = 5):
        """停止 uvicorn 进程。"""
        if self._server_process is None:
            return

        self._server_process.terminate()
        try:
            self._server_process.wait(timeout=graceful_timeout)
        except subprocess.TimeoutExpired:
            self._server_process.kill()
            self._server_process.wait()

        self._server_process = None
        print("[NewmanRunner] Server stopped")

    async def _wait_for_server(self, url: str, timeout: int = 60) -> bool:
        """轮询 HTTP 端点直到返回 200 或超时。"""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                resp = await asyncio.to_thread(urllib.request.urlopen, url, timeout=2)
                if resp.status == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    # Newman 执行
    # ------------------------------------------------------------------

    def _run_collection(self) -> dict:
        """执行 newman run，返回解析后的 JSON 结果。"""
        fd, reporter_output = tempfile.mkstemp(suffix=".json", prefix="newman-")
        os.close(fd)

        args = [
            *self.newman_cmd,
            "run",
            str(self.collection_path),
            "--reporters",
            "cli,json",
            "--reporter-json-export",
            reporter_output,
        ]

        if self.env_path and self.env_path.exists():
            args.extend(["-e", str(self.env_path)])

        for key, value in self.env_vars.items():
            args.extend(["--env-var", f"{key}={value}"])

        # Windows 上 npx 是 .cmd 脚本，需要 shell=True 才能执行
        use_shell = sys.platform == "win32"
        cmd_str = " ".join(args) if use_shell else args

        print(f"[NewmanRunner] Running: {' '.join(args)}")
        subprocess.run(cmd_str, cwd=str(self.project_root), shell=use_shell)

        raw = {}
        if os.path.exists(reporter_output):
            try:
                with open(reporter_output, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[NewmanRunner] Failed to parse Newman JSON output: {exc}")

        try:
            os.unlink(reporter_output)
        except OSError:
            pass

        return raw

    # ------------------------------------------------------------------
    # 结果解析
    # ------------------------------------------------------------------

    def _parse_results(self, raw: dict) -> NewmanReport:
        """解析 Newman JSON 输出为 NewmanReport。"""
        run = raw.get("run", {})
        stats = run.get("stats", {})

        report = NewmanReport(
            total=stats.get("requests", {}).get("total", 0),
            failed=stats.get("requests", {}).get("failed", 0),
            assertions_total=stats.get("assertions", {}).get("total", 0),
            assertions_failed=stats.get("assertions", {}).get("failed", 0),
        )

        for execution in run.get("executions", []):
            for assertion in execution.get("assertions", []):
                if assertion.get("error"):
                    report.failures.append(
                        {
                            "name": execution.get("item", {}).get("name", "Unknown"),
                            "assertion": assertion.get("assertion", ""),
                            "error": assertion["error"].get("message", "Unknown error"),
                        }
                    )

        return report

    # ------------------------------------------------------------------
    # 结构化日志
    # ------------------------------------------------------------------

    def _build_run_log(self, raw: dict, report: NewmanReport) -> dict:
        """组装结构化运行日志。"""
        now = datetime.now(timezone.utc)
        run_id = now.strftime("run-%Y-%m-%dT%H-%M-%S")

        return {
            "run_id": run_id,
            "timestamp": now.isoformat(),
            "base_url": self.env_vars.get("base_url", "unknown"),
            "collection": self.collection_path.name,
            "summary": {
                "requests": {
                    "total": report.total,
                    "passed": report.passed,
                    "failed": report.failed,
                },
                "assertions": {
                    "total": report.assertions_total,
                    "passed": report.assertions_total - report.assertions_failed,
                    "failed": report.assertions_failed,
                },
                "duration_ms": report.duration_ms,
            },
            "requests": self._extract_request_details(raw),
            "failures": report.failures,
        }

    def _extract_request_details(self, raw: dict) -> list:
        """从 Newman 原始输出中提取每个请求的详情。"""
        details = []
        for execution in raw.get("run", {}).get("executions", []):
            item = execution.get("item", {})
            response = execution.get("response", {})
            assertions = execution.get("assertions", [])

            assertion_results = []
            passed = 0
            failed = 0
            for a in assertions:
                ok = a.get("error") is None
                assertion_results.append({
                    "name": a.get("assertion", ""),
                    "passed": ok,
                    "error": a["error"].get("message", "") if a.get("error") else None,
                })
                if ok:
                    passed += 1
                else:
                    failed += 1

            details.append({
                "name": item.get("name", "Unknown"),
                "status": response.get("code", 0),
                "response_time_ms": response.get("responseTime", 0),
                "response_size_bytes": response.get("responseSize", 0),
                "assertions_passed": passed,
                "assertions_failed": failed,
                "assertions": assertion_results,
            })

        return details

    def _write_run_log(self, run_log: dict) -> Optional[Path]:
        """将运行日志写入 output_dir。"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[NewmanRunner] Failed to create output dir {self.output_dir}: {exc}")
            return None

        filename = f"{run_log['run_id']}.json"
        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(run_log, f, indent=2, ensure_ascii=False)
            return filepath
        except OSError as exc:
            print(f"[NewmanRunner] Failed to write run log: {exc}")
            return None
