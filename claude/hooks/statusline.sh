#!/bin/bash

# Claude Code Status Line — Elegant edition
# Line 1: Model │ 📍 path │ repo │ 🔀 branch
# Line 2: 📊 context bar │ ⏱ 5h/7d rate limits with reset countdowns
#
# Requires: jq (brew install jq)

input=$(cat)

# Parse JSON
model_name="Claude"
pct_int=0
pct="0.0"

if command -v jq &>/dev/null && [ -n "$input" ]; then
  display_name=$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)
  [ -n "$display_name" ] && model_name="$display_name"

  used=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)
  if [ -n "$used" ] && [ "$used" != "null" ]; then
    pct_int=$(printf '%.0f' "$used")
    pct=$(printf '%.0f' "$used")
  fi

  five_hr=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
  five_hr_resets=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // empty' 2>/dev/null)
  seven_day=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)
  seven_day_resets=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.resets_at // empty' 2>/dev/null)
fi

# Dracula theme colors (true color)
purple="\033[38;2;189;147;249m"   # #bd93f9
cyan="\033[38;2;139;233;253m"     # #8be9fd
pink="\033[38;2;255;121;198m"     # #ff79c6
green="\033[38;2;80;250;123m"     # #50fa7b
comment="\033[38;2;98;114;164m"   # #6272a4
bold="\033[1m"
reset="\033[0m"

# Separator
sep=" ${comment}│${reset} "

# Slim progress bar (args: percentage_int, width)
make_bar() {
  local pct_val=$1 width=${2:-12}
  local filled_count=$((pct_val * width / 100))
  [ "$filled_count" -gt "$width" ] && filled_count=$width
  local empty_count=$((width - filled_count))
  printf '%s%s' "$(printf '%*s' "$filled_count" '' | tr ' ' '▰')" "$(printf '%*s' "$empty_count" '' | tr ' ' '▱')"
}

# Color by percentage (Dracula: green → yellow → orange → red)
pct_color() {
  local val=$1
  if [ "$val" -ge 80 ]; then
    printf '\033[38;2;255;85;85m'      # #ff5555 red
  elif [ "$val" -ge 60 ]; then
    printf '\033[38;2;255;184;108m'    # #ffb86c orange
  elif [ "$val" -ge 40 ]; then
    printf '\033[38;2;241;250;140m'    # #f1fa8c yellow
  else
    printf '\033[38;2;80;250;123m'     # #50fa7b green
  fi
}

# Countdown helper (args: unix_timestamp) → "4.2h" or "23m" or "2.3d"
time_until() {
  local resets_at=$1
  local now=$(date +%s)
  local diff=$((resets_at - now))
  [ "$diff" -le 0 ] && printf 'now' && return
  if [ "$diff" -ge 86400 ]; then
    printf '%s' "$(echo "scale=1; $diff / 86400" | bc)d"
  elif [ "$diff" -ge 3600 ]; then
    printf '%s' "$(echo "scale=1; $diff / 3600" | bc)h"
  else
    printf '%s' "$(echo "scale=0; $diff / 60" | bc)m"
  fi
}

# Context bar
bar_color=$(pct_color "$pct_int")
bar=$(make_bar "$pct_int" 12)

# Directory relative to home
dir_path=$(echo "$PWD" | sed "s|^$HOME|~|")

# Git branch + clickable repo link
git_info=""
repo_link=""
if git rev-parse --git-dir &>/dev/null 2>&1; then
  branch=$(git branch --show-current 2>/dev/null)
  if [ -n "$branch" ]; then
    dirty=""
    [ -n "$(git status --porcelain 2>/dev/null)" ] && dirty="*"
    git_info="${green}$branch${dirty}${reset}"
  fi

  # Clickable repo link (OSC 8)
  remote_url=$(git remote get-url origin 2>/dev/null)
  if [ -n "$remote_url" ]; then
    remote_url=$(echo "$remote_url" | sed 's|git@github.com:|https://github.com/|' | sed 's|\.git$||')
    repo_name=$(basename "$remote_url")
    repo_link="\033]8;;${remote_url}\a${pink}${repo_name}${reset}\033]8;;\a"
  fi
fi

# Rate limit bars with reset countdown
rate_info=""
if [ -n "$five_hr" ] && [ "$five_hr" != "null" ]; then
  five_hr_int=$(printf '%.0f' "$five_hr")
  five_hr_color=$(pct_color "$five_hr_int")
  five_hr_bar=$(make_bar "$five_hr_int" 10)
  five_hr_reset=""
  if [ -n "$five_hr_resets" ] && [ "$five_hr_resets" != "null" ]; then
    five_hr_reset=" ${comment}(🔄 $(time_until "$five_hr_resets"))${reset}"
  fi
  rate_info="${comment}5h${reset} ${five_hr_color}${five_hr_bar}${reset} ${five_hr_int}%${five_hr_reset}"
fi
if [ -n "$seven_day" ] && [ "$seven_day" != "null" ]; then
  seven_day_int=$(printf '%.0f' "$seven_day")
  seven_day_color=$(pct_color "$seven_day_int")
  seven_day_bar=$(make_bar "$seven_day_int" 10)
  seven_day_reset=""
  if [ -n "$seven_day_resets" ] && [ "$seven_day_resets" != "null" ]; then
    seven_day_reset=" ${comment}(🔄 $(time_until "$seven_day_resets"))${reset}"
  fi
  [ -n "$rate_info" ] && rate_info="$rate_info${sep}"
  rate_info="${rate_info}${comment}7d${reset} ${seven_day_color}${seven_day_bar}${reset} ${seven_day_int}%${seven_day_reset}"
fi

# Line 1: Model │ 📍 path │ repo │ 🔀 branch
line1="${bold}${purple}${model_name}${reset}${sep}${cyan}${dir_path}${reset}"
[ -n "$repo_link" ] && line1="$line1${sep}$repo_link"
[ -n "$git_info" ] && line1="$line1${sep}$git_info"

# Line 2: 📊 context │ ⏱ rate limits
line2="${comment}ctx${reset} ${bar_color}${bar}${reset} ${pct}%"
[ -n "$rate_info" ] && line2="$line2${sep}$rate_info"

printf '%b\n\n%b\n' "$line1" "$line2"
