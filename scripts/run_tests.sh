#!/usr/bin/env bash
set -euo pipefail

CATEGORY=""
DEVICE_HOST=""
MOCK=false
OUTPUT_XML="test-results.xml"
EXTRA_ARGS=""

usage() {
  echo "Usage: $0 [--category boot|sensor_io|data_integrity] [--device-host HOST] [--mock] [--output FILE]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --category) CATEGORY="$2"; shift 2 ;;
    --device-host) DEVICE_HOST="$2"; shift 2 ;;
    --mock) MOCK=true; shift ;;
    --output) OUTPUT_XML="$2"; shift 2 ;;
    --) shift; EXTRA_ARGS="$*"; break ;;
    *) usage ;;
  esac
done

if $MOCK || [[ -z "$DEVICE_HOST" ]]; then
  export MOCK_DEVICE=true
  echo "Running in MOCK device mode"
else
  export DEVICE_HOST="$DEVICE_HOST"
  export MOCK_DEVICE=false
  echo "Running against device: $DEVICE_HOST"
fi

TEST_PATH="tests/"
MARKER_ARGS=""
if [[ -n "$CATEGORY" ]]; then
  TEST_PATH="tests/${CATEGORY}/"
  MARKER_ARGS="-m ${CATEGORY}"
  echo "Running category: $CATEGORY"
fi

echo "Output: $OUTPUT_XML"
echo "---"

pytest "$TEST_PATH" \
  --tb=short \
  --junitxml="$OUTPUT_XML" \
  -v \
  $MARKER_ARGS \
  $EXTRA_ARGS

EXIT_CODE=$?

if [[ -n "${PORTAL_URL:-}" && -n "${PORTAL_TOKEN:-}" ]]; then
  echo "Posting results to portal..."
  python scripts/post_results.py --xml "$OUTPUT_XML"
fi

exit $EXIT_CODE
