#!/bin/sh
set -eu

umask 027

mkdir -p /output

if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /output /home/app 2>/dev/null || true
    exec gosu appuser python -m src.main "$@"
fi

exec python -m src.main "$@"
