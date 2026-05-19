# Locust Load Tests

Realistic HTTP load tests for `dj-lite-tenant` using [Locust](https://locust.io).
Targets the **example** Django app and measures tenant read/write throughput.

## Quick start

### 1. Install the `load-test` extras

```bash
uv sync --extra load-test
```

### 2. Set up the example app and seed users

```bash
just migrate
just locust-setup
```

`locust/setup.py` creates 10 test users (`locustuser1` … `locustuser10`) and
provisions their per-tenant SQLite databases via the `post_save` signal.

### 3. Start the server

For realistic concurrency testing use gunicorn (recommended for load tests):

```bash
just serve-gunicorn
```

Or use Django's dev server for quick smoke-testing (single-threaded):

```bash
just serve
```

### 4. Run Locust

**Interactive web UI** (open http://localhost:8089 after starting):

```bash
just locust
```

**Headless / CI mode** (10 users, 2 users/s spawn rate, 60-second run):

```bash
just locust --headless --users 10 --spawn-rate 2 --run-time 60s
```

## User classes

| Class | Weight | Behaviour |
|---|---|---|
| `TenantReadUser` | 3× | Logs in once, repeatedly GETs `/` (notes list) |
| `TenantWriteUser` | 1× | Logs in once, 3:1 mix of GET `/` and POST `/notes/add/` |

## Configuration

Edit the constants at the top of `locustfile.py` / `setup.py` to change the
number of users or password:

```python
NUM_USERS = 10        # must match --users (or fewer)
USER_PASSWORD = "locustpass123"
```
