#!/bin/bash

# Claude Code status line.
#
#   ~/dotfiles · dotfiles · main* · Opus 5 · high
#   ctx ▰▰▰▱▱▱▱▱▱▱ 34%  ·  5h ▰▰▰▰▱▱▱▱▱▱ 38% ↻3.1h  ·  wk ▰▰▱▱▱▱▱▱▱▱ 19% ↻4.2d
#
# This USED to mirror the Codex CLI status line in ../../codex/config.toml.managed
# item for item, so the two tools read identically. That constraint is now
# deliberately dropped, and the split is the whole design: Codex's status line is
# a fixed list of item ids, so it cannot render a bar, a second line, or a
# different separator -- matching it meant Claude could not either, and a
# percentage alone gives you a number to read rather than a shape to glance at.
# Codex keeps its single flat line; this one takes the two lines it can afford.
# Don't "restore parity" by deleting the bars -- that trade was made on purpose.
#
# Line 1 is where you are, line 2 is how much is left. The split is by kind, not
# by width: nothing on line 1 is a quantity, nothing on line 2 is a place.
#
# Requires: jq

input=$(cat)

model_name="Claude"
effort=""
pct_int=0

if command -v jq &>/dev/null && [ -n "$input" ]; then
  display_name=$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)
  # "Opus 5 (1M context)" -> "Opus 5". The qualifier never changes mid-session,
  # so it is ink spent on the one thing that cannot tell you anything new.
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
  five_hr_resets=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // empty' 2>/dev/null)
  seven_day=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' 2>/dev/null)
  seven_day_resets=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.resets_at // empty' 2>/dev/null)
fi

# Dracula theme (true color).
#
# Hue carries meaning here, so each one gets exactly one job:
#
#   green / gold / blue   where you are -- dir, repo, branch (following Codex)
#   green..red scale      how heavy things are -- meters and effort
#   comment (dim)         separators, empty bar cells, reset countdowns
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

# Line 1 items are single tokens and pack tight. Line 2 items are three-part
# composites (label, bar, number) that run into each other at one space, so they
# get more air. Two separator widths on one screen is a real cost; it buys the
# meters reading as three units instead of nine loose tokens.
sep=" ${comment}·${reset} "
sep2="  ${comment}·${reset}  "

bar_width=10

# Countdowns render on every quota meter that reports a reset time, at any usage.
# They used to stay hidden until 60% (the orange boundary in pct_color) so that
# the countdown APPEARING was itself the signal -- but that made the number you
# most want when deciding whether to start something big ("how long until this
# window rolls over?") the one you could not see until you were already deep into
# the window. A fixed slot you can read at a glance beats a surprise. Severity is
# still carried by the bar and its colour; the countdown is now plain schedule.
# Colour by percentage CONSUMED, green -> yellow -> orange -> red.
#
# These are muted, not the stock Dracula neons (#50FA7B and friends). A whole
# item in #50FA7B is a wall of the brightest thing on screen, and the resting
# state -- green -- is what you look at ~90% of the time, so it has to recede.
# Ten-cell bars multiply that ink three ways over, so this matters MORE here than
# it did when the line was numbers only. Saturation therefore rises with
# severity: green is nearly grey-green, red stays hot enough to alarm. That
# gradient is doing real work; don't flatten it by "fixing" green to match red.
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

# Slim bar. Args: used_pct, colour for the filled run.
#
# Filled cells take the item's severity colour, empty cells stay dim. That is the
# one place the "colour the item whole" rule bends, and it has to: an empty run in
# the item colour reads as filled, and the bar stops being a bar. The label and
# the number still take the severity colour, so the item is a band with a dim
# track through it -- not a dim label wrapped around a bright number, which is
# what left the digit an isolated dot with nothing tying it to its label.
#
# Built by concatenation, not `printf | tr ' ' '▰'`: BSD tr is byte-oriented and
# maps the space onto the FIRST BYTE of a multibyte glyph, which is mojibake.
#
# Fill floors, except that any nonzero usage claims at least one cell -- 4%
# flooring to an empty track would render "barely started" and "not started"
# identically, and those are the two states the bar exists to tell apart.
make_bar() {
  local pct_val=$1 color=$2 filled i out=""
  filled=$((pct_val * bar_width / 100))
  [ "$filled" -lt 1 ] && [ "$pct_val" -gt 0 ] && filled=1
  [ "$filled" -gt "$bar_width" ] && filled=$bar_width
  i=0
  while [ "$i" -lt "$bar_width" ]; do
    # Order matters: at 0% these two conditions both hold at i=0, and the dim
    # one has to win or an empty track renders in the item colour and reads full.
    if   [ "$i" -eq "$filled" ]; then out="${out}${comment}"
    elif [ "$i" -eq 0 ];         then out="${color}"
    fi
    if [ "$i" -lt "$filled" ]; then out="${out}▰"; else out="${out}▱"; fi
    i=$((i + 1))
  done
  printf '%s' "${out}${reset}"
}

