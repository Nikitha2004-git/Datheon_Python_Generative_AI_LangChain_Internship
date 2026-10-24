from agent.tools.web_search import search_web


class FakeClient:
    def __init__(self, results=None, error=None):
        self.results, self.error = results, error

    def text(self, query, max_results=5):
        if self.error:
            raise self.error
        return self.results


def factory(results=None, error=None):
    return lambda timeout: FakeClient(results, error)


def test_success_formats_results():
    data = [{"title": "Python 9.9 released", "href": "https://example.test/py", "body": "Fake  body\ntext"},
            {"title": "Second", "href": "https://example.test/2", "body": "more"}]
    out = search_web("python", 5, 5, factory(data))
    assert "Python 9.9 released" in out and "https://example.test/py" in out
    assert "Fake body text" in out
    assert "not verified facts" in out


def test_respects_max_results():
    data = [{"title": f"T{i}", "href": f"https://e.test/{i}", "body": "b"} for i in range(10)]
    out = search_web("q", 2, 5, factory(data))
    assert "T0" in out and "T1" in out and "T2" not in out


def test_long_snippet_truncated():
    out = search_web("q", 1, 5, factory([{"title": "t", "href": "u", "body": "x" * 5000}]))
    assert len(out) < 1000 and "..." in out


def test_missing_fields_do_not_crash_or_invent_urls():
    out = search_web("q", 1, 5, factory([{"body": "only body"}]))
    assert "(no title)" in out and "(no URL)" in out and "http" not in out


def test_empty_results():
    assert "No web results" in search_web("zzzz", 5, 5, factory([]))
    assert "No web results" in search_web("zzzz", 5, 5, factory(None))


def test_connection_error_is_friendly():
    out = search_web("q", 5, 5, factory(error=ConnectionError("boom host=secret")))
    assert out.startswith("Web search error") and "internet" in out
    assert "secret" not in out


def test_rate_limit_error():
    class RatelimitException(Exception):
        pass
    assert "rate limit" in search_web("q", 5, 5, factory(error=RatelimitException("202")))


def test_timeout_error():
    assert "timed out" in search_web("q", 5, 5, factory(error=TimeoutError()))


def test_missing_dependency():
    def broken(timeout):
        raise ImportError("no ddgs")
    assert "not installed" in search_web("q", 5, 5, broken)


def test_empty_query():
    assert search_web("   ").startswith("Web search error")
