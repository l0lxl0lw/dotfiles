#!/usr/bin/env zsh
# Sync one tool (or all) from the active hubs, or print the hubs doctor report,
# without interactive startup files or completion setup. Exit 2 when a
# collision was skipped so the installer can say so.
source "$DOTFILES_INSTALL_ROOT/zsh/functions.zsh"
source "$DOTFILES_INSTALL_ROOT/zsh/hubs.zsh"
case "$1" in
  doctor) hubs_doctor; exit $?;;
  hub-file)  # print <hub>/<path> for the first listed hub that has it
    local hub; for hub in ${(f)"$(hubs_list 2>/dev/null)"}; do
      [[ -f "$hub/$2" ]] && { print -r -- "$hub/$2"; exit 0 }
    done; exit 1;;
  all) hubs_sync || exit $?;;
  grok) grok_merge_config || exit $?;;
  *) hubs_sync --tool "$1" || exit $?;;
esac
(( _AGENTCFG_SKIPPED == 0 )) || exit 2
