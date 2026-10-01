#!/bin/bash
set -euo pipefail
ROOT="$DOTFILES_INSTALL_ROOT"
source "$ROOT/install/lib.sh"
case "$1" in
  link) link_file "$2" "$3";;
  approve) approve_change "$2";;
  *) die 'Invalid adapter operation';;
esac
