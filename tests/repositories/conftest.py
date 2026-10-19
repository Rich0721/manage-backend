import asyncio
import selectors
import sys
from collections.abc import Callable
from collections.abc import Mapping

import pytest


EventLoopFactory = Callable[[], asyncio.AbstractEventLoop]


def _create_selector_event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> Mapping[str, EventLoopFactory]:
    if sys.platform == "win32":
        return {"selector": _create_selector_event_loop}
    return {"default": asyncio.new_event_loop}
