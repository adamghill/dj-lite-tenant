import? 'adamghill.justfile'
import? '../dotfiles/just/justfile'

src := "src/dj_lite_tenant"

# List commands
_default:
    just --list --unsorted --justfile {{ justfile() }} --list-heading $'Available commands:\n'

# Grab default `adamghill.justfile` from GitHub
fetch:
  curl https://raw.githubusercontent.com/adamghill/dotfiles/master/just/justfile > adamghill.justfile

# Run the dev server for the example project (uses runserver, single-threaded)
serve:
  -uv run --all-extras example/manage.py runserver 0:8049

# Run gunicorn for load testing (better concurrency handling)
serve-gunicorn:
  -cd example && uv run --extra load-test gunicorn project.wsgi:application -b 0.0.0.0:8049 -w 2 --threads 2 --worker-class gthread

migrate:
  -uv run --all-extras example/manage.py migrate
  -uv run --all-extras example/manage.py migrate_tenant_dbs

dance:
  -uv run --all-extras example/manage.py makemigrations
  just migrate

# Run only integration tests (concurrency, signals, management commands, etc.)
test-integration:
  uv run pytest -m integration --override-ini="addopts="

# Run pytest-benchmark microbenchmarks
benchmark:
  uv run pytest tests/test_benchmarks.py --benchmark-only -v --override-ini="addopts="

# Seed the example app with load-test users (run once before `locust`)
locust-setup:
  uv run --all-extras locust/setup.py

# Run Locust load tests against the example app (requires `just serve` running)
locust *args:
  uv run --extra load-test locust -f locust/locustfile.py --host http://localhost:8049 {{ args }}
