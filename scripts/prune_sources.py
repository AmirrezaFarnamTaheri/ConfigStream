import logging
import asyncio
import httpx
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SOURCES_DIR = Path("sources")
TIMEOUT = 10.0
MAX_CONCURRENT_CHECKS = 20


async def check_url(client, url):
    def _redact(u: str) -> str:
        # Minimal log redaction: drop query string to avoid leaking tokens
        return u.split("?", 1)[0]

    try:
        response = await client.head(url, timeout=TIMEOUT, follow_redirects=True)

        # HEAD is often blocked; retry with a lightweight GET before declaring dead.
        if response.status_code in (403, 405, 501):
            response = await client.get(
                url,
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={"Range": "bytes=0-0"},
            )

        if response.status_code in (404, 403, 410):
            logger.warning(f"Dead URL found ({response.status_code}): {_redact(url)}")
            return url, response.status_code
        return url, 200
    except Exception as e:
        logger.warning(f"Error checking {_redact(url)}: {e}")
        # Treat connection errors as potentially temporary
        return url, 0


async def prune_sources():
    if not SOURCES_DIR.exists():
        logger.error(f"Sources directory {SOURCES_DIR} not found.")
        return

    dead_urls = set()
    all_urls = set()
    # [FIX] Use recursive glob to capture all .txt files in root and subdirectories
    # The 'or' operator previously short-circuited if root had files, ignoring subdirs.
    files_to_process = list(SOURCES_DIR.rglob("*.txt"))

    if not files_to_process:
        logger.info("No source files found.")
        return

    logger.info(f"Scanning {len(files_to_process)} source files...")

    # 1. Collect all URLs
    file_map = {}  # url -> list of files containing it

    for file_path in files_to_process:
        try:
            content = file_path.read_text(encoding="utf-8")
            urls = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("http")
            ]
            for url in urls:
                all_urls.add(url)
                if url not in file_map:
                    file_map[url] = []
                file_map[url].append(file_path)
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")

    logger.info(f"Found {len(all_urls)} unique URLs to check.")

    # 2. Check URLs
    async with httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=MAX_CONCURRENT_CHECKS,
            max_keepalive_connections=MAX_CONCURRENT_CHECKS,
        ),
        headers={"User-Agent": "ConfigStream/PruneSources"},
    ) as client:
        sem = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)

        async def bounded_check(url):
            async with sem:
                return await check_url(client, url)

        tasks = [asyncio.create_task(bounded_check(url)) for url in all_urls]

        results = []
        for fut in asyncio.as_completed(tasks):
            results.append(await fut)

        for url, status in results:
            if status in (404, 403, 410):
                dead_urls.add(url)

    logger.info(f"Found {len(dead_urls)} dead URLs to remove.")

    if not dead_urls:
        return

    # 3. Remove Dead URLs from files
    for file_path in files_to_process:
        try:
            original_content = file_path.read_text(encoding="utf-8")
            lines = original_content.splitlines()
            new_lines = []
            modified = False

            for line in lines:
                stripped = line.strip()
                if stripped in dead_urls:
                    logger.info(f"Removing {stripped} from {file_path}")
                    modified = True
                else:
                    new_lines.append(line)

            if modified:
                file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                logger.info(f"Updated {file_path}")

        except Exception as e:
            logger.error(f"Failed to update {file_path}: {e}")


if __name__ == "__main__":
    asyncio.run(prune_sources())
