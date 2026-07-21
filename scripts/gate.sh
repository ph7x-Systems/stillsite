#!/usr/bin/env sh
# The local gate: run as the LAST step before every commit — after ANY
# edit, however small. Verifies only; it never rewrites files.
#
#   ./scripts/gate.sh          # lint, format, types, full test suite
#   FAST=1 ./scripts/gate.sh   # skip the test suite (docs-only changes)
#
# Set SARDINE_POSTGRES_URL / SARDINE_MYSQL_URL / SARDINE_MSSQL_URL to run
# the storage conformance suite against the real engines as CI does.
set -eu

PY="${PYTHON:-.venv/bin/python}"

echo "==> ruff check"
"$PY" -m ruff check .
echo "==> ruff format --check"
"$PY" -m ruff format --check .
echo "==> mypy"
"$PY" -m mypy .
echo "==> bandit"
"$PY" -m bandit -q -r apps packages scripts -x '*/static/*,*/assets/*' -ll -ii
if [ "${FAST:-0}" = "1" ]; then
  echo "==> tests skipped (FAST=1)"
else
  echo "==> pytest"
  "$PY" -m pytest -q
fi
echo "==> gate green"
