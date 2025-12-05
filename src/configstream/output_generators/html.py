from typing import List, Dict, Any
import logging

from ..models import Proxy

logger = logging.getLogger(__name__)


def generate_html_listing(proxies: List[Proxy]) -> str:
    """
    Generates a simple HTML table of proxies for debugging/human viewing.
    """
    rows = []
    for p in proxies:
        if not p.is_working:
            continue

        status_color = "green" if p.is_working else "red"
        latency = p.latency if p.latency else "N/A"

        row = f"""
        <tr>
            <td>{p.protocol.upper()}</td>
            <td>{p.country_code}</td>
            <td>{latency} ms</td>
            <td style="color: {status_color}">{"Online" if p.is_working else "Offline"}</td>
            <td><code style="display:block; width: 200px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">{p.config}</code></td>
        </tr>
        """
        rows.append(row)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy Listing</title>
        <style>
            body {{ font-family: sans-serif; background: #111; color: #eee; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #333; text-align: left; }}
            th {{ background: #222; }}
            code {{ background: #222; padding: 2px 5px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>Proxy Listing ({len(rows)} Working)</h1>
        <table>
            <thead>
                <tr>
                    <th>Protocol</th>
                    <th>Country</th>
                    <th>Latency</th>
                    <th>Status</th>
                    <th>Config</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </body>
    </html>
    """
    return html
