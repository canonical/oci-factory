: "${LOG_LEVEL:=INFO}"

# If RUNNER_DEBUG=1, force DEBUG level
if [ "${RUNNER_DEBUG:-0}" = "1" ]; then
    LOG_LEVEL="DEBUG"
fi

LOG_FILE="/dev/null"  # Or any path you prefer

# ANSI color codes
COLOR_DEBUG="\033[0;32m"   # Green
COLOR_INFO="\033[0;34m"    # Blue
COLOR_WARNING="\033[0;33m"    # Yellow
COLOR_ERROR="\033[0;31m"   # Red
COLOR_RESET="\033[0m"

log() {
    local level="$1"
    local message="$2"
    local timestamp script_name
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    script_name=$(basename "$0")

    # Log level ordering
    declare -A LEVELS=(["DEBUG"]=0 ["INFO"]=1 ["WARNING"]=2 ["ERROR"]=3)
    if [ "${LEVELS[$level]}" -lt "${LEVELS[$LOG_LEVEL]}" ]; then
        return
    fi

    # Set color based on level
    local color
    case "$level" in
        DEBUG) color=$COLOR_DEBUG ;;
        INFO)  color=$COLOR_INFO ;;
        WARNING)  color=$COLOR_WARNING ;;
        ERROR) color=$COLOR_ERROR ;;
        *)     color=$COLOR_RESET ;;
    esac

    local entry="[$timestamp] [$script_name] ${color}[$level]${COLOR_RESET} $message"

    # Print to console
    echo -e "$entry"

    # Strip colors and log to file
    local entry_plain="[$timestamp] [$level] $message"
    echo -e "$entry_plain" >> "$LOG_FILE"
}

log_debug() { log "DEBUG" "$1"; }
log_info()  { log "INFO"  "$1"; }
log_warning()  { log "WARNING"  "$1"; }
log_error() { log "ERROR" "$1"; }
