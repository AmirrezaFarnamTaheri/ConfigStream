import pytest
import asyncio
import nest_asyncio
import sys

# Apply nest_asyncio globally
nest_asyncio.apply()

# Aggressive patching of Runner.run to handle reentrancy
def patch_runner_run():
    runners_to_patch = []

    # Python 3.11+
    if hasattr(asyncio, "Runner"):
        runners_to_patch.append(asyncio.Runner)

    # Backports
    try:
        import backports.asyncio.runner.runner
        runners_to_patch.append(backports.asyncio.runner.runner.Runner)
    except ImportError:
        pass

    for RunnerClass in runners_to_patch:
        original_run = RunnerClass.run

        def patched_run(self, coro, *, context=None):
            try:
                # Check if ANY loop is running
                asyncio.get_running_loop()
                # If we get here, a loop is running.
                # Runner.run would normally raise RuntimeError.
                # We bypass it and use the runner's loop directly.
                loop = self.get_loop()
                # Ensure this specific loop is patched for reentrancy
                nest_asyncio.apply(loop)
                return loop.run_until_complete(coro)
            except RuntimeError:
                # No running loop, safe to delegate to original implementation
                return original_run(self, coro, context=context)

        RunnerClass.run = patched_run

patch_runner_run()

@pytest.fixture(scope="function")
def event_loop():
    """
    Create an instance of the default event loop for each test.
    """
    loop = asyncio.new_event_loop()
    nest_asyncio.apply(loop)
    yield loop
    loop.close()

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
