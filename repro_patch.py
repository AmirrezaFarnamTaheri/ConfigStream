import asyncio
import asyncio.runners

def patch():
    if not hasattr(asyncio, 'Runner'):
        print("No asyncio.Runner")
        return

    original_run = asyncio.Runner.run
    def new_run(self, coro, *, context=None):
        print("Patched run called")
        return original_run(self, coro, context=context)
    asyncio.Runner.run = new_run

patch()

async def main():
    print("Main running")

try:
    r = asyncio.Runner()
    r.run(main())
except Exception as e:
    print(f"Error: {e}")
