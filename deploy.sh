#!/bin/bash
# Bootstrap uses the Bash shipped with macOS; no Python/Node prerequisite.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")" && pwd -P)"
export ROOT
source "$ROOT/install/lib.sh"
main "$@"
