#!/usr/bin/env bash
# List the agent skills installed on this machine, grouped by where they come from.
#
#   list-skills.sh            every skill: this repo's first, then the global ones
#   list-skills.sh --repo     only the skills the current repo defines
#   list-skills.sh --desc     one skill per line, with its description
#   list-skills.sh --names    one skill name per line, no grouping, for piping
#
# A repo's own skills are whatever lives under its .claude/skills, .agents/skills,
# .codex/skills or .grok/skills -- they shadow a global skill of the same name.
set -uo pipefail

repo_only=0
names_only=0
with_desc=0
for arg in "$@"; do
  case "$arg" in
    --repo|--repo-only) repo_only=1 ;;
    --desc|--descriptions) with_desc=1 ;;
    --names) names_only=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "list-skills.sh: unknown argument '$arg'" >&2; exit 2 ;;
  esac
done

# Physical path of a directory, with every symlink resolved. ~/.claude/skills is
# mostly symlinks into dotfiles, and the real path is what says which group a
# skill belongs to.
realdir() { (cd "$1" 2>/dev/null && pwd -P); }

# rank keeps repo skills at the top of the sort, plugins at the bottom.
group_for() {
  local real="$1" rest grp
  case "$real" in
    "$HOME"/dotfiles/ai/shared/skills/*)
      rest="${real#"$HOME"/dotfiles/ai/shared/skills/}"; echo "1|dotfiles · shared/${rest%%/*}" ;;
    "$HOME"/dotfiles/ai/*/skills/*)
      rest="${real#"$HOME"/dotfiles/ai/}"; echo "1|dotfiles · ${rest%%/*}" ;;
    "$HOME"/.claude/skills/gstack/*) echo "2|gstack" ;;
    "$HOME"/.claude/skills/*)        echo "2|global · ~/.claude/skills" ;;
    "$HOME"/.claude/plugins/cache/*)
      rest="${real#"$HOME"/.claude/plugins/cache/}"; rest="${rest#*/}"; echo "3|plugin · ${rest%%/*}" ;;
    *) grp="${real%/*}"; echo "3|${grp/#"$HOME"/\~}" ;;
  esac
}

# Frontmatter description, trimmed to one terminal line. Handles the plain,
# quoted and block-scalar (`>-`, `|`) forms all three runtimes accept.
description_of() {
  awk '
    NR==1 && $0!="---" { exit }
    NR>1 && $0=="---"  { exit }
    !indesc && /^description:/ {
      line=$0; sub(/^description:[[:space:]]*/, "", line)
      if (line=="" || line ~ /^[>|][-+0-9]*[[:space:]]*$/) { indesc=1; next }
      buf=line; exit
    }
    indesc {
      if ($0 ~ /^[[:space:]]+[^[:space:]]/) { s=$0; sub(/^[[:space:]]+/, "", s); buf = buf (buf=="" ? "" : " ") s; next }
      exit
    }
    END {
      gsub(/^["'"'"']|["'"'"']$/, "", buf); gsub(/[[:space:]]+/, " ", buf)
      if (length(buf) > 104) buf = substr(buf, 1, 103) "\xe2\x80\xa6"
      print buf
    }
  ' "$1"
}

