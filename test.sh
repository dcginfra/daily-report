#!/usr/bin/env bash
# Run the test suite.
# All arguments are forwarded to pytest.
#
# Examples:
#   ./test.sh              # run all tests
#   ./test.sh -v           # verbose output
#   ./test.sh -k tc01      # run only tc01 tests
#   ./test.sh -x           # stop on first failure

set -euo pipefail
cd "$(dirname "$0")"
exec python3 -m pytest tests/ "$@"
