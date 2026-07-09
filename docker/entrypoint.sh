#!/usr/bin/env sh
set -eu

umask 027

mkdir -p /input /output

if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /input /output /home/app
    exec gosu appuser python -m src.main "$@"
fi

exec python -m src.main "$@"
