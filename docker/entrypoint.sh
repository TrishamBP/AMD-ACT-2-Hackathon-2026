#!/bin/sh
set -eu

mkdir -p /output 2>/dev/null || true
chmod 777 /output 2>/dev/null || true

exec python -m src.main "$@"
