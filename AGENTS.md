# How to write code here

Reuse a function that already does the job. Add a new one only when no current function fits.

Keep function names clear and short.

Split a hard function into smaller ones, but not too short and call those from it. Each smaller function does one step. The functions shouldn't be 70+ lines long or 3 lines short.

Explain a change in simple English. Keep the explanation short.

# Debug access on the VPS

The only allowed SSH login is user `debugger` on port `2222`. Do not SSH as `deploy` (blocked by passphrase). Do not use `~/.ssh/narratives`, `~/.ssh/ssh_key_one`, or `~/.ssh/ssh_key_two`. Do not use the database owner, `.env`, or the Docker socket.

The private key is `~/.config/market_narratives_engine/debug/id_ed25519` on the Mac. The tunnel must forward port `2222`.

```bash
ssh -i ~/.config/market_narratives_engine/debug/id_ed25519 -p 2222 debugger@127.0.0.1
```

Inside that shell, read `/opt/airflow/logs` and call `http://airflow:8080/health` and `http://superset:8088/health`. That shell cannot reach Postgres.

Prod SQL from the Mac is `make db-query-prod`. It reads `.env.readonly` only and the session is read-only.
