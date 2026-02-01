import pytest
import asyncio
import os
import nest_asyncio

# Apply nest_asyncio globally for all tests to support nested event loops
# (e.g. running pytest from inside an existing loop, or tests calling asyncio.run)
nest_asyncio.apply()

# Manually patch Runner.run to support nested loops with nest_asyncio
# This is required because nest_asyncio does not patch asyncio.Runner.run (or backports)
def patch_runner_for_nest_asyncio():
    try:
        # Check if Runner exists (Python 3.11+)
        if hasattr(asyncio, "Runner"):
            original_run = asyncio.Runner.run

            def patched_run(self, coro, *, context=None):
                # If loop is already running, use run_until_complete
                loop = self.get_loop()
                if loop.is_running():
                    # nest_asyncio patched loop.run_until_complete handles reentrancy
                    return loop.run_until_complete(coro)
                else:
                    return original_run(self, coro, context=context)

            asyncio.Runner.run = patched_run
    except Exception:
        pass

# Apply the patch immediately
patch_runner_for_nest_asyncio()

@pytest.fixture(scope="function")
def isolate_asyncio():
    """
    Fixture to isolate asyncio loop for a test.
    Useful if a test modifies loop state significantly.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
    yield loop
    loop.close()
