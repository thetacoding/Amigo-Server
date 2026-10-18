import unittest

from app.services.unified_router.capabilities.web_search.normalizers import (
    normalize_baidu_response,
    normalize_tavily_response,
    normalize_volcengine_response,
)


class WebSearchNormalizersTest(unittest.TestCase):
    def test_normalize_tavily_response(self):
        raw = {
            "query": "python",
            "answer": "ok",
            "request_id": "req-1",
            "results": [{"title": "T1", "url": "https://a", "content": "hello"}],
        }
        result = normalize_tavily_response("tavily", "python", raw)
        self.assertEqual(result.provider, "tavily")
        self.assertEqual(result.request_id, "req-1")
        self.assertEqual(result.results[0].title, "T1")

    def test_normalize_baidu_mock_shape(self):
        raw = {
            "id": "b-1",
            "summary": "sum",
            "data": [{"name": "B1", "link": "https://b", "snippet": "snippet"}],
        }
        result = normalize_baidu_response("baidu", "q", raw)
        self.assertEqual(result.provider, "baidu")
        self.assertEqual(result.request_id, "b-1")
        self.assertEqual(result.results[0].title, "B1")

    def test_normalize_volcengine_mock_shape(self):
        raw = {
            "request_id": "v-1",
            "items": [{"title": "V1", "url": "https://v", "summary": "summary"}],
        }
        result = normalize_volcengine_response("volcengine", "q", raw)
        self.assertEqual(result.provider, "volcengine")
        self.assertEqual(result.request_id, "v-1")
        self.assertEqual(result.results[0].content, "summary")


if __name__ == "__main__":
    unittest.main()
