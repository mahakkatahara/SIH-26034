"""
Production Hygiene Tests — Verify entrypoint.sh, Dockerfile, and docker-compose configurations
"""
import os
import stat
import subprocess
import tempfile
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENTRYPOINT_PATH = os.path.join(BACKEND_DIR, "entrypoint.sh")
DOCKERFILE_PATH = os.path.join(BACKEND_DIR, "Dockerfile")
COMPOSE_PATH = os.path.abspath(os.path.join(BACKEND_DIR, "..", "docker-compose.yml"))


def test_entrypoint_script_syntax():
    """Verify entrypoint.sh has valid POSIX shell syntax."""
    assert os.path.exists(ENTRYPOINT_PATH)
    proc = subprocess.run(["sh", "-n", ENTRYPOINT_PATH], capture_output=True, text=True)
    assert proc.returncode == 0, f"Syntax error in entrypoint.sh: {proc.stderr}"


def test_entrypoint_seeding_is_conditional_when_disabled():
    """When SEED_ON_START is unset or false, seed command must not run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "executed.log")
        alembic_bin = os.path.join(tmpdir, "alembic")
        python_bin = os.path.join(tmpdir, "python")

        with open(alembic_bin, "w", newline="\n") as f:
            f.write(f'#!/bin/sh\necho "alembic $@" >> "{log_file}"\n')
        with open(python_bin, "w", newline="\n") as f:
            f.write(f'#!/bin/sh\necho "python $@" >> "{log_file}"\n')

        os.chmod(alembic_bin, stat.S_IRWXU)
        os.chmod(python_bin, stat.S_IRWXU)

        env = dict(os.environ)
        env["PATH"] = f"{tmpdir}:{env.get('PATH', '')}"
        env.pop("SEED_ON_START", None)

        proc = subprocess.run(
            ["sh", ENTRYPOINT_PATH, "echo", "done"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert proc.returncode == 0

        with open(log_file, "r") as f:
            logs = f.read()

        assert "alembic upgrade head" in logs
        assert "app.scripts.seed" not in logs
        assert "skipping database seeding" in proc.stdout


def test_entrypoint_seeding_is_conditional_when_enabled():
    """When SEED_ON_START=true, seed command must run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "executed.log")
        alembic_bin = os.path.join(tmpdir, "alembic")
        python_bin = os.path.join(tmpdir, "python")

        with open(alembic_bin, "w", newline="\n") as f:
            f.write(f'#!/bin/sh\necho "alembic $@" >> "{log_file}"\n')
        with open(python_bin, "w", newline="\n") as f:
            f.write(f'#!/bin/sh\necho "python $@" >> "{log_file}"\n')

        os.chmod(alembic_bin, stat.S_IRWXU)
        os.chmod(python_bin, stat.S_IRWXU)

        env = dict(os.environ)
        env["PATH"] = f"{tmpdir}:{env.get('PATH', '')}"
        env["SEED_ON_START"] = "true"

        proc = subprocess.run(
            ["sh", ENTRYPOINT_PATH, "echo", "done"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert proc.returncode == 0

        with open(log_file, "r") as f:
            logs = f.read()

        assert "alembic upgrade head" in logs
        assert "python -m app.scripts.seed" in logs
        assert "seeding initial database data" in proc.stdout


def test_dockerfile_production_no_reload():
    """Verify Dockerfile CMD does not use --reload."""
    with open(DOCKERFILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "--reload" not in content


def test_docker_compose_backend_no_reload():
    """Verify docker-compose.yml backend service does not use --reload."""
    if os.path.exists(COMPOSE_PATH):
        with open(COMPOSE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "--reload" not in content
