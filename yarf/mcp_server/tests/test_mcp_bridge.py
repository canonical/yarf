import asyncio
import threading

import pytest

from yarf.mcp_server.bridge import RobotBridge


class TestRobotBridge:
    @pytest.mark.asyncio
    async def test_run_executes_on_serving_thread(self) -> None:
        bridge = RobotBridge()
        serving: dict[str, int] = {}

        def serve() -> None:
            serving["id"] = threading.get_ident()
            bridge.serve()

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            result = await bridge.run(
                lambda a, b: (a + b, threading.get_ident()), 1, 2
            )
        finally:
            bridge.close()
            thread.join()

        assert result == (3, serving["id"])
        assert result[1] != threading.get_ident()

    @pytest.mark.asyncio
    async def test_run_propagates_exceptions(self) -> None:
        bridge = RobotBridge()
        thread = threading.Thread(target=bridge.serve)
        thread.start()

        def fail() -> None:
            raise ValueError("boom")

        try:
            with pytest.raises(ValueError, match="boom"):
                await bridge.run(fail)
            # It keeps serving after a failure
            assert await bridge.run(lambda: "still alive") == "still alive"
        finally:
            bridge.close()
            thread.join()

    @pytest.mark.asyncio
    async def test_run_skips_cancelled_calls(self) -> None:
        bridge = RobotBridge()
        calls = []
        task = asyncio.ensure_future(bridge.run(calls.append, "cancelled"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        thread = threading.Thread(target=bridge.serve)
        thread.start()
        try:
            await bridge.run(calls.append, "executed")
        finally:
            bridge.close()
            thread.join()

        assert calls == ["executed"]

    def test_serve_waits_for_calls(self, monkeypatch) -> None:
        monkeypatch.setattr("yarf.mcp_server.bridge.POLL_INTERVAL", 0.01)
        bridge = RobotBridge()
        thread = threading.Thread(target=bridge.serve)
        thread.start()
        # Lets the queue time out at least once before closing it
        thread.join(0.1)
        assert thread.is_alive()
        bridge.close()
        thread.join(5)
        assert not thread.is_alive()
