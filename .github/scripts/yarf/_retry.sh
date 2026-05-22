# Source this file then call:
#   retry_attempts "<display name>" <max-attempts> <command...>
# The command is invoked up to <max-attempts> times. Emits GitHub Actions
# log annotations (::notice::, ::warning::, ::error::) so retries show up
# in the workflow UI.

retry_attempts() {
  local name=$1
  local max=$2
  shift 2

  for attempt in $(seq 1 "$max"); do
    if "$@"; then
      if [ "$attempt" -gt 1 ]; then
        echo "::notice::$name passed on attempt $attempt/$max"
      fi
      return 0
    fi
    echo "::warning::$name failed on attempt $attempt/$max"
  done

  echo "::error::$name failed after $max attempts"
  return 1
}