emit() { # emit <rank|group override or ""> <skills-dir>
  local override="$1" dir="$2" skill name real group
  [ -d "$dir" ] || return 0
  for skill in "$dir"/*/; do
    [ -f "$skill/SKILL.md" ] || continue
    name="$(basename "$skill")"
    case "$name" in _*) continue ;; esac
    if [ -n "$override" ]; then
      group="$override"
    else
      real="$(realdir "$skill")"; [ -n "$real" ] || continue
      group="$(group_for "$real")"
    fi
    printf '%s\t%s\t%s\n' "$group" "$name" "$(description_of "$skill/SKILL.md")"
  done
}

root="$(git rev-parse --show-toplevel 2>/dev/null)" || root=""
in_git=1; [ -n "$root" ] || { root="$PWD"; in_git=0; }

collected="$(
  for d in .claude/skills .agents/skills .codex/skills .grok/skills; do
    emit "0|this repo · $d" "$root/$d"
  done
  if [ "$repo_only" -eq 0 ]; then
    emit "" "$HOME/.claude/skills"
    # installed_plugins.json names the version of each plugin actually in use;
    # the cache keeps older ones around, and listing those would show the same
    # skill twice under one plugin.
    installed="$HOME/.claude/plugins/installed_plugins.json"
    if [ -f "$installed" ]; then
      sed -n 's/.*"installPath"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$installed" | sort -u |
        while IFS= read -r p; do emit "" "$p/skills"; done
    else
      for p in "$HOME"/.claude/plugins/cache/*/*/*/skills; do emit "" "$p"; done
    fi
  fi
)"

if [ "$names_only" -eq 1 ]; then
  printf '%s\n' "$collected" | awk -F'\t' 'NF{print $2}' | sort -u
  exit 0
fi

if [ -z "$collected" ]; then
  if [ "$repo_only" -eq 1 ]; then
    [ "$in_git" -eq 1 ] \
      && echo "No repo skills: $root defines none (looked in .claude/skills, .agents/skills, .codex/skills, .grok/skills)." \
      || echo "Not inside a git repo, and $PWD defines no skills."
  else
    echo "No skills found."
  fi
  exit 0
fi

tmp="$(mktemp -t list-skills)" || exit 1
trap 'rm -f "$tmp"' EXIT
printf '%s\n' "$collected" | LC_ALL=C sort -t"$(printf '\t')" -k1,1 -k2,2 > "$tmp"

width="${COLUMNS:-0}"
[ "$width" -gt 20 ] 2>/dev/null || width="$(tput cols 2>/dev/null)" || width=0
[ "$width" -gt 20 ] 2>/dev/null || width=100

# Two passes: the first learns which repo skills shadow a global skill of the
# same name, the second prints. A shadowed global never loads, so saying which
# ones are covered up matters more than listing them twice.
awk -F'\t' -v root="$root" -v with_desc="$with_desc" -v width="$width" '
  NR==FNR {
    if ($1 ~ /^0\|/) repo[$2] = 1; else if ($2 in repo) shadowed[$2] = 1
    next
  }
  {
    split($1, g, "|"); group = g[2]; name = $2
    if (($1 ~ /^0\|/) && (name in shadowed)) name = name " *"
    if (!($1 ~ /^0\|/) && (name in repo)) next   # shadowed global: never loads
    if (group != last) { groups[++ng] = group; last = group }
    n = ++count[group]
    item[group, n] = name
    desc[group, n] = $3
    if (length(name) > maxname) maxname = length(name)
    if ($1 ~ /^0\|/) has_repo = 1
    total++
  }
  END {
    if (with_desc) {
      for (i = 1; i <= ng; i++) {
        if (i > 1) printf "\n"
        printf "%s\n", groups[i]
        for (j = 1; j <= count[groups[i]]; j++)
          printf "  %-28s %s\n", item[groups[i], j], desc[groups[i], j]
      }
    } else {
      colw = maxname + 2
      cols = int((width - 2) / colw)
      if (cols < 1) cols = 1
      fmt = "%-" colw "s"
      for (i = 1; i <= ng; i++) {
        if (i > 1) printf "\n"
        printf "%s\n", groups[i]
        n = count[groups[i]]
        rows = int((n + cols - 1) / cols)
        for (r = 1; r <= rows; r++) {          # column-major: read down, A-Z
          line = ""
          for (c = 0; c < cols; c++) {
            k = c * rows + r
            if (k <= n) line = line sprintf(fmt, item[groups[i], k])
          }
          sub(/ +$/, "", line)
          printf "  %s\n", line
        }
      }
    }
    printf "\n%d skills.%s\n", total, (has_repo ? " Repo: " root : "")
    for (nm in shadowed) s = s (s == "" ? "" : ", ") nm
    if (s != "") printf "* repo skill shadows a global one of the same name: %s\n", s
  }
' "$tmp" "$tmp"
