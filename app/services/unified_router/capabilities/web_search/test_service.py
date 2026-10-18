import unittest
from typing import Any

from app.services.unified_router import BaseCapabilityAdapter, CapabilityRoutingRule, UnifiedRouterConfig, UnifiedServiceRouter
from app.services.unified_router.capabilities.web_search.service import UnifiedWebSearchService


class _FakeWebAdapter(BaseCapabilityAdapter):
    def __init__(self, provider_id: str, payload: dict[str, Any]):
        super().__init__(provider_id)
        self._payload = payload

    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"web_search"})

    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        return raw_response

    async def invoke(self, capability_id: str, **params: Any) -> dict[str, Any]:
        self.assert_supports(capability_id)
        data = dict(self._payload)
        data["query"] = params.get("query")
        return data


class UnifiedWebSearchServiceTest(unittest.TestCase):
    def test_search_and_markdown(self):
        config = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(priority=["a", "b"], fallback=True),
            }
        )
        router = UnifiedServiceRouter(config)
        router.register_adapter(
            _FakeWebAdapter(
                "a",
                {"results": [{"title": "T1", "url": "https://a", "content": "hello"}]},
            )
        )
        router.register_adapter(
            _FakeWebAdapter(
                "b",
                {"results": [{"title": "T2", "url": "https://b", "content": "world"}]},
            )
        )
        svc = UnifiedWebSearchService(router)
        raw = svc.search("python")
        blocks = svc.to_readable_blocks(raw)
        markdown = svc.to_markdown(raw)

        self.assertEqual(raw["provider"], "a")
        self.assertEqual(blocks["query"], "python")
        self.assertIn("# Web Search Result", markdown)
        self.assertIn("T1", markdown)


if __name__ == "__main__":
    unittest.main()
