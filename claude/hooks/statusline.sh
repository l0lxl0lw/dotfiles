#!/bin/bash

# Claude Code status line.
#
# Deliberately mirrors the Codex CLI status line configured in
# ../../codex/config.toml.managed, so the two tools read identically:
#
#   dir · repo · branch · Context N% used · 5h N% left · weekly N% left · model
#
# Codex's status line is a fixed list of item ids -- it cannot render progress
# bars, reset countdowns, a second line, or a different separator. So this script
# stays inside what Codex can express, and only adds what Codex silently omits
# (reset countdowns, the dirty marker, a clickable repo link).
#
# On "used" vs "left": context is a ceiling you fill, so it reads as used and a
# high number is bad. Quotas are a budget you spend down, so they read as left
# and a LOW number is bad -- note pct_color is fed the used value in both cases.
# This matches Codex, which words them the same way and cannot be changed.
#
# Requires: jq, bc

input=$(cat)

model_name="Claude"
pct_int=0

if command -v jq &>/dev/null && [ -n "$input" ]; then
  display_name=$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)
  [ -n "$display_name" ] && model_name="$display_name"

  used=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)
  if [ -n "$used" ] && [ "$used" != "null" ]; then
    pct_int=$(printf '%.0f' "$used")
  fi

  five_hr=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
  five_hr_resets=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // empty' 2>/dev/null)
  seven_day=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)
  seven_day_resets=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.resets_at // empty' 2>/dev/null)
fi

# Dracula theme (true color)
purple="\033[38;2;189;147;249m"
cyan="\033[38;2;139;233;253m"
pink="\033[38;2;255;121;198m"
green="\033[38;2;80;250;123m"
comment="\033[38;2;98;114;164m"
bold="\033[1m"
reset="\033[0m"

# Codex joins items with " · " and offers no way to change it.
sep=" ${comment}·${reset} "

# Colour by percentage CONSUMED, green -> yellow -> orange -> red.
pct_color() {
  local val=$1
  if   [ "$val" -ge 80 ]; then printf '\033[38;2;255;85;85m'    # red
  elif [ "$val" -ge 60 ]; then printf '\033[38;2;255;184;108m'  # orange
  elif [ "$val" -ge 40 ]; then printf '\033[38;2;241;250;140m'  # yellow
  else                         printf '\033[38;2;80;250;123m'   # green
  fi
}

# unix timestamp -> "4.2h" / "23m" / "2.3d"
time_until() {
  local resets_at=$1 now diff
  now=$(date +%s)
  diff=$((resets_at - now))
  [ "$diff" -le 0 ] && printf 'now' && return
  if   [ "$diff" -ge 86400 ]; then printf '%s' "$(echo "scale=1; $diff / 86400" | bc)d"
  elif [ "$diff" -ge 3600 ];  then printf '%s' "$(echo "scale=1; $diff / 3600" | bc)h"
  else                             printf '%s' "$(echo "scale=0; $diff / 60" | bc)m"
  fi
}

# "<label> N% left (reset)" for a quota. Args: label, used_pct, resets_at
# Displays remaining, but colours by consumed so red still means trouble.
rate_item() {
  local label=$1 used_raw=$2 resets=$3
  [ -z "$used_raw" ] || [ "$used_raw" = "null" ] && return 1
  local used_int left color countdown=""
  used_int=$(printf '%.0f' "$used_raw")
  left=$((100 - used_int))
  color=$(pct_color "$used_int")
  if [ -n "$resets" ] && [ "$resets" != "null" ]; then
    # ↻ rather than an emoji: emoji render in their own palette and ignore the
    # dim comment colour, so they shout on a line meant to be scannable.
    countdown=" ${comment}(↻ $(time_until "$resets"))${reset}"
  fi
  # Single %, not %%: the caller emits this through printf '%b', which expands
  # backslash escapes but does not treat % as a conversion.
  printf '%b' "${comment}${label}${reset} ${color}${left}%${reset} ${comment}left${reset}${countdown}"
}

# Location
dir_path=${PWD/#$HOME/\~}

repo_link=""
git_info=""
if git rev-parse --git-dir &>/dev/null 2>&1; then
  branch=$(git branch --show-current 2>/dev/null)
  if [ -n "$branch" ]; then
    dirty=""
    [ -n "$(git status --porcelain 2>/dev/null)" ] && dirty="*"
    git_info="${green}${branch}${dirty}${reset}"
  fi
  remote_url=$(git remote get-url origin 2>/dev/null)
  if [ -n "$remote_url" ]; then
    remote_url=$(echo "$remote_url" | sed 's|git@github.com:|https://github.com/|; s|\.git$||')
    repo_link="\033]8;;${remote_url}\a${pink}$(basename "$remote_url")${reset}\033]8;;\a"
  fi
fi

# Assemble: dir · repo · branch · context · 5h · weekly · model
line="${cyan}${dir_path}${reset}"
[ -n "$repo_link" ] && line="${line}${sep}${repo_link}"
[ -n "$git_info" ]  && line="${line}${sep}${git_info}"

ctx_color=$(pct_color "$pct_int")
line="${line}${sep}${comment}Context${reset} ${ctx_color}${pct_int}%${reset} ${comment}used${reset}"

if item=$(rate_item "5h" "$five_hr" "$five_hr_resets"); then
  line="${line}${sep}${item}"
fi
# Labelled "weekly", not "7d", to match what Codex prints for weekly-limit.
if item=$(rate_item "weekly" "$seven_day" "$seven_day_resets"); then
  line="${line}${sep}${item}"
fi

line="${line}${sep}${bold}${purple}${model_name}${reset}"

printf '%b\n' "$line"
