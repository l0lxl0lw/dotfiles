install_component() {
  ensure_tool emacs emacs
  clone_plugin https://github.com/syl20bnr/spacemacs "$HOME/.emacs.d"
  if (( ! DRY_RUN )) && [[ ! -f "$HOME/.emacs.d/core/core-spacemacs.el" ]]; then
    say 'Existing ~/.emacs.d is not Spacemacs; preserved. Move it aside after backing it up, then rerun.'
    return 2
  fi
  if exists "$HOME/.emacs"; then
    say '~/.emacs takes precedence over Spacemacs; reconcile it manually before continuing.'
    return 2
  fi
  copy_file "$ROOT/emacs/spacemacs.el" "$HOME/.spacemacs"
  say 'Start Emacs to let Spacemacs download its packages. Customize the writable ~/.spacemacs file.'
}
