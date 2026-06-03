#!/usr/bin/env bash
# Bell Notification Hook — Claude Code Stop + Notification Hook
#
# Plays an audio cue so engineers know when Claude finishes a task
# or needs their attention without having to watch the terminal.
#
# Usage (called by Claude Code automatically):
#   notify-bell.sh stop          — task/response complete
#   notify-bell.sh notification  — Claude needs user input

set -euo pipefail

EVENT="${1:-stop}"

# Play a sound file via afplay (macOS). Falls back to terminal bell.
play_sound() {
    local sound_file="$1"
    if command -v afplay &>/dev/null && [[ -f "$sound_file" ]]; then
        afplay "$sound_file" &>/dev/null &
    else
        tput bel 2>/dev/null || true
    fi
}

case "$EVENT" in
    stop)
        # Task complete — Glass chime: pleasant, non-intrusive
        play_sound "/System/Library/Sounds/Glass.aiff"
        ;;
    notification)
        # Needs attention — Ping: short, distinct, hard to miss
        play_sound "/System/Library/Sounds/Ping.aiff"
        ;;
    *)
        tput bel 2>/dev/null || true
        ;;
esac

exit 0
