# GitHub identity profiles: one gh account plus one git author per profile.
#
#   ghp            show the active profile
#   ghp list       list configured profiles
#   ghp <profile>  switch gh account, global git author and git's HTTPS credentials
#
# Profiles live outside the repo, one per line, in
# ${XDG_CONFIG_HOME:-~/.config}/dotfiles/github-profiles:
#
#   # profile  gh-user           email                     git author name
#   personal   my-handle         me@example.com            My Name
#   work       my-work-handle    me@company.example        My Name
#
# The active profile is whichever profile owns the active gh account, read from
# gh's hosts.yml, so a manual `gh auth switch` is reflected too. The prompt and
# ai/claude/hooks/statusline.sh both display it and flag a repo whose effective
# git email belongs to a different profile.

_ghp_file() { print -r -- "${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/github-profiles"; }

# Active gh user for github.com, parsed without running gh (it is on every prompt).
_ghp_active_user() {
  local hosts="${GH_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/gh}/hosts.yml" line in_host=0
  [[ -r $hosts ]] || return 1
  while IFS= read -r line; do
    if [[ $line == [^[:space:]]* ]]; then
      [[ $line == github.com:* ]] && in_host=1 || in_host=0
    elif (( in_host )) && [[ $line == '    user: '* ]]; then
      print -r -- "${line#    user: }"
      return 0
    fi
  done < "$hosts"
  return 1
}

# Print "profile gh-user email name" for the first line whose field $1 equals $2.
_ghp_lookup() {
  local field=$1 value=$2 file line
  local -a f
  file=$(_ghp_file)
  [[ -r $file ]] || return 1
  while IFS= read -r line; do
    f=(${=line})
    (( ${#f} >= 4 )) && [[ ${f[1]} != \#* ]] || continue
    [[ ${(L)f[$field]} == ${(L)value} ]] && { print -r -- "$line"; return 0; }
  done < "$file"
  return 1
}

# Prompt segment: [gh:work], or a red [gh:work git:personal] when the effective
# git email in the current repo belongs to another profile (or none).
github_profile_prompt() {
  local user entry email owner
  local -a f
  user=$(_ghp_active_user) || return 0
  if entry=$(_ghp_lookup 2 "$user"); then
    f=(${=entry})
  else
    f=("$user")
  fi
  if git rev-parse --is-inside-work-tree &>/dev/null; then
    email=$(git config user.email 2>/dev/null)
    if [[ -n $email && ${(L)email} != ${(L)f[3]-} ]]; then
      owner=$(_ghp_lookup 3 "$email") && owner=${${=owner}[1]} || owner=$email
      print -rn -- "%{$fg[red]%}[gh:${f[1]} git:${owner}]%{$reset_color%}"
      return 0
    fi
  fi
  print -rn -- "%{$fg[magenta]%}[gh:${f[1]}]%{$reset_color%}"
}

ghp() {
  local file entry user email name
  local -a f
  file=$(_ghp_file)
  if [[ ! -r $file ]]; then
    print -u2 "No profiles: create $file (format in ~/dotfiles/zsh/github-profile.zsh)."
    return 1
  fi

  case ${1-} in
    '')
      user=$(_ghp_active_user) || { print -u2 'gh is not logged in to github.com.'; return 1; }
      entry=$(_ghp_lookup 2 "$user") && f=(${=entry}) || f=('(unlisted)' "$user")
      print -r -- "profile:  ${f[1]}"
      print -r -- "gh user:  $user"
      print -r -- "git:      $(git config --global user.name) <$(git config --global user.email)>"
      email=$(git config user.email 2>/dev/null)
      if git rev-parse --is-inside-work-tree &>/dev/null && [[ $email != "$(git config --global user.email)" ]]; then
        print -r -- "this repo overrides git email: $email"
      fi
      ;;
    list)
      user=$(_ghp_active_user)
      while IFS= read -r entry; do
        f=(${=entry})
        (( ${#f} >= 4 )) && [[ ${f[1]} != \#* ]] || continue
        [[ ${(L)f[2]} == ${(L)user-} ]] && print -rn -- '* ' || print -rn -- '  '
        print -r -- "${f[1]}  ${f[2]}  ${f[4,-1]} <${f[3]}>"
      done < "$file"
      ;;
    *)
      entry=$(_ghp_lookup 1 "$1") || { print -u2 "Unknown profile: $1 (see ghp list)"; return 1; }
      f=(${=entry})
      user=${f[2]} email=${f[3]} name=${f[4,-1]}
      if ! gh auth switch --hostname github.com --user "$user" >/dev/null 2>&1; then
        print -u2 "gh has no login for $user. Run: gh auth login --hostname github.com --git-protocol https"
        print -u2 "(log in as $user in the browser), then rerun: ghp $1"
        return 1
      fi
      git config --global user.name "$name"
      git config --global user.email "$email"
      # Without this git pushes with whatever single github.com credential
      # osxkeychain cached, regardless of the active gh account.
      if [[ "$(git config --global --get-all credential.https://github.com.helper 2>/dev/null)" != *'gh auth git-credential'* ]]; then
        gh auth setup-git --hostname github.com
      fi
      print -r -- "Switched to $1: gh $user, git $name <$email>"
      if git rev-parse --is-inside-work-tree &>/dev/null && [[ "$(git config user.email)" != "$email" ]]; then
        print -u2 "Note: this repo sets its own git email ($(git config user.email))."
      fi
      ;;
  esac
}

_ghp() {
  local file=$(_ghp_file) line
  local -a f profiles
  [[ -r $file ]] && while IFS= read -r line; do
    f=(${=line})
    (( ${#f} >= 4 )) && [[ ${f[1]} != \#* ]] && profiles+=(${f[1]})
  done < "$file"
  _arguments "1:profile:(list $profiles)"
}
(( $+functions[compdef] )) && compdef _ghp ghp
