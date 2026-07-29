#!/bin/bash
# Extract executable commands from README files
# Outputs JSON with grouped commands for Claude to present

set -e

# Find README file
find_readme() {
    for name in README.md README readme.md readme.txt README.txt; do
        if [[ -f "$1/$name" ]]; then
            echo "$1/$name"
            return 0
        fi
    done
    return 1
}

# Extract fenced code blocks with bash/sh/shell/zsh markers
extract_fenced_blocks() {
    local file="$1"
    awk '
    /^```(bash|sh|shell|zsh|console)/ {
        in_block=1
        lang=$0
        gsub(/^```/, "", lang)
        next
    }
    /^```$/ && in_block {
        in_block=0
        next
    }
    in_block {
        # Skip comments and empty lines for cleaner output
        if ($0 !~ /^[[:space:]]*#/ && $0 !~ /^[[:space:]]*$/) {
            print $0
        }
    }
    ' "$file"
}

# Extract inline commands (backticks starting with common CLI tools)
extract_inline_commands() {
    local file="$1"
    grep -oE '`(npm|yarn|pnpm|pip|cargo|brew|apt|apt-get|make|docker|docker-compose|git|curl|wget|go|poetry|bundle|gem|composer|mvn|gradle|kubectl|terraform|ansible)[^`]+`' "$file" 2>/dev/null | \
        sed 's/^`//; s/`$//' | \
        sort -u
}

# Detect command purpose based on keywords
detect_purpose() {
    local cmd="$1"
    case "$cmd" in
        *install*|*add*|*init*|*setup*|*create*) echo "setup" ;;
        *build*|*compile*) echo "build" ;;
        *test*|*spec*|*check*) echo "test" ;;
        *start*|*run*|*serve*|*dev*) echo "run" ;;
        *lint*|*format*|*prettier*|*eslint*) echo "lint" ;;
        *deploy*|*push*|*publish*) echo "deploy" ;;
        *clean*|*reset*|*rm*|*remove*) echo "cleanup" ;;
        *) echo "other" ;;
    esac
}

# Main
dir="${1:-.}"
readme=$(find_readme "$dir")

if [[ -z "$readme" ]]; then
    echo "ERROR: No README file found in $dir"
    exit 1
fi

echo "=== README: $readme ==="
echo ""

# Extract and display fenced commands
echo "=== FENCED CODE BLOCKS (bash/sh/shell/zsh) ==="
fenced=$(extract_fenced_blocks "$readme")
if [[ -n "$fenced" ]]; then
    echo "$fenced"
else
    echo "(none found)"
fi
echo ""

# Extract and display inline commands
echo "=== INLINE COMMANDS ==="
inline=$(extract_inline_commands "$readme")
if [[ -n "$inline" ]]; then
    echo "$inline"
else
    echo "(none found)"
fi
echo ""

# Group commands by purpose
echo "=== COMMANDS BY PURPOSE ==="
all_commands=$(echo -e "${fenced}\n${inline}" | grep -v "^$" | sort -u)
if [[ -n "$all_commands" ]]; then
    for purpose in setup build test run lint deploy cleanup other; do
        matches=""
        while IFS= read -r cmd; do
            [[ -z "$cmd" ]] && continue
            if [[ "$(detect_purpose "$cmd")" == "$purpose" ]]; then
                matches+="  - $cmd"$'\n'
            fi
        done <<< "$all_commands"
        if [[ -n "$matches" ]]; then
            echo "[$purpose]"
            echo -n "$matches"
        fi
    done
else
    echo "(no commands extracted)"
fi
