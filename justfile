import? 'adamghill.justfile'
import? '../dotfiles/just/justfile'

src := "src/dj_lite_tenant"

# List commands
_default:
    just --list --unsorted --justfile {{ justfile() }} --list-heading $'Available commands:\n'

# Grab default `adamghill.justfile` from GitHub
fetch:
  curl https://raw.githubusercontent.com/adamghill/dotfiles/master/just/justfile > adamghill.justfile

# Run the dev server for the example project
serve:
  -uv run --all-extras example/manage.py runserver 0:8049

migrate:
  -uv run --all-extras example/manage.py migrate
  -uv run --all-extras example/manage.py migrate_tenant_dbs

dance:
  -uv run --all-extras example/manage.py makemigrations
  just migrate
