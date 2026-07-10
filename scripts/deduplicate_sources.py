# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
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

# Extras to ensure coverage as per user feedback
EXTRA_SOURCES = [
    # Huibq missing vless (guessing path based on structure)
    "https://raw.githubusercontent.com/Huibq/TrojanLinks/master/links/vless",
    # Mohammadgb0078 missing others
    "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/vmess.txt",
    "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/trojan.txt",
    "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/ss.txt",
    # freevpnspy - ensuring both are present
    "https://freevpnspy.raw.githubusercontent.com/2024/08/20240802_novless.yaml",
    "https://freevpnspy.raw.githubusercontent.com/2024/08/20240802_vless.yaml",
    # barry-far/V2ray-Config (Splitted-By-Protocol)
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vmess.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/trojan.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/ss.txt",
    # yebekhe/TelegramV2rayCollector
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vmess",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/trojan",
    # Argh94/V2RayAutoConfig
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Vless.txt",
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Trojan.txt",
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Shadowsocks.txt",
]

USER_ADDED_SOURCES = [
    "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/Movaghat",
    "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/FRAGMENT",
    "https://raw.githubusercontent.com/ThomasJasperthecat/sub/main/sublist1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub3.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub4.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub5.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/masir-sefid/Sub/main/@Masir_Sefid.txt",
    "https://raw.githubusercontent.com/iampedii/whitedns-sub/refs/heads/main/base64.txt",
    "https://sub.iampedi5.live/sub/base64.txt",
    "https://sub.whitedns.one/sub/mihomo.yaml",
    "https://raw.githubusercontent.com/4n0nymou3/multi-proxy-config-fetcher/refs/heads/main/configs/proxy_configs.txt",
    "https://key.zarazaex.xyz/sub",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_1.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_2.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_3.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_4.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_1.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_2.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_3.txt",
    "https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_4.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_SS+All_RUS.txt",
    "https://raw.githubusercontent.com/ShadowException/VPN/refs/heads/main/configs/VPN-cat",
    "https://raw.githubusercontent.com/F0rc3Run/F0rc3Run/main/splitted-by-protocol/vless.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
    "https://raw.githubusercontent.com/MohammadBahemmat/V2ray-Collector/main/subscriptions/all.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
]

SOURCES_DIR = Path("sources")
CONSOLIDATED_FILE = Path("consolidated_sources.txt")
BATCH_PATTERN = "batch_*.txt"
NUM_BATCHES = 17


def _read_url_lines(path: Path) -> Set[str]:
    urls: Set[str] = set()
    if not path.exists():
        return urls
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            urls.add(line)
    return urls


def _project_key(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        parts = [p for p in parsed.path.split("/") if p]
        if host in ("raw.githubusercontent.com", "github.com"):
            if len(parts) >= 2:
                return f"github:{parts[0]}/{parts[1]}"
        if host in ("gitlab.com", "bitbucket.org") and len(parts) >= 2:
            return f"{host}:{parts[0]}/{parts[1]}"
        return host or url
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
        return url


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
        return ""


def main():
    print("Starting Source Deduplication & Restoration...")

    # 1. Gather all existing sources. Batch files are canonical; the
    # consolidated file is a synchronized mirror used by reshard tooling.
    existing_urls: Set[str] = set()
    if SOURCES_DIR.exists():
        for f in SOURCES_DIR.glob(BATCH_PATTERN):
            existing_urls.update(_read_url_lines(f))
    if CONSOLIDATED_FILE.exists():
        existing_urls.update(_read_url_lines(CONSOLIDATED_FILE))

    print(f"Loaded {len(existing_urls)} existing sources.")

    # 2. Identify Domains for New Sources
    new_source_domains = {get_domain(u): u for u in NEW_SOURCES}

    # 3. Filter & Merge
    final_urls: Set[str] = set()

    # Add NEW sources
    for url in NEW_SOURCES:
        final_urls.add(url)

    # Add EXTRA sources
    for url in EXTRA_SOURCES:
        final_urls.add(url)

    # Add USER_ADDED sources
    for url in USER_ADDED_SOURCES:
        final_urls.add(url)

    # Process existing
    dropped_count = 0
    kept_count = 0
    blocked_count = 0

    for url in existing_urls:
        # BLACKLIST: Remove SoroushMirzaei
        if "soroushmirzaei" in url.lower():
            blocked_count += 1
            continue

        domain = get_domain(url)

        # GitHub Logic: Keep all unless explicitly replaced or blacklisted
        if domain == "raw.githubusercontent.com" or domain == "github.com":
            if url not in final_urls:
                final_urls.add(url)
                kept_count += 1
        elif domain in new_source_domains:
            # Domain exists in NEW_SOURCES, use canonical
            if url == new_source_domains[domain]:
                pass
            else:
                dropped_count += 1
        else:
            final_urls.add(url)
            kept_count += 1

    print("Deduplication complete.")
    print(f"  - Dropped {dropped_count} subset/duplicate links.")
    print(f"  - Blocked {blocked_count} dead/blacklisted links.")
    print(f"Final source count: {len(final_urls)}")

    # 4. Redistribute into Batches with project separation
    sorted_urls = sorted(list(final_urls))
    batches: List[List[str]] = [[] for _ in range(NUM_BATCHES)]
    batch_projects = [set() for _ in range(NUM_BATCHES)]
    batch_loads = [0] * NUM_BATCHES

    project_groups = {}
    for url in sorted_urls:
        key = _project_key(url)
        project_groups.setdefault(key, []).append(url)

    for project, items in sorted(
        project_groups.items(), key=lambda x: len(x[1]), reverse=True
    ):
        if len(items) > NUM_BATCHES:
            print(
                f"Warning: Project {project} has {len(items)} links; "
                "some shards will contain more than one link."
            )
        for url in items:
            candidate_batches = [
                i for i in range(NUM_BATCHES) if project not in batch_projects[i]
            ]
            if not candidate_batches:
                candidate_batches = list(range(NUM_BATCHES))
            target = min(candidate_batches, key=lambda i: batch_loads[i])
            batches[target].append(url)
            batch_projects[target].add(project)
            batch_loads[target] += 1

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

    # 6. Update Consolidated File
    CONSOLIDATED_FILE.write_text("\n".join(sorted_urls), encoding="utf-8")

    print(
        f"Written {len(final_urls)} sources to {NUM_BATCHES} batch files and consolidated_sources.txt."
    )


if __name__ == "__main__":
    main()
