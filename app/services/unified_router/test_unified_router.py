import unittest
from typing import Any

from app.services.unified_router import (
    AllProvidersExhaustedError,
    BaseCapabilityAdapter,
    CapabilityRoutingRule,
    UnifiedRouterConfig,
    UnifiedServiceRouter,
)


class _FakeAdapter(BaseCapabilityAdapter):
    def __init__(self, provider_id: str, caps: frozenset[str], fn) -> None:
        super().__init__(provider_id)
        self._caps = caps
        self._fn = fn

    def supported_capabilities(self) -> frozenset[str]:
        return self._caps

    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        return raw_response

    async def invoke(self, capability_id: str, **params: Any):
        self.assert_supports(capability_id)
        return await self._fn(capability_id, **params)


class UnifiedServiceRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_priority_fallback_second_succeeds(self) -> None:
        calls: list[str] = []

        async def fail_first(cap, **kw):
            calls.append("a")
            raise RuntimeError("boom")

        async def ok_second(cap, **kw):
            calls.append("b")
            return {"ok": True}

        cfg = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(priority=["a", "b"], fallback=True),
            },
        )
        r = UnifiedServiceRouter(cfg)
        r.register_adapter(_FakeAdapter("a", frozenset({"web_search"}), fail_first))
        r.register_adapter(_FakeAdapter("b", frozenset({"web_search"}), ok_second))

        res = await r.execute("web_search", params={"query": "x"})
        self.assertEqual(res.provider_id, "b")
        self.assertEqual(res.data, {"ok": True})
        self.assertEqual(calls, ["a", "b"])

    async def test_preferred_prepended(self) -> None:
        order: list[str] = []

        async def mark(pid: str):
            async def _inner(cap, **kw):
                order.append(pid)
                return pid

            return _inner

        cfg = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(priority=["bocha", "baidu"], fallback=True),
            },
        )
        r = UnifiedServiceRouter(cfg)
        r.register_adapter(_FakeAdapter("bocha", frozenset({"web_search"}), await mark("bocha")))
        r.register_adapter(_FakeAdapter("baidu", frozenset({"web_search"}), await mark("baidu")))

        res = await r.execute(
            "web_search",
            params={},
            preferred_provider="baidu",
            strict_preferred=False,
        )
        self.assertEqual(res.provider_id, "baidu")
        self.assertEqual(order, ["baidu"])

    async def test_strict_preferred_no_fallback(self) -> None:
        async def fail(_cap, **kw):
            raise RuntimeError("no")

        cfg = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(priority=["bocha", "baidu"], fallback=True),
            },
        )
        r = UnifiedServiceRouter(cfg)
        r.register_adapter(_FakeAdapter("bocha", frozenset({"web_search"}), fail))
        r.register_adapter(_FakeAdapter("baidu", frozenset({"web_search"}), fail))

        with self.assertRaises(AllProvidersExhaustedError) as ctx:
            await r.execute(
                "web_search",
                params={},
                preferred_provider="baidu",
                strict_preferred=True,
            )
        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)

    async def test_quota_skips_then_ok(self) -> None:
        async def ok(_c, **kw):
            return 1

        cfg = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(priority=["a", "b"], fallback=True),
            },
        )
        r = UnifiedServiceRouter(cfg)
        r.register_adapter(_FakeAdapter("a", frozenset({"web_search"}), ok))
        r.register_adapter(_FakeAdapter("b", frozenset({"web_search"}), ok))
        r._quota.mark_exhausted("a", "web_search", ttl_seconds=3600)

        res = await r.execute("web_search", params={})
        self.assertEqual(res.provider_id, "b")


if __name__ == "__main__":
    unittest.main()
