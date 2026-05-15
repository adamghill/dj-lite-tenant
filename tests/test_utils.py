import os


from django_sqlite_tenant.utils import (
    delete_user_db,
    get_user_db_alias,
    get_user_db_path,
    setup_user_db,
)


def test_get_user_db_alias():
    assert get_user_db_alias(42) == "user_42"


def test_get_user_db_path_contains_user_id():
    path = get_user_db_path(99)
    assert "user_99" in path
    assert path.endswith(".sqlite3")


def test_setup_and_delete_user_db(allow_all_databases):
    user_id = 1001
    result = setup_user_db(user_id)
    assert result is True

    path = get_user_db_path(user_id)
    assert os.path.exists(path)

    deleted = delete_user_db(user_id)
    assert deleted is True
    assert not os.path.exists(path)
