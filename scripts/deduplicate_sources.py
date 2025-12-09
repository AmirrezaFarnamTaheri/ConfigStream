from pathlib import Path
from urllib.parse import urlparse
from typing import Set, List

# List of new sources provided by the user (Universal/Canonical)
NEW_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http,socks4,socks5&timeout=10000&country=all",
    "https://www.proxyscan.io/download?type=http,https,socks4,socks5",
    "https://www.proxy-list.download/api/v1/get?type=all",
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/",
    "http://spys.one/en/free-proxy-list/",
    "https://openproxy.space/list/http",
    "https://www.proxynova.com/proxy-server-list/",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://www.freeproxylist.net/",
    "https://iproyal.com/free-proxy-list",
    "https://geonode.com/free-proxy-list",
    "https://proxyrack.com/free-proxy-list",
    "https://proxyway.com/free-proxy",
    "https://hidemy.name/en/proxy-list/",
    "https://fresh-proxy-list.net/",
    "http://gatherproxy.com/",
    "http://free-proxy.cz/en/proxylist/main",
    "https://proxylist.to/api/proxy?all=true",
    "https://proxy-daily.com/",
    "https://proxy11.com/api/proxy",
    "http://proxydb.net/",
    "https://www.allfreevpn.com/proxy-list/",
    "https://freeproxy.world/?type=&anonymity=&country=&speed=&port=&uptime=90",
    "https://www.cool-proxy.net/proxies.json",
    "https://www.best-proxy-list.com/",
    "https://raw.githubusercontent.com/rootjazz/proxylist/master/proxylist.txt",
    "https://openproxylist.xyz/all.txt",
    "http://www.freeproxy.win/api/proxy",
    "https://proxapi.co/api/proxy?protocol=all",
    "https://hidemyip.com/proxylist",
    "https://www.bestfreeproxy.com/",
    "https://yip.su/proxy",
    "https://www.my-proxy.com/free-proxy-list.html",
    "https://aliveproxy.com/proxy-list/",
    "https://free.proxynova.com/proxy-list/",
    "https://www.multi-proxy.com/proxylist.php",
    "https://publicproxyservers.com/api/proxy",
    "http://cybersyndrome.net/pla2.html",
    "https://proxychecked.org/",
    "https://netproxylist.com/api/get?list=all",
    "https://www.freeproxyupdate.com/api/proxy",
    "https://proxyhub.me/free-proxy-list",
    "https://proxyspeedy.com/api/all",
    "https://sureproxy.com/free",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/main/http.txt",
    "https://proxifly.dev/api/proxy?format=txt",
    "https://marsproxies.com/free-proxy-list",
    "https://proxymlist.com/freeproxy",
    "https://proxyorbit.com/api/all",
    "https://kproxy.com/proxylist",
    "https://raw.githubusercontent.com/proxyscrape/proxyscrape/master/proxies.json",
    "https://packetstream.io/free-proxy-list",
    "https://noopsproxy.com/api/all",
    "https://scys.org/proxy",
]

SOURCES_DIR = Path("sources")
BATCH_PATTERN = "batch_*.txt"
NUM_BATCHES = 10


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def main():
    print("🚀 Starting Source Optimization...")

    # 1. Gather all existing sources
    existing_urls: Set[str] = set()
    if SOURCES_DIR.exists():
        for f in SOURCES_DIR.glob(BATCH_PATTERN):
            content = f.read_text(encoding="utf-8").splitlines()
            for line in content:
                line = line.strip()
                if line and not line.startswith("#"):
                    existing_urls.add(line)

    print(f"📦 Loaded {len(existing_urls)} existing sources.")

    # 2. Identify Domains for New Sources
    new_source_domains = {get_domain(u): u for u in NEW_SOURCES}

    # 3. Filter Existing Sources
    # Strategy: If we have a new source for a domain, use ONLY that new source.
    # Otherwise, keep the existing source.

    final_urls: Set[str] = set()

    # Add all NEW sources first
    for url in NEW_SOURCES:
        final_urls.add(url)

    # Process existing
    dropped_count = 0
    kept_count = 0

    for url in existing_urls:
        domain = get_domain(url)

        # Special handling for raw.githubusercontent.com
        # We can't treat all github as one domain, so we check the user/repo part?
        # For now, let's treat github as a special case where we DON'T deduplicate by domain unless it matches exactly?
        # Or better: The user's list has some github links (TheSpeedX, rootjazz).
        # If the domain is github, we check if the path overlaps?
        # Actually, the user's instruction "for each domain, keep only one link" is risky for GitHub.
        # "ProxyScrape Github" -> raw.githubusercontent.com/proxyscrape...
        # "JetKai" -> raw.githubusercontent.com/jetkai...
        # These are different "providers" hosted on the same domain.

        if domain == "raw.githubusercontent.com" or domain == "github.com":
            # Keep existing github links unless exact duplicate
            if url not in final_urls:
                final_urls.add(url)
                kept_count += 1
            else:
                # It's already in (exact match)
                pass
        elif domain in new_source_domains:
            # We have a canonical link for this domain in NEW_SOURCES
            # Check if this url is the canonical one
            if url == new_source_domains[domain]:
                pass  # Already added
            else:
                # Drop it! It's likely a subset/duplicate
                # print(f"  - Dropping {url} in favor of {new_source_domains[domain]}")
                dropped_count += 1
        else:
            # Domain not in new list, keep it
            final_urls.add(url)
            kept_count += 1

    print(f"🧹 Deduplication complete. Dropped {dropped_count} subset/duplicate links.")
    print(f"✨ Final source count: {len(final_urls)}")

    # 4. Redistribute into Batches
    # Simple round-robin for now (Dynamic Resharding will optimize later based on timing)
    sorted_urls = sorted(list(final_urls))
    batches: List[List[str]] = [[] for _ in range(NUM_BATCHES)]

    for i, url in enumerate(sorted_urls):
        batches[i % NUM_BATCHES].append(url)

    # 5. Write to files
    SOURCES_DIR.mkdir(exist_ok=True)

    for i, batch in enumerate(batches):
        file_path = SOURCES_DIR / f"batch_{i+1}.txt"
        content = [
            f"# ConfigStream Batch {i+1}",
            f"# Optimized Sources: {len(batch)}",
            "",
        ]
        content.extend(batch)
        file_path.write_text("\n".join(content), encoding="utf-8")

    print(f"💾 Written {len(final_urls)} sources to {NUM_BATCHES} batch files.")


if __name__ == "__main__":
    main()