# Unix timestamp -> "4.2h" / "23m" / "2.3d".
#
# Integer arithmetic rather than bc: one fractional digit is the most this ever
# shows, and computing it by hand is cheaper than a second hard dependency on a
# script that runs on every render.
time_until() {
  local resets_at=$1 now diff
  now=$(date +%s)
  diff=$((resets_at - now))
  [ "$diff" -le 0 ] && { printf 'now'; return; }
  if [ "$diff" -ge 86400 ]; then
    printf '%d.%dd' $((diff / 86400)) $(((diff % 86400) * 10 / 86400))
  elif [ "$diff" -ge 3600 ]; then
    printf '%d.%dh' $((diff / 3600)) $(((diff % 3600) * 10 / 3600))
  else
    printf '%dm' $((diff / 60))
  fi
}

# "<label> <bar> N%" for one meter, plus a dim "↻2.5h" whenever a reset time is
# known. Args: label, used_pct, resets_at (optional).
#
# Everything reads as CONSUMED now, where the quotas used to read "N% left". A
# bar fills as you spend, so "left" would have pointed the bar and its own number
# in opposite directions -- a track four cells full labelled 62%. Codex says
# "left" and cannot be changed, so this is the wording half of the same split.
meter() {
  local label=$1 used_raw=$2 resets=$3
  [ -z "$used_raw" ] || [ "$used_raw" = "null" ] && return 1
  local used_int color countdown=""
  used_int=$(printf '%.0f' "$used_raw")
  color=$(pct_color "$used_int")

  if [ -n "$resets" ] && [ "$resets" != "null" ]; then
    # Tolerate a fractional timestamp, then reject anything that is not a plain
    # integer, so a payload format change surfaces as a missing countdown rather
    # than as an arithmetic error printed into the status line.
    resets=${resets%%.*}
    case "$resets" in
      '' | *[!0-9]*) ;;
      *) countdown=" ${comment}↻$(time_until "$resets")${reset}" ;;
    esac
  fi

  # Single %, not %%: the caller emits this through printf '%b', which expands
  # backslash escapes but does not treat % as a conversion.
  printf '%b' "${color}${label}${reset} $(make_bar "$used_int" "$color") ${color}${used_int}%${reset}${countdown}"
}

# Line 1: where you are.
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

line1="${loc_green}${dir_path}${reset}"
[ -n "$repo_link" ] && line1="${line1}${sep}${repo_link}"
[ -n "$git_info" ]  && line1="${line1}${sep}${git_info}"

# Codex renders these as one item, "gpt-5.5 medium", because model-with-reasoning
# is a single id and it has no choice. Here they are two, on the same separator
# as everything else on line 1: they are two independent facts (one you picked,
# one you can change mid-session), and joining them with a bare space made the
# effort read as a suffix of the model name. Effort is still coloured on the
# severity scale so the line's one colour language covers everything that varies.
line1="${line1}${sep}${bold}${model_name}${reset}"
if [ -n "$effort" ] && [ "$effort" != "null" ]; then
  line1="${line1}${sep}$(effort_color "$effort")${effort}${reset}"
fi

# Line 2: how much is left. Context first -- it is the one that moves fastest and
# the only one you can actually act on inside a single session.
#
# Labels are clipped to ctx/5h/wk. The bar carries the magnitude now, so the label
# only has to say WHICH meter, and "Context"/"weekly" were paying full width to
# repeat what three characters already identify.
line2=$(meter "ctx" "$pct_int")
if item=$(meter "5h" "$five_hr" "$five_hr_resets"); then
  line2="${line2}${sep2}${item}"
fi
if item=$(meter "wk" "$seven_day" "$seven_day_resets"); then
  line2="${line2}${sep2}${item}"
fi

printf '%b\n%b\n' "$line1" "$line2"
