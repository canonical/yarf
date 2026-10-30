"""
Run calls on the thread that owns the Robot Framework execution context.

Robot Framework keywords can only run on the thread executing the suite,
while the MCP server needs its own event loop. The bridge queues the
calls made by the server so the Robot thread can run them one at a time.
"""

import asyncio
import queue
from concurrent.futures import Future
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")
# How often the Robot thread wakes up, to let Robot handle signals meanwhile
POLL_INTERVAL = 0.5

Job = tuple[Callable[[], Any], "Future[Any]"]


class RobotBridge:
    """
    Queue of calls to run on the Robot Framework thread.
    """

    def __init__(self) -> None:
        self._jobs: "queue.Queue[Optional[Job]]" = queue.Queue()

    async def run(self, func: Callable[..., T], *args: Any) -> T:
        """
        Run a function on the Robot Framework thread.

        What the function raises is raised here.

        Args:
            func: function to run
            *args: arguments for the function

        Returns:
            what the function returned
        """
        future: "Future[T]" = Future()
        self._jobs.put((lambda: func(*args), future))
        return await asyncio.wrap_future(future)

    def serve(self) -> None:
        """
        Run the queued calls until `close` is called.

        This blocks, and must be called on the Robot Framework thread.
        """
        while True:
            try:
                job = self._jobs.get(timeout=POLL_INTERVAL)
            except queue.Empty:
                continue

            if job is None:
                return

            call, future = job
            if not future.set_running_or_notify_cancel():
                continue

            try:
                future.set_result(call())
            except Exception as e:
                future.set_exception(e)

    def close(self) -> None:
        """
        Stop serving, once the already queued calls are done.
        """
        self._jobs.put(None)
