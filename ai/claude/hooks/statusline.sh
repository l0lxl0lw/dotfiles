#!/bin/bash

# Claude Code status line.
#
# Deliberately mirrors the Codex CLI status line configured in
# ../../codex/config.toml.managed, so the two tools read identically:
#
#   dir · repo · branch · Context N% used · 5h N% left · weekly N% left · model
#
# Codex's status line is a fixed list of item ids -- it cannot render progress
# bars, a second line, or a different separator. So this script stays inside what
# Codex can express, and only adds what Codex silently omits (the dirty marker,
# a clickable repo link).
#
# The line is a flat list: every item is `label value` separated by ` · `, with
# no nesting anywhere. That uniformity is what makes it scannable -- the eye
# locks onto the separator and never has to switch parsing modes. Reset
# countdowns "(↻ 2.5h)" used to hang off the two quota items and were the whole
# reason to break that rule: three of seven items carried a second grouping
# level, and "5h ... (↻ 2.5h)" put two different h-quantities inside one item.
# On identical input they also cost 29 of the line's 130 visible characters and 3
# of its 8 numeric tokens -- digits force a fixation each, so that is the cost
# that actually lands. Dropped, along with the parenthetical in the model name,
# putting the line at 101 characters and 5 numbers against Codex's 86 and 3. If
# a countdown is ever wanted back, it belongs in /usage, not here.
#
# On "used" vs "left": context is a ceiling you fill, so it reads as used and a
# high number is bad. Quotas are a budget you spend down, so they read as left
# and a LOW number is bad -- note pct_color is fed the used value in both cases.
# This matches Codex, which words them the same way and cannot be changed.
#
# Requires: jq

input=$(cat)

model_name="Claude"
effort=""
pct_int=0

if command -v jq &>/dev/null && [ -n "$input" ]; then
  display_name=$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)
  # "Opus 5 (1M context)" -> "Opus 5". The qualifier is the third nested group on
  # a line whose whole point is that it has none, and it never changes mid-session.
  [ -n "$display_name" ] && model_name="${display_name%% (*}"

  # Codex prints "gpt-5.5 medium" via model-with-reasoning; .effort.level is the
  # equivalent here (low|medium|high|xhigh). Also on offer if ever wanted:
  # .fast_mode, .thinking.enabled, .output_style.name, .cost.total_cost_usd.
  effort=$(printf '%s' "$input" | jq -r '.effort.level // empty' 2>/dev/null)

  used=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)
  if [ -n "$used" ] && [ "$used" != "null" ]; then
    pct_int=$(printf '%.0f' "$used")
  fi

  five_hr=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)
  seven_day=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)
fi

# Dracula theme (true color).
#
# Hue carries meaning here, so each one gets exactly one job:
#
#   green / gold / blue   where you are -- dir, repo, branch (following Codex)
#   green..red scale      how heavy things are -- usage items and effort
#   comment (dim)         separators
#   bold, no hue          the model
#
# Location hues copy Codex's. Note Codex can spend green and yellow there only
# because its quota renders pink -- it has no green or yellow in its data
# channel, and we do. So the two groups are separated by CHROMA instead: the
# three below are saturated, and pct_color's scale is muted. Same hue, different
# intensity, and the eye groups by intensity first. If a location colour is ever
# dulled to match the data scale, that separation collapses and a green path
# starts reading as "quota healthy" -- which is exactly what the old green
# branch did.
#
# The model stays bold and uncoloured: it was the heaviest ink on the line for
# the item that changes least.
loc_green="\033[38;2;122;214;130m"
loc_gold="\033[38;2;232;197;113m"
loc_blue="\033[38;2;122;162;247m"
comment="\033[38;2;98;114;164m"
bold="\033[1m"
reset="\033[0m"

# Codex joins items with " · " and offers no way to change it.
sep=" ${comment}·${reset} "

# Colour by percentage CONSUMED, green -> yellow -> orange -> red.
#
# The whole item takes this colour -- "Context 12% used" is one green band, not a
# dim label wrapped around a bright number. Colouring only the digit made the
# number an isolated bright dot with nothing tying it to its label, so the eye
# had to travel back to read what it meant. One band per item groups them.
#
# These are muted, not the stock Dracula neons (#50FA7B and friends). A whole
# item in #50FA7B is a wall of the brightest thing on screen, and the resting
# state -- green -- is what you look at ~90% of the time, so it has to recede.
# Saturation therefore rises with severity: green is nearly grey-green, red stays
# hot enough to alarm. That gradient is doing real work; don't flatten it by
# "fixing" green to match red's intensity.
pct_color() {
  local val=$1
  if   [ "$val" -ge 80 ]; then printf '\033[38;2;224;108;108m'  # red
  elif [ "$val" -ge 60 ]; then printf '\033[38;2;209;160;114m'  # orange
  elif [ "$val" -ge 40 ]; then printf '\033[38;2;196;190;134m'  # yellow
  else                         printf '\033[38;2;126;176;137m'  # green
  fi
}

# Effort reuses the same scale rather than a second palette -- higher effort
# burns quota faster, so it is the same "how hot is this" question the
# percentages answer, and one source of truth keeps them from drifting apart.
# The numbers are only a way to index pct_color; they are not percentages.
effort_color() {
  case "$1" in
    low)       pct_color 0  ;;
    medium)    pct_color 45 ;;
    high)      pct_color 65 ;;
    xhigh|max) pct_color 85 ;;
    *)         printf '%s' "$comment" ;;
  esac
}

# "<label> N% left" for a quota. Args: label, used_pct
# Displays remaining, but colours by consumed so red still means trouble.
rate_item() {
  local label=$1 used_raw=$2
  [ -z "$used_raw" ] || [ "$used_raw" = "null" ] && return 1
  local used_int left color
  used_int=$(printf '%.0f' "$used_raw")
  left=$((100 - used_int))
  color=$(pct_color "$used_int")
  # Single %, not %%: the caller emits this through printf '%b', which expands
  # backslash escapes but does not treat % as a conversion.
  printf '%b' "${color}${label} ${left}% left${reset}"
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
    git_info="${loc_blue}${branch}${dirty}${reset}"
  fi
  remote_url=$(git remote get-url origin 2>/dev/null)
  if [ -n "$remote_url" ]; then
    remote_url=$(echo "$remote_url" | sed 's|git@github.com:|https://github.com/|; s|\.git$||')
    repo_link="\033]8;;${remote_url}\a${loc_gold}$(basename "$remote_url")${reset}\033]8;;\a"
  fi
fi

# Assemble: dir · repo · branch · context · 5h · weekly · model
line="${loc_green}${dir_path}${reset}"
[ -n "$repo_link" ] && line="${line}${sep}${repo_link}"
[ -n "$git_info" ]  && line="${line}${sep}${git_info}"

ctx_color=$(pct_color "$pct_int")
line="${line}${sep}${ctx_color}Context ${pct_int}% used${reset}"

if item=$(rate_item "5h" "$five_hr"); then
  line="${line}${sep}${item}"
fi
# Labelled "weekly", not "7d", to match what Codex prints for weekly-limit.
if item=$(rate_item "weekly" "$seven_day"); then
  line="${line}${sep}${item}"
fi

# Mirrors Codex's "gpt-5.5 medium", but coloured on the severity scale so the
# line's one colour language covers everything that varies.
line="${line}${sep}${bold}${model_name}${reset}"
if [ -n "$effort" ] && [ "$effort" != "null" ]; then
  line="${line} $(effort_color "$effort")${effort}${reset}"
fi

printf '%b\n' "$line"
