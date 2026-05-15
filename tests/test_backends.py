from django_sqlite_tenant.backends.sqlite3.operations import DatabaseOperations
from unittest.mock import MagicMock


def _make_ops():
    connection = MagicMock()
    return DatabaseOperations(connection)


def test_quote_name_plain():
    ops = _make_ops()
    assert ops.quote_name("sometable") == '"sometable"'


def test_quote_name_dotted():
    ops = _make_ops()
    result = ops.quote_name("catalog.movie_movie")
    assert result == '"catalog"."movie_movie"'


def test_quote_name_already_quoted():
    ops = _make_ops()
    result = ops.quote_name('"catalog"."movie_movie"')
    assert '"catalog"."movie_movie"' in result


def test_quote_name_no_double_wrapping():
    ops = _make_ops()
    result = ops.quote_name("catalog.movie_movie")
    assert result.count('"catalog"') == 1
    assert result.count('"movie_movie"') == 1
