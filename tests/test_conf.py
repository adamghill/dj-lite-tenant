from django_sqlite_tenant.conf import get_conf


def test_get_conf_defaults():
    assert get_conf("APP_LABELS") == {"testapp"}
    assert get_conf("CATALOG_ATTACH_NAME") == "catalog"
    assert get_conf("DB_NAME_PATTERN") == "user_{user_id}.sqlite3"


def test_get_conf_db_dir_set():
    db_dir = get_conf("DB_DIR")
    assert db_dir is not None
