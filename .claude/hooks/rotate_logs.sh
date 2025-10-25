#!/usr/bin/env bash
# Simple log rotation script for KuzuMemory hooks
# Alternative to logrotate for quick manual rotation

set -euo pipefail

LOG_DIR="/tmp"
KEEP_DAYS=7
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

rotate_log() {
    local logfile="$1"
    local basename=$(basename "$logfile")

    if [[ -f "$logfile" ]] && [[ -s "$logfile" ]]; then
        echo "Rotating $logfile..."

        # Compress and rename
        gzip -c "$logfile" > "${logfile}.${TIMESTAMP}.gz"

        # Truncate original
        > "$logfile"

        echo "  Created ${logfile}.${TIMESTAMP}.gz"
    else
        echo "Skipping $logfile (missing or empty)"
    fi
}

cleanup_old_logs() {
    local logfile="$1"
    local count=0

    echo "Cleaning up old rotations of $logfile..."

    # Find and delete logs older than KEEP_DAYS
    while IFS= read -r old_log; do
        rm "$old_log"
        ((count++))
        echo "  Deleted $old_log"
    done < <(find "$LOG_DIR" -name "$(basename "$logfile").*.gz" -mtime +$KEEP_DAYS)

    if [[ $count -eq 0 ]]; then
        echo "  No old logs to clean up"
    else
        echo "  Deleted $count old log(s)"
    fi
}

main() {
    echo "KuzuMemory Hook Log Rotation"
    echo "============================="
    echo "Log directory: $LOG_DIR"
    echo "Keep days: $KEEP_DAYS"
    echo ""

    # Rotate enhance log
    rotate_log "$LOG_DIR/kuzu_enhance.log"
    cleanup_old_logs "$LOG_DIR/kuzu_enhance.log"
    echo ""

    # Rotate learn log
    rotate_log "$LOG_DIR/kuzu_learn.log"
    cleanup_old_logs "$LOG_DIR/kuzu_learn.log"
    echo ""

    echo "Rotation complete!"
    echo ""
    echo "Current logs:"
    ls -lh "$LOG_DIR"/kuzu_*.log* 2>/dev/null || echo "  No logs found"
}

main "$@"
