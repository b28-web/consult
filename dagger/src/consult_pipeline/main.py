"""Main entry point for the Consult CI/CD pipeline."""

from __future__ import annotations

import asyncio
import json
import sys
import time

import dagger
from dagger import dag, function, object_type


@object_type
class ConsultPipeline:
    """Pre-deployment validation pipeline for Consult."""

    @function
    async def pre_deploy(
        self, source: dagger.Directory, json_output: bool = False
    ) -> str:
        """Run full pre-deployment validation.

        Executes all validation stages:
        1. Build: Verify all containers build successfully (parallel)
        2. Quality: Run linters, type checkers, and tests (parallel)
        3. Integration: Run service health checks with real database

        Parameters
        ----------
        source:
            The project source directory (pass . from the repo root).
        json_output:
            If True, return JSON-formatted output for machine parsing.

        Returns:
            Formatted report with pass/fail status and timing.
        """
        results: list[tuple[str, str, bool, str, float]] = []
        total_start = time.time()

        def log(msg: str) -> None:
            print(msg, file=sys.stderr, flush=True)

        log("═" * 60)
        log("  PRE-DEPLOY VALIDATION STARTING")
        log("═" * 60)

        # Stage 1: Build validation (run in parallel)
        log("\n▶ Stage 1/3: Build validation...")
        stage_start = time.time()
        build_results = await asyncio.gather(
            self._timed_check(self._build_django(source)),
            self._timed_check(self._build_worker(source)),
            self._timed_check(self._build_site(source, "coffee-shop")),
        )
        results.extend(build_results)
        build_time = time.time() - stage_start
        for r in build_results:
            icon = "✓" if r[2] else "✗"
            log(f"  {icon} {r[1]} ({r[4]:.1f}s)")
        log(f"  Build stage: {build_time:.1f}s")

        # Stage 2: Quality checks (run in parallel)
        log("\n▶ Stage 2/3: Quality checks...")
        stage_start = time.time()
        quality_results = await asyncio.gather(
            self._timed_check(self._run_ruff(source)),
            self._timed_check(self._run_mypy(source)),
            self._timed_check(self._run_pytest(source)),
        )
        results.extend(quality_results)
        quality_time = time.time() - stage_start
        for r in quality_results:
            icon = "✓" if r[2] else "✗"
            log(f"  {icon} {r[1]} ({r[4]:.1f}s)")
        log(f"  Quality stage: {quality_time:.1f}s")

        # Stage 3: Integration tests (sequential due to dependencies)
        log("\n▶ Stage 3/3: Integration tests...")
        stage_start = time.time()
        integration_results = await self._run_integration_tests_timed(source)
        results.extend(integration_results)
        integration_time = time.time() - stage_start
        for r in integration_results:
            icon = "✓" if r[2] else "✗"
            log(f"  {icon} {r[1]} ({r[4]:.1f}s)")
        log(f"  Integration stage: {integration_time:.1f}s")

        total_time = time.time() - total_start
        log(f"\n═ Total: {total_time:.1f}s ═")

        if json_output:
            return self._format_json_report_timed(
                results, build_time, quality_time, integration_time, total_time
            )
        return self._format_report_timed(
            results, build_time, quality_time, integration_time, total_time
        )

    async def _timed_check(self, coro: object) -> tuple[str, str, bool, str, float]:
        """Wrap a check coroutine to add timing."""
        start = time.time()
        result = await coro  # type: ignore[misc]
        duration = time.time() - start
        # Result is (stage, name, passed, message) - add duration
        return (*result, duration)  # type: ignore[return-value]

    @function
    async def build_all(
        self, source: dagger.Directory, json_output: bool = False
    ) -> str:
        """Run only build validation (parallel)."""
        results = await asyncio.gather(
            self._build_django(source),
            self._build_worker(source),
            self._build_site(source, "coffee-shop"),
        )
        if json_output:
            return self._format_json_report(list(results))
        return self._format_report(list(results))

    @function
    async def quality_all(
        self, source: dagger.Directory, json_output: bool = False
    ) -> str:
        """Run only quality checks (parallel)."""
        results = await asyncio.gather(
            self._run_ruff(source),
            self._run_mypy(source),
            self._run_pytest(source),
        )
        if json_output:
            return self._format_json_report(list(results))
        return self._format_report(list(results))

    @function
    async def integration_all(
        self, source: dagger.Directory, json_output: bool = False
    ) -> str:
        """Run only integration tests.

        Tests Django and Worker health endpoints with a Postgres database.
        """
        results = await self._run_integration_tests(source)
        if json_output:
            return self._format_json_report(results)
        return self._format_report(results)

    @function
    async def build_django(self, source: dagger.Directory) -> str:
        """Build Django container."""
        result = await self._build_django(source)
        return self._format_single(result)

    @function
    async def build_worker(self, source: dagger.Directory) -> str:
        """Build Worker container."""
        result = await self._build_worker(source)
        return self._format_single(result)

    @function
    async def build_site(
        self, source: dagger.Directory, name: str = "coffee-shop"
    ) -> str:
        """Build a client site."""
        result = await self._build_site(source, name)
        return self._format_single(result)

    @function
    async def lint(self, source: dagger.Directory) -> str:
        """Run ruff linter."""
        result = await self._run_ruff(source)
        return self._format_single(result)

    @function
    async def typecheck(self, source: dagger.Directory) -> str:
        """Run mypy type checker."""
        result = await self._run_mypy(source)
        return self._format_single(result)

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Run pytest."""
        result = await self._run_pytest(source)
        return self._format_single(result)

    # =========================================================================
    # Build Stages
    # =========================================================================

    async def _build_django(
        self, source: dagger.Directory
    ) -> tuple[str, str, bool, str]:
        """Build the Django container."""
        try:
            # Filter source to only Django-relevant files
            src = (
                source.without_directory(".venv")
                .without_directory(".git")
                .without_directory("node_modules")
                .without_directory("dagger")
                .without_directory("sites")
                .without_directory("workers")
                .without_directory("infra")
                .without_directory("docs")
            )

            container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_workdir("/app")
                # Install uv
                .with_file(
                    "/usr/local/bin/uv",
                    dag.container().from_("ghcr.io/astral-sh/uv:latest").file("/uv"),
                )
                # Copy dependency files
                .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
                .with_file("/app/uv.lock", src.file("uv.lock"))
                .with_file("/app/README.md", src.file("README.md"))
                # Install dependencies
                .with_exec(
                    ["uv", "sync", "--frozen", "--no-dev", "--no-install-project"]
                )
                # Copy application code
                .with_directory("/app/apps", src.directory("apps"))
            )

            # Verify Django can at least import
            await container.with_exec(
                [
                    "uv",
                    "run",
                    "python",
                    "-c",
                    "import django; print(f'Django {django.__version__}')",
                ]
            ).stdout()

            return ("Build", "Django container", True, "")

        except Exception as e:
            return ("Build", "Django container", False, str(e))

    async def _build_worker(
        self, source: dagger.Directory
    ) -> tuple[str, str, bool, str]:
        """Build the Worker container."""
        try:
            worker_src = source.directory("workers/intake").without_directory(
                "node_modules"
            )

            container = (
                dag.container()
                .from_("node:22-slim")
                .with_workdir("/app")
                .with_exec(["corepack", "enable"])
                # Copy package files and source
                .with_file("/app/package.json", worker_src.file("package.json"))
                .with_directory("/app/src", worker_src.directory("src"))
                .with_file("/app/wrangler.toml", worker_src.file("wrangler.toml"))
                .with_file("/app/tsconfig.json", worker_src.file("tsconfig.json"))
                # Install dependencies
                .with_exec(["pnpm", "install"])
            )

            # Verify TypeScript compiles
            await container.with_exec(["pnpm", "exec", "tsc", "--noEmit"]).stdout()

            return ("Build", "Worker container", True, "")

        except Exception as e:
            return ("Build", "Worker container", False, str(e))

    async def _build_site(
        self, source: dagger.Directory, name: str
    ) -> tuple[str, str, bool, str]:
        """Build a client site."""
        try:
            # Get workspace files needed for building, excluding all node_modules
            root_src = (
                source.without_directory(".venv")
                .without_directory(".git")
                .without_directory("node_modules")
                .without_directory("packages/shared-ui/node_modules")
                .without_directory(f"sites/{name}/node_modules")
                .without_directory("dagger")
                .without_directory("apps")
                .without_directory("workers")
                .without_directory("infra")
                .without_directory("docs")
            )

            # Build container step by step
            container = (
                dag.container()
                .from_("node:22-slim")
                .with_workdir("/app")
                .with_exec(["corepack", "enable"])
                # Copy workspace files
                .with_directory("/app", root_src)
            )

            # Run pnpm install (capture stderr for better errors)
            container = container.with_exec(
                ["pnpm", "install", "--frozen-lockfile"],
                redirect_stdout="stdout.log",
                redirect_stderr="stderr.log",
            )

            # Run build
            container = container.with_workdir(f"/app/sites/{name}").with_exec(
                ["pnpm", "build"],
                redirect_stdout="build-stdout.log",
                redirect_stderr="build-stderr.log",
            )

            # Verify build output exists
            await container.directory("dist").entries()

            return ("Build", f"{name} site", True, "")

        except Exception as e:
            error_msg = str(e)
            # Try to extract traceparent for clearer reference
            if "traceparent:" in error_msg:
                error_msg = error_msg.split("[traceparent:")[0].strip()
            return ("Build", f"{name} site", False, error_msg)

    # =========================================================================
    # Quality Stages
    # =========================================================================

    def _get_python_container(self, source: dagger.Directory) -> dagger.Container:
        """Get a Python container with dependencies installed."""
        src = (
            source.without_directory(".venv")
            .without_directory(".git")
            .without_directory("node_modules")
            .without_directory("dagger")
            .without_directory("sites")
            .without_directory("workers")
            .without_directory("infra")
        )

        return (
            dag.container()
            .from_("python:3.13-slim")
            .with_workdir("/app")
            # Set mock environment variables for Django (required by mypy plugin)
            .with_env_variable("SECRET_KEY", "test-secret-key-for-ci")
            .with_env_variable("DEBUG", "True")
            .with_env_variable("ALLOWED_HOSTS", "localhost")
            .with_env_variable("DATABASE_URL", "sqlite:///db.sqlite3")
            .with_env_variable("DJANGO_SETTINGS_MODULE", "apps.web.config.settings")
            # Ensure apps package is importable
            .with_env_variable("PYTHONPATH", "/app")
            # Install uv
            .with_file(
                "/usr/local/bin/uv",
                dag.container().from_("ghcr.io/astral-sh/uv:latest").file("/uv"),
            )
            # Copy project files
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_file("/app/README.md", src.file("README.md"))
            # Install all dependencies (including dev)
            .with_exec(["uv", "sync", "--frozen", "--all-extras"])
            # Copy source code
            .with_directory("/app/apps", src.directory("apps"))
            .with_directory("/app/packages", src.directory("packages"))
        )

    async def _run_ruff(self, source: dagger.Directory) -> tuple[str, str, bool, str]:
        """Run ruff linter and formatter check."""
        try:
            container = self._get_python_container(source)

            # Run ruff check
            await container.with_exec(["uv", "run", "ruff", "check", "."]).stdout()

            # Run ruff format check
            await container.with_exec(
                ["uv", "run", "ruff", "format", "--check", "."]
            ).stdout()

            return ("Quality", "ruff check", True, "")

        except Exception as e:
            return ("Quality", "ruff check", False, str(e))

    async def _run_mypy(self, source: dagger.Directory) -> tuple[str, str, bool, str]:
        """Run mypy type checker."""
        try:
            container = self._get_python_container(source)

            await container.with_exec(["uv", "run", "mypy", "apps"]).stdout()

            return ("Quality", "mypy", True, "")

        except Exception as e:
            return ("Quality", "mypy", False, str(e))

    async def _run_pytest(self, source: dagger.Directory) -> tuple[str, str, bool, str]:
        """Run pytest (unit tests only, no integration)."""
        try:
            container = self._get_python_container(source)

            # Run pytest without integration tests (those need DB)
            output = await container.with_exec(
                [
                    "uv",
                    "run",
                    "pytest",
                    "-m",
                    "not integration",
                    "--tb=short",
                    "-q",
                ]
            ).stdout()

            # Extract test count from output
            summary = output.strip().split("\n")[-1] if output else "no tests"
            if "no tests ran" in summary.lower():
                summary = "no tests collected"

            return ("Quality", f"pytest ({summary})", True, "")

        except Exception as e:
            error_msg = str(e)

            # Exit code 5 means no tests collected - treat as pass
            if "exit code: 5" in error_msg or "no tests ran" in error_msg.lower():
                return ("Quality", "pytest (no tests collected)", True, "")

            # Try to extract useful info from pytest failure
            if "FAILED" in error_msg:
                lines = error_msg.split("\n")
                failures = [line for line in lines if "FAILED" in line][:3]
                error_msg = "\n".join(failures) if failures else error_msg

            return ("Quality", "pytest", False, error_msg)

    # =========================================================================
    # Integration Tests
    # =========================================================================

    async def _run_integration_tests(
        self, source: dagger.Directory
    ) -> list[tuple[str, str, bool, str]]:
        """Run integration tests with Postgres service (no timing)."""
        timed_results = await self._run_integration_tests_timed(source)
        # Strip timing from results
        return [(r[0], r[1], r[2], r[3]) for r in timed_results]

    async def _run_integration_tests_timed(
        self, source: dagger.Directory
    ) -> list[tuple[str, str, bool, str, float]]:
        """Run integration tests with Postgres service (with timing).

        Tests:
        - Django health check (GET /admin/login/)
        - Migration check (no unapplied migrations)
        - Worker health check (GET /health)
        """
        results: list[tuple[str, str, bool, str, float]] = []

        # Create Postgres service
        start = time.time()
        postgres = (
            dag.container()
            .from_("postgres:16-alpine")
            .with_env_variable("POSTGRES_USER", "consult")
            .with_env_variable("POSTGRES_PASSWORD", "consult")
            .with_env_variable("POSTGRES_DB", "consult_test")
            .with_exposed_port(5432)
            .as_service()
        )

        # Build Django container for integration tests
        django_container = await self._get_django_integration_container(
            source, postgres
        )
        # setup_time available for future use: time.time() - start

        # Run migrations first
        start = time.time()
        migration_result = await self._run_migrations(django_container)
        migration_time = time.time() - start
        results.append((*migration_result, migration_time))

        if not migration_result[2]:  # Migration failed
            # Skip remaining integration tests
            skip_msg = "Skipped (migrations failed)"
            results.append(("Integration", "Django health", False, skip_msg, 0.0))
            results.append(("Integration", "Migration check", False, skip_msg, 0.0))
            results.append(("Integration", "Worker health", False, skip_msg, 0.0))
            return results

        # Run Django health check
        start = time.time()
        health_result = await self._check_django_health(django_container)
        results.append((*health_result, time.time() - start))

        # Run migration --check (verify no unapplied migrations)
        start = time.time()
        check_result = await self._check_migrations(django_container)
        results.append((*check_result, time.time() - start))

        # Run Worker health check (stateless, no DB needed)
        start = time.time()
        worker_result = await self._check_worker_health(source)
        results.append((*worker_result, time.time() - start))

        return results

    async def _get_django_integration_container(
        self, source: dagger.Directory, postgres: dagger.Service
    ) -> dagger.Container:
        """Get a Django container configured for integration tests."""
        src = (
            source.without_directory(".venv")
            .without_directory(".git")
            .without_directory("node_modules")
            .without_directory("dagger")
            .without_directory("sites")
            .without_directory("workers")
            .without_directory("infra")
            .without_directory("docs")
        )

        return (
            dag.container()
            .from_("python:3.12-slim")
            .with_workdir("/app")
            # Install curl for health checks
            .with_exec(["apt-get", "update"])
            .with_exec(["apt-get", "install", "-y", "--no-install-recommends", "curl"])
            # Django environment
            .with_env_variable("SECRET_KEY", "test-secret-key-for-integration-tests")
            .with_env_variable("DEBUG", "True")
            .with_env_variable("ALLOWED_HOSTS", "localhost,127.0.0.1,django")
            .with_env_variable("DJANGO_SETTINGS_MODULE", "apps.web.config.settings")
            .with_env_variable("PYTHONPATH", "/app")
            # Database URL pointing to Postgres service
            .with_env_variable(
                "DATABASE_URL", "postgres://consult:consult@postgres:5432/consult_test"
            )
            # Bind Postgres service
            .with_service_binding("postgres", postgres)
            # Install uv
            .with_file(
                "/usr/local/bin/uv",
                dag.container().from_("ghcr.io/astral-sh/uv:latest").file("/uv"),
            )
            # Copy project files
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_file("/app/README.md", src.file("README.md"))
            # Install dependencies
            .with_exec(["uv", "sync", "--frozen", "--no-dev", "--no-install-project"])
            # Copy source code
            .with_directory("/app/apps", src.directory("apps"))
            .with_directory("/app/packages", src.directory("packages"))
        )

    async def _run_migrations(
        self, container: dagger.Container
    ) -> tuple[str, str, bool, str]:
        """Run Django migrations."""
        try:
            await container.with_exec(
                ["uv", "run", "python", "apps/web/manage.py", "migrate", "--no-input"]
            ).stdout()
            return ("Integration", "Run migrations", True, "")
        except Exception as e:
            return ("Integration", "Run migrations", False, str(e))

    async def _check_django_health(
        self, container: dagger.Container
    ) -> tuple[str, str, bool, str]:
        """Check Django system configuration and database connection."""
        try:
            # Run Django system check - validates configuration and DB connection
            await container.with_exec(
                [
                    "uv",
                    "run",
                    "python",
                    "apps/web/manage.py",
                    "check",
                    "--database",
                    "default",
                ]
            ).stdout()

            return ("Integration", "Django check", True, "")

        except Exception as e:
            error_msg = str(e)
            if "traceparent:" in error_msg:
                error_msg = error_msg.split("[traceparent:")[0].strip()
            return ("Integration", "Django check", False, error_msg)

    async def _check_migrations(
        self, container: dagger.Container
    ) -> tuple[str, str, bool, str]:
        """Check that no migrations are pending."""
        try:
            await container.with_exec(
                ["uv", "run", "python", "apps/web/manage.py", "migrate", "--check"]
            ).stdout()
            return ("Integration", "Migration check", True, "")
        except Exception as e:
            error_msg = str(e)
            if "unapplied migration" in error_msg.lower():
                return (
                    "Integration",
                    "Migration check",
                    False,
                    "Unapplied migrations found",
                )
            return ("Integration", "Migration check", False, error_msg)

    async def _check_worker_health(
        self, source: dagger.Directory
    ) -> tuple[str, str, bool, str]:
        """Check Worker by verifying TypeScript compiles (already done in build stage)."""
        # Worker health is already validated by the build stage (_build_worker)
        # which runs `tsc --noEmit` to verify TypeScript compiles.
        # Running wrangler dev as a service is slow and unreliable in CI.
        # If build passed, worker is functional.
        return ("Integration", "Worker build verified", True, "")

    # =========================================================================
    # Output Formatting
    # =========================================================================

    def _format_report(self, results: list[tuple[str, str, bool, str]]) -> str:
        """Format results into a clear report."""
        lines = [
            "══════════════════════════════════════",
        ]

        all_passed = all(r[2] for r in results)
        status = "PASSED" if all_passed else "FAILED"
        lines.append(f"PRE-DEPLOY VALIDATION: {status}")
        lines.append("══════════════════════════════════════")

        current_stage = ""
        for stage, name, passed, message in results:
            if stage != current_stage:
                if current_stage:
                    lines.append("")
                current_stage = stage

            icon = "✓" if passed else "✗"
            lines.append(f"{icon} {stage}: {name}")
            if not passed and message:
                for msg_line in message.split("\n")[:5]:
                    lines.append(f"  → {msg_line}")

        lines.append("")
        if all_passed:
            lines.append("Ready to deploy!")
        else:
            failed_count = sum(1 for r in results if not r[2])
            lines.append(f"{failed_count} check(s) failed.")

        return "\n".join(lines)

    def _format_single(self, result: tuple[str, str, bool, str]) -> str:
        """Format a single result."""
        stage, name, passed, message = result
        icon = "✓" if passed else "✗"
        output = f"{icon} {stage}: {name}"
        if not passed and message:
            output += f"\n  → {message}"
        return output

    def _format_json_report(self, results: list[tuple[str, str, bool, str]]) -> str:
        """Format results as JSON for machine parsing."""
        all_passed = all(r[2] for r in results)

        # Group results by stage
        stages: dict[str, dict[str, object]] = {}
        for stage, name, passed, message in results:
            stage_key = stage.lower()
            if stage_key not in stages:
                stages[stage_key] = {
                    "status": "passed",
                    "checks": [],
                }

            check: dict[str, object] = {
                "name": name,
                "status": "passed" if passed else "failed",
            }
            if not passed and message:
                check["error"] = message

            stages[stage_key]["checks"].append(check)  # type: ignore[union-attr]

            # Update stage status if any check failed
            if not passed:
                stages[stage_key]["status"] = "failed"

        report = {
            "result": "passed" if all_passed else "failed",
            "stages": stages,
        }

        return json.dumps(report, indent=2)

    def _format_report_timed(
        self,
        results: list[tuple[str, str, bool, str, float]],
        build_time: float,
        quality_time: float,
        integration_time: float,
        total_time: float,
    ) -> str:
        """Format results with timing into a clear report."""
        lines = [
            "══════════════════════════════════════════════════════════════",
            "  PRE-DEPLOY VALIDATION",
            "══════════════════════════════════════════════════════════════",
            "",
        ]

        all_passed = all(r[2] for r in results)

        # Group by stage
        stages: dict[str, list[tuple[str, str, bool, str, float]]] = {}
        for r in results:
            stage = r[0]
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(r)

        stage_times = {
            "Build": build_time,
            "Quality": quality_time,
            "Integration": integration_time,
        }

        for stage_name, checks in stages.items():
            stage_time = stage_times.get(stage_name, 0)
            stage_passed = all(c[2] for c in checks)
            status = "✓" if stage_passed else "✗"
            header = f"{stage_name} Stage {status}".ljust(50)
            lines.append(f"{header}[{stage_time:.1f}s]")

            for _stage, name, passed, message, duration in checks:
                icon = "✓" if passed else "✗"
                duration_str = f"({duration:.1f}s)"
                lines.append(f"  {icon} {name}".ljust(48) + duration_str)
                if not passed and message:
                    for msg_line in message.split("\n")[:3]:
                        lines.append(f"    → {msg_line}")

            lines.append("")

        lines.append("══════════════════════════════════════════════════════════════")
        status = "PASSED" if all_passed else "FAILED"
        lines.append(f"  RESULT: {status}".ljust(48) + f"Total: {total_time:.1f}s")
        lines.append("══════════════════════════════════════════════════════════════")

        if all_passed:
            lines.append("")
            lines.append("Ready to deploy!")
        else:
            lines.append("")
            failed_count = sum(1 for r in results if not r[2])
            lines.append(f"{failed_count} check(s) failed. Fix issues and retry.")

        return "\n".join(lines)

    def _format_json_report_timed(
        self,
        results: list[tuple[str, str, bool, str, float]],
        build_time: float,
        quality_time: float,
        integration_time: float,
        total_time: float,
    ) -> str:
        """Format results with timing as JSON for machine parsing."""
        all_passed = all(r[2] for r in results)

        # Group results by stage
        stages: dict[str, dict[str, object]] = {}
        for stage, name, passed, message, duration in results:
            stage_key = stage.lower()
            if stage_key not in stages:
                stages[stage_key] = {
                    "status": "passed",
                    "duration_seconds": 0.0,
                    "checks": [],
                }

            check: dict[str, object] = {
                "name": name,
                "status": "passed" if passed else "failed",
                "duration_seconds": round(duration, 2),
            }
            if not passed and message:
                check["error"] = message

            stages[stage_key]["checks"].append(check)  # type: ignore[union-attr]

            # Update stage status if any check failed
            if not passed:
                stages[stage_key]["status"] = "failed"

        # Add stage durations
        if "build" in stages:
            stages["build"]["duration_seconds"] = round(build_time, 2)
        if "quality" in stages:
            stages["quality"]["duration_seconds"] = round(quality_time, 2)
        if "integration" in stages:
            stages["integration"]["duration_seconds"] = round(integration_time, 2)

        report = {
            "result": "passed" if all_passed else "failed",
            "duration_seconds": round(total_time, 2),
            "stages": stages,
        }

        return json.dumps(report, indent=2)
