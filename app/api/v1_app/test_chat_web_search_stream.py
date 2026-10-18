import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _FakeChunk:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self):
        self.last_messages = None

    def bind(self, **kwargs):
        return self

    async def astream(self, messages):
        self.last_messages = messages
        yield _FakeChunk("hello ")
        yield _FakeChunk("world")

    async def ainvoke(self, messages):
        self.last_messages = messages
        return _FakeChunk("hello world")


class ChatWebSearchStreamTest(unittest.TestCase):
    def test_stream_contains_web_search_frame(self):
        client = TestClient(app)
        fake_llm = _FakeLLM()
        req_body = {
            "sessionInfo": {"session_id": "s1", "interaction_id": "i1"},
            "userInfo": {"user_id": "u1"},
            "DeviceInfo": {"device_id": "d1"},
            "AppBaseInfo": {"package_name": "pkg"},
            "SystemSetting": {"gps": "0,0"},
            "messages": [{"role": "user", "content": "python 是什么"}],
            "streaming": True,
            "reasoning": False,
            "options": {
                "temperature": 0.7,
                "web_search_enabled": True,
                "web_search_format": "blocks",
                "systemPrompt": "你是一个知识助手",
            },
        }

        fake_raw = {
            "query": "python 是什么",
            "answer": "Python 是编程语言",
            "request_id": "req-1",
            "results": [{"title": "Python", "url": "https://python.org", "content": "desc", "score": 0.9}],
        }

        with patch("app.api.v1_app.chat.LLMFactory.get_model", return_value=fake_llm), patch(
            "app.api.v1_app.chat.TavilyWebSearchService.search", return_value=fake_raw
        ):
            with client.stream("POST", "/api/v1_app/chat/completions", json=req_body) as resp:
                body = "".join([chunk.decode("utf-8") for chunk in resp.iter_raw()])

        self.assertEqual(resp.status_code, 200)
        self.assertIn("web_search_completed", body)
        self.assertIn("\"result_count\":1", body)
        self.assertIn("\"event\":\"text\"", body)
        self.assertIsNotNone(fake_llm.last_messages)
        self.assertIn("端侧 SystemPrompt", fake_llm.last_messages[0].content)
        self.assertIn("WebSearch", fake_llm.last_messages[0].content)
        self.assertIn("你是一个知识助手", fake_llm.last_messages[0].content)

    def test_stream_skips_llm_when_request_llm_false(self):
        client = TestClient(app)
        req_body = {
            "sessionInfo": {"session_id": "s1", "interaction_id": "i1"},
            "userInfo": {"user_id": "u1"},
            "DeviceInfo": {"device_id": "d1"},
            "AppBaseInfo": {"package_name": "pkg"},
            "SystemSetting": {"gps": "0,0"},
            "messages": [{"role": "user", "content": "python 是什么"}],
            "streaming": True,
            "reasoning": False,
            "options": {
                "web_search_enabled": True,
                "request_llm": False,
            },
        }
        fake_raw = {
            "query": "python 是什么",
            "answer": "Python 是编程语言",
            "request_id": "req-2",
            "results": [{"title": "Python", "url": "https://python.org", "content": "desc", "score": 0.9}],
        }

        with patch("app.api.v1_app.chat.LLMFactory.get_model") as mock_get_model, patch(
            "app.api.v1_app.chat.TavilyWebSearchService.search", return_value=fake_raw
        ):
            with client.stream("POST", "/api/v1_app/chat/completions", json=req_body) as resp:
                body = "".join([chunk.decode("utf-8") for chunk in resp.iter_raw()])

        self.assertEqual(resp.status_code, 200)
        self.assertIn("# Web Search Result", body)
        self.assertIn("\"event\":\"done\"", body)
        self.assertIn("llm_skipped", body)
        mock_get_model.assert_not_called()

    def test_stream_web_search_markdown_in_content_not_extra(self):
        client = TestClient(app)
        fake_llm = _FakeLLM()
        req_body = {
            "sessionInfo": {"session_id": "s1", "interaction_id": "i1"},
            "userInfo": {"user_id": "u1"},
            "DeviceInfo": {"device_id": "d1"},
            "AppBaseInfo": {"package_name": "pkg"},
            "SystemSetting": {"gps": "0,0"},
            "messages": [{"role": "user", "content": "python 是什么"}],
            "streaming": True,
            "reasoning": False,
            "options": {
                "web_search_enabled": True,
                "web_search_format": "both",
            },
        }
        fake_raw = {
            "query": "python 是什么",
            "answer": "Python 是编程语言",
            "request_id": "req-3",
            "results": [{"title": "Python", "url": "https://python.org", "content": "desc", "score": 0.9}],
        }

        with patch("app.api.v1_app.chat.LLMFactory.get_model", return_value=fake_llm), patch(
            "app.api.v1_app.chat.TavilyWebSearchService.search", return_value=fake_raw
        ):
            with client.stream("POST", "/api/v1_app/chat/completions", json=req_body) as resp:
                body = "".join([chunk.decode("utf-8") for chunk in resp.iter_raw()])

        self.assertEqual(resp.status_code, 200)
        self.assertIn("# Web Search Result", body)
        self.assertIn("\"web_search\":", body)
        self.assertNotIn("\"markdown\":", body)


if __name__ == "__main__":
    unittest.main()
