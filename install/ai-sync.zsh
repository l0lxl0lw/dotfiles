#!/usr/bin/env zsh
# Sync one tool from the active hubs, without interactive startup files or
# completion setup. Exit 2 when a collision was skipped so the installer can say so.
source "$DOTFILES_INSTALL_ROOT/zsh/functions.zsh"
source "$DOTFILES_INSTALL_ROOT/zsh/hubs.zsh"
hubs_sync --tool "$1" || exit $?
(( _AGENTCFG_SKIPPED == 0 )) || exit 2
