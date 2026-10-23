#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
debug_dir="${HOME}/.config/market_narratives_engine/debug"
key_file="${debug_dir}/id_ed25519"
authorized_keys="${debug_dir}/authorized_keys"

mkdir -p "${debug_dir}"
chmod 700 "${debug_dir}"

if [[ ! -f "${key_file}" ]]; then
  ssh-keygen -t ed25519 -f "${key_file}" -N "" -C "market-narratives-debugger"
fi
chmod 600 "${key_file}"
cp "${key_file}.pub" "${authorized_keys}"
chmod 600 "${authorized_keys}"

cd "${root}"
docker compose run --rm --no-deps --user 0 --entrypoint /bin/bash airflow -c 'mkdir -p /opt/airflow/logs && chown 50000:0 /opt/airflow/logs && chmod 755 /opt/airflow/logs'
docker compose up -d --build

echo "ssh -i ${key_file} -p ${DEBUG_SSH_PORT:-2222} debugger@127.0.0.1"
