#!/bin/bash
set -euo pipefail
requested_dry="$DRY_RUN" requested_mode="$MODE"
source "$ROOT/install/lib.sh"
DRY_RUN="$requested_dry" MODE="$requested_mode"
source "$ROOT/install/modules/$1.sh"
install_component
