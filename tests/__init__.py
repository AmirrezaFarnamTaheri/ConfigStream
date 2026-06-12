# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import os
import nest_asyncio

# Ensure TLS-related tests do not inherit a broken SSL_CERT_FILE/SSL_CERT_DIR
# from the host environment. httpx reads these via trust_env=True by default.
_ssl_cert_file = os.environ.get("SSL_CERT_FILE")
if _ssl_cert_file and not os.path.exists(_ssl_cert_file):
    os.environ.pop("SSL_CERT_FILE", None)

_ssl_cert_dir = os.environ.get("SSL_CERT_DIR")
if _ssl_cert_dir and not os.path.isdir(_ssl_cert_dir):
    os.environ.pop("SSL_CERT_DIR", None)

if not os.environ.get("SSL_CERT_FILE"):
    try:
        import certifi  # type: ignore[import-untyped]

        os.environ["SSL_CERT_FILE"] = certifi.where()
    except Exception:
        # Fallback to system trust when certifi is unavailable.
        pass

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

        # Bind original_run per-iteration: a plain closure would make every
        # patched_run delegate to the LAST runner's original implementation
        # when more than one Runner class is patched.
        def patched_run(self, coro, *, context=None, original_run=original_run):
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
