# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import nest_asyncio
import sys

# Apply nest_asyncio logic via Runner patching
# This patches asyncio.Runner.run (and backports) to allow nested execution
# if a loop is already running.

def patch_runner_run():
    runners_to_patch = []

    # Python 3.11+
    if hasattr(asyncio, "Runner"):
        runners_to_patch.append(asyncio.Runner)

    # Backports (used by pytest-asyncio on Py3.10)
    try:
        import backports.asyncio.runner.runner
        runners_to_patch.append(backports.asyncio.runner.runner.Runner)
    except ImportError:
        pass

    for RunnerClass in runners_to_patch:
        if getattr(RunnerClass, "_patched_by_configstream", False):
            continue

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
        RunnerClass._patched_by_configstream = True

patch_runner_run()
