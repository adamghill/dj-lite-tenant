from unittest.mock import MagicMock, patch

from dj_lite_tenant import connection_registry


def _clear_registry():
    with connection_registry._lock:
        connection_registry._registry.clear()


def test_touch_adds_alias():
    _clear_registry()
    connection_registry.touch("user_1")

    with connection_registry._lock:
        assert "user_1" in connection_registry._registry


def test_touch_moves_to_end():
    _clear_registry()
    connection_registry.touch("user_1")
    connection_registry.touch("user_2")
    connection_registry.touch("user_1")

    with connection_registry._lock:
        keys = list(connection_registry._registry.keys())
    assert keys == ["user_2", "user_1"]


def test_evict_if_needed_removes_lru():
    _clear_registry()
    connection_registry.touch("user_1")
    connection_registry.touch("user_2")
    connection_registry.touch("user_3")

    with patch.object(connection_registry, "_close_alias") as mock_close:
        connection_registry.evict_if_needed(max_connections=2)
        mock_close.assert_called_once_with("user_1")

    with connection_registry._lock:
        assert "user_1" not in connection_registry._registry
        assert len(connection_registry._registry) == 2


def test_evict_if_needed_no_eviction_when_under_limit():
    _clear_registry()
    connection_registry.touch("user_1")
    connection_registry.touch("user_2")

    with patch.object(connection_registry, "_close_alias") as mock_close:
        connection_registry.evict_if_needed(max_connections=5)
        mock_close.assert_not_called()


def test_evict_multiple():
    _clear_registry()

    for i in range(1, 6):
        connection_registry.touch(f"user_{i}")

    with patch.object(connection_registry, "_close_alias") as mock_close:
        connection_registry.evict_if_needed(max_connections=2)
        assert mock_close.call_count == 3
        evicted = [call.args[0] for call in mock_close.call_args_list]
        assert evicted == ["user_1", "user_2", "user_3"]


def test_remove_clears_alias():
    _clear_registry()
    connection_registry.touch("user_1")
    connection_registry.remove("user_1")

    with connection_registry._lock:
        assert "user_1" not in connection_registry._registry


def test_remove_missing_alias_is_noop():
    _clear_registry()
    connection_registry.remove("user_999")


def test_close_alias_closes_connection_and_removes_from_settings():
    _clear_registry()
    mock_conn = MagicMock()
    mock_connections = {"user_1": mock_conn}
    mock_databases = {"user_1": {}}

    with patch("django.db.connections", mock_connections), patch("django.conf.settings") as mock_settings:
        mock_settings.DATABASES = mock_databases
        connection_registry._close_alias("user_1")

    mock_conn.close.assert_called_once()
    assert "user_1" not in mock_connections
    assert "user_1" not in mock_databases
