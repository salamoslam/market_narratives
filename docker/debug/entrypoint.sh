#!/bin/sh
set -eu

mkdir -p /run/sshd /home/debugger/.ssh
chown debugger:debugger /home/debugger /home/debugger/.ssh
chmod 700 /home/debugger /home/debugger/.ssh

if [ ! -s /run/secrets/authorized_keys ]; then
  echo "missing authorized_keys" >&2
  exit 1
fi

cp /run/secrets/authorized_keys /home/debugger/.ssh/authorized_keys
chown debugger:debugger /home/debugger/.ssh/authorized_keys
chmod 600 /home/debugger/.ssh/authorized_keys

exec /usr/sbin/sshd -D -e
