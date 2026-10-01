#!/usr/bin/env zsh
# Load synchronization without interactive startup files or completion setup.
source "$DOTFILES_INSTALL_ROOT/zsh/functions.zsh"
"${1}_merge_config" || exit $?
(( _AGENTCFG_SKIPPED == 0 )) || exit 2
