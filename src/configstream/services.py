from __future__ import annotations

import logging
from typing import List, Dict, Optional, Any

from rich.progress import Progress

from .models import Proxy
from .performance import PerformanceTracker


logger = logging.getLogger(__name__)


class GeoLocationService:
    def __init__(self, progress: Progress | None, tracker: PerformanceTracker, geo_cache: Dict[str, Dict[str, Optional[str]]]):
        self.progress = progress
        self.tracker = tracker
        self.geo_cache = geo_cache

    async def geolocate_batch(self, batch: List[Proxy], label: str) -> None:
        """
        Geolocate proxies using a robust 2-layer approach:
        Layer 1 (Primary): IP-based lookup using geoip_offline.DEFAULT_RESOLVER
        Layer 2 (Fallback): Remark-based parsing using remark_parser
        """
        if not batch:
            return

        geo_task = (
            self.progress.add_task(f"Geolocating {label}", total=len(batch)) if self.progress else None
        )

        # Import the new geolocation modules
        from . import geoip_offline
        from . import remark_parser

        # Initialize the remark parser (it pre-compiles regexes/maps)
        remark_geo_parser = remark_parser.RemarkGeoParser()

        geo_ip_count = 0
        geo_remark_count = 0

        try:
            with self.tracker.phase("geo"):
                for proxy in batch:
                    # Layer 1: Primary Method (IP-based)
                    # Use the *resolved_ip* from the tester, not proxy.address
                    if proxy.resolved_ip:
                        cached_geo = self.geo_cache.get(proxy.resolved_ip)
                        if cached_geo:
                            proxy.country = cached_geo.get("country") or proxy.country
                            proxy.country_code = (
                                cached_geo.get("country_code") or proxy.country_code
                            )
                            proxy.city = cached_geo.get("city") or proxy.city
                            proxy.asn = cached_geo.get("asn") or proxy.asn
                        else:
                            geo_info = geoip_offline.DEFAULT_RESOLVER.lookup(proxy.resolved_ip)
                            if geo_info.country_code:
                                proxy.country_code = geo_info.country_code
                                proxy.country = (
                                    geo_info.country_code
                                )  # Use code as country for compatibility
                                proxy.asn = geo_info.asn or proxy.asn
                                geo_ip_count += 1

                                # MISSING LINE FROM REPORT ADDED HERE:
                                proxy.org = geo_info.org or ""
                                proxy.isp = geo_info.org or "" # Map org to isp for frontend consistency

                                # Cache the result
                                self.geo_cache[proxy.resolved_ip] = {
                                    "country": proxy.country,
                                    "country_code": proxy.country_code,
                                    "city": proxy.city,
                                    "asn": proxy.asn,
                                    "org": proxy.org # Cache this too
                                }

                    # Layer 2: Fallback Method (Remark-based)
                    # Only run if Layer 1 failed AND we have remarks to parse
                    if not proxy.country_code and proxy.remarks:
                        country_from_remark = remark_geo_parser.parse(proxy.remarks)
                        if country_from_remark:
                            proxy.country_code = country_from_remark
                            proxy.country = country_from_remark
                            geo_remark_count += 1

                    if self.progress and geo_task is not None:
                        self.progress.update(geo_task, advance=1)

            logger.info(
                "Geolocation complete for %s: %d by IP, %d by remark.",
                label,
                geo_ip_count,
                geo_remark_count,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("GeoIP lookup failed during %s: %s", label, exc)
        finally:
            if self.progress and geo_task is not None:
                self.progress.update(geo_task, completed=len(batch))

class ReportGenerator:
    def __init__(self, output_path: str, tracker: PerformanceTracker, all_working_proxies: List[Proxy], all_tested_proxies: List[Proxy], stats: Dict[str, Any], start_time: str, phase_summaries: List[Dict[str, Any]]):
        self.output_path = output_path
        self.tracker = tracker
        self.all_working_proxies = all_working_proxies
        self.all_tested_proxies = all_tested_proxies
        self.stats = stats
        self.start_time = start_time
        self.phase_summaries = phase_summaries
        self.output_files: Dict[str, str] = {}

    def write_outputs(self) -> None:
        try:
            with self.tracker.phase("output"):
                # Apply Aggressive Endpoint Deduplication
                from .filtering import filter_unique_endpoints
                final_proxies = filter_unique_endpoints(self.all_working_proxies)
                final_proxies.sort(key=lambda p: p.latency or float("inf"))

                logger.info(
                    "Filtered %d working proxies down to %d unique endpoints",
                    len(self.all_working_proxies),
                    len(final_proxies),
                )

                # Apply custom tagging
                from .config import AppSettings
                from . import tagging

                app_config = AppSettings()
                if app_config.RENAME_TEMPLATE:
                    tagger = tagging.ProxyTagger(name_template=app_config.RENAME_TEMPLATE)
                    tagger.apply(final_proxies)
                else:
                    from .output import format_proxy_names_with_rank
                    format_proxy_names_with_rank(final_proxies)

                from .output import (
                    generate_base64_subscription,
                    generate_clash_config,
                    generate_singbox_config,
                    generate_shadowrocket_subscription,
                    generate_quantumult_config,
                    generate_surge_config,
                    generate_categorized_outputs,
                )
                import json
                from datetime import datetime, timezone

                sub_content = generate_base64_subscription(final_proxies)
                sub_path = self.output_path / "vpn_subscription_base64.txt"
                sub_path.write_text(sub_content)
                self.output_files["subscription"] = sub_path.name

                clash_content = generate_clash_config(self.all_working_proxies)
                clash_path = self.output_path / "clash.yaml"
                clash_path.write_text(generate_clash_config(final_proxies))
                self.output_files["clash"] = clash_path.name

                (self.output_path / "singbox.json").write_text(generate_singbox_config(final_proxies))
                self.output_files["singbox"] = "singbox.json"

                (self.output_path / "configs_raw.txt").write_text("\n".join(p.config for p in final_proxies))
                self.output_files["raw"] = "configs_raw.txt"

                (self.output_path / "shadowrocket.txt").write_text(generate_shadowrocket_subscription(final_proxies))
                (self.output_path / "quantumult.conf").write_text(generate_quantumult_config(final_proxies))
                (self.output_path / "surge.conf").write_text(generate_surge_config(final_proxies))

                proxies_json = [
                    {
                        "config": p.config, "protocol": p.protocol, "address": p.address, "port": p.port,
                        "latency": p.latency, "country": p.country, "country_code": p.country_code,
                        "city": p.city, "remarks": p.remarks, "is_working": p.is_working,
                        "security_issues": p.security_issues, "tested_at": p.tested_at,
                    }
                    for p in final_proxies
                ]

                json_path = self.output_path / "proxies.json"
                json_path.write_text(json.dumps(proxies_json, indent=2))
                self.output_files["json"] = str(json_path)

                full_dir = self.output_path / "full"
                full_dir.mkdir(parents=True, exist_ok=True)
                full_payload = [
                    {
                        "config": p.config,
                        "protocol": p.protocol,
                        "address": p.address,
                        "port": p.port,
                        "latency": p.latency,
                        "country": p.country,
                        "country_code": p.country_code,
                        "city": p.city,
                        "remarks": p.remarks,
                        "is_working": p.is_working,
                        "security_issues": p.security_issues,
                        "tested_at": p.tested_at,
                    }
                    for p in self.all_tested_proxies
                ]

                full_json_path = full_dir / "all.json"
                full_json_path.write_text(json.dumps(full_payload, indent=2))
                self.output_files["full"] = str(full_json_path)

                success_rate = (
                    (self.stats["working"] / self.stats["tested"]) * 100 if self.stats["tested"] > 0 else 0.0
                )
                success_rate = (len(final_proxies) / self.stats["tested"] * 100) if self.stats["tested"] > 0 else 0.0

                stats_json = {
                    "generated_at": self.start_time,
                    "generated_now": datetime.now(timezone.utc).isoformat(),
                    "total_fetched": self.stats["fetched"],
                    "total_tested": self.stats["tested"],
                    "total_working": len(final_proxies),
                    "success_rate": round(success_rate, 2),
                    "phase_summaries": self.phase_summaries,
                }
                (self.output_path / "statistics.json").write_text(json.dumps(stats_json, indent=2))

                metadata = {
                    "version": "1.1.0",
                    "generated_at": self.start_time,
                    "proxy_count": len(final_proxies),
                    "working_count": len(final_proxies),
                    "stats": stats_json,
                }
                (self.output_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

                self.output_files.update(generate_categorized_outputs(final_proxies, self.output_path))

        except Exception as exc:
            logger.error("Failed to generate outputs: %s", exc)
            raise
