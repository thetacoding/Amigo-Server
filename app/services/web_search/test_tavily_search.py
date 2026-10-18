import json
import unittest
from unittest.mock import patch
from urllib import error

from app.services.web_search.tavily_search import TavilyWebSearchService
from app.core.config import settings


class _MockHttpResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TavilyWebSearchServiceTest(unittest.TestCase):
    def test_to_markdown_and_blocks(self):
        raw = {
            "query": "python",
            "answer": "Python is a programming language.",
            "request_id": "req-123",
            "results": [
                {
                    "title": "Python Official",
                    "url": "https://www.python.org",
                    "content": "Python is an interpreted, high-level programming language.",
                    "score": 0.99,
                }
            ],
        }
        blocks = TavilyWebSearchService.to_readable_blocks(raw, content_max_len=20)
        markdown = TavilyWebSearchService.to_markdown(raw, content_max_len=20)

        self.assertEqual(blocks["query"], "python")
        self.assertEqual(len(blocks["results"]), 1)
        self.assertIn("snippet", blocks["results"][0])
        self.assertIn("# Web Search Result", markdown)
        self.assertIn("## Sources", markdown)
        self.assertIn("Python Official", markdown)
        self.assertNotIn("request_id", markdown)

    def test_search_success(self):
        expected = {
            "query": "python",
            "answer": "Python is a programming language.",
            "results": [{"title": "Python", "url": "https://www.python.org"}],
        }

        with patch(
            "app.services.web_search.tavily_search.request.urlopen",
            return_value=_MockHttpResponse(expected),
        ) as mock_urlopen:
            with patch.object(settings, "tavily_api_url", "https://api.tavily.com/search"), patch.object(
                settings, "tavily_timeout_seconds", 20
            ):
                result = TavilyWebSearchService.search("python", api_key="test-key")

        self.assertEqual(result, expected)
        self.assertEqual(mock_urlopen.call_count, 1)
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.full_url, settings.tavily_api_url)
        self.assertEqual(kwargs.get("timeout"), 20)

    def test_search_with_empty_query_raises(self):
        with self.assertRaises(ValueError):
            TavilyWebSearchService.search("   ", api_key="test-key")

    def test_search_without_api_key_raises(self):
        with patch.object(settings, "tavily_api_key", ""):
            with self.assertRaises(ValueError):
                TavilyWebSearchService.search("python")

    def test_search_http_error_raises_runtime_error(self):
        with patch(
            "app.services.web_search.tavily_search.request.urlopen",
            side_effect=error.HTTPError(
                url=settings.tavily_api_url,
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            ),
        ):
            with self.assertRaises(RuntimeError):
                TavilyWebSearchService.search("python", api_key="test-key")

    def test_search_live_integration(self):
        if not settings.tavily_api_key:
            self.skipTest("未配置 TAVILY_API_KEY，跳过联调测试")
        result = TavilyWebSearchService.search("What is Python programming language?")
        print(result)
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)


if __name__ == "__main__":
    unittest.main()
