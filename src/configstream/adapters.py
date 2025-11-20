import json  # noqa: F401
from typing import List, Dict, Any, Optional
from .models import Proxy


def to_clash_proxy(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """
    Converts a Proxy object to a Clash dictionary.
    """
    conf: Dict[str, Any] = {
        "name": proxy.remarks or f"{proxy.protocol.upper()} {proxy.address}",
        "type": proxy.protocol,
        "server": proxy.address,
        "port": proxy.port,
    }

    if proxy.protocol == "vmess":
        conf["uuid"] = proxy.uuid
        conf["alterId"] = int(proxy.details.get("alterId", 0))
        conf["cipher"] = proxy.details.get("scy", "auto")

        is_tls = proxy.details.get("tls") or proxy.details.get("security") == "tls"
        conf["tls"] = bool(is_tls)
        conf["skip-cert-verify"] = True

        if is_tls:
            conf["servername"] = proxy.details.get("sni", "") or proxy.details.get(
                "host", ""
            )

        net = proxy.details.get("net") or proxy.details.get("network")
        if net == "ws":
            conf["network"] = "ws"
            conf["ws-opts"] = {"path": proxy.details.get("path", "/"), "headers": {}}
            if proxy.details.get("host"):
                conf["ws-opts"]["headers"]["Host"] = proxy.details.get("host")
        elif net == "grpc":
            conf["network"] = "grpc"
            conf["grpc-opts"] = {
                "grpc-service-name": proxy.details.get("serviceName", "")
            }
        elif net == "h2":
            conf["network"] = "h2"
            conf["h2-opts"] = {"path": proxy.details.get("path", "/")}

    elif proxy.protocol == "trojan":
        conf["password"] = proxy.uuid
        conf["udp"] = True
        conf["skip-cert-verify"] = True
        conf["sni"] = proxy.details.get("sni", "") or proxy.details.get("peer", "")

    elif proxy.protocol == "vless":
        conf["uuid"] = proxy.uuid
        conf["tls"] = True
        conf["udp"] = True
        conf["skip-cert-verify"] = True
        conf["servername"] = proxy.details.get("sni", "")

        if proxy.details.get("flow"):
            conf["flow"] = proxy.details.get("flow")

        if proxy.details.get("security") == "reality":
            conf["client-fingerprint"] = proxy.details.get("fp", "chrome")
            conf["reality-opts"] = {
                "public-key": proxy.details.get("pbk", ""),
                "short-id": proxy.details.get("sid", ""),
            }

        net = proxy.details.get("type") or proxy.details.get("net")
        if net == "ws":
            conf["network"] = "ws"
            conf["ws-opts"] = {"path": proxy.details.get("path", "/")}
        elif net == "grpc":
            conf["network"] = "grpc"
            conf["grpc-opts"] = {
                "grpc-service-name": proxy.details.get("serviceName", "")
            }

    elif proxy.protocol == "shadowsocks":
        conf["type"] = "ss"
        conf["cipher"] = proxy.details.get("method", "chacha20-ietf-poly1305")
        conf["password"] = proxy.details.get("password", "")

        plugin = proxy.details.get("plugin")
        if plugin:
            conf["plugin"] = plugin
            conf["plugin-opts"] = proxy.details.get("plugin_opts", {})

    elif proxy.protocol == "hysteria2":
        conf["type"] = "hysteria2"
        conf["password"] = proxy.uuid
        conf["sni"] = proxy.details.get("sni", "")
        conf["skip-cert-verify"] = True
        if proxy.details.get("obfs"):
            conf["obfs"] = proxy.details.get("obfs")
            conf["obfs-password"] = proxy.details.get("obfs-password", "")

    elif proxy.protocol == "tuic":
        conf["type"] = "tuic"
        conf["uuid"] = proxy.uuid
        conf["password"] = proxy.details.get("password", "")
        conf["sni"] = proxy.details.get("sni", "")
        conf["skip-cert-verify"] = True

    elif proxy.protocol == "wireguard":
        conf["type"] = "wireguard"
        conf["ip"] = proxy.details.get("ip", "172.16.0.2")
        conf["ipv6"] = proxy.details.get("ipv6", "")
        conf["private-key"] = proxy.details.get("private_key", "")
        conf["public-key"] = proxy.details.get("public_key", "")
        conf["udp"] = True
        if proxy.details.get("reserved"):
            conf["reserved"] = proxy.details.get("reserved")

    else:
        return None

    return conf


def to_singbox_outbound(proxy: Proxy) -> Optional[Dict[str, Any]]:
    """
    Converts a Proxy object to a Sing-box outbound dictionary.
    """
    conf: Dict[str, Any] = {
        "tag": proxy.remarks or f"{proxy.protocol.upper()} {proxy.address}",
        "server": proxy.address,
        "server_port": proxy.port,
    }

    if proxy.protocol == "vmess":
        conf["type"] = "vmess"
        conf["uuid"] = proxy.uuid
        conf["security"] = "auto"

        conf["tls"] = {}
        is_tls = proxy.details.get("tls") or proxy.details.get("security") == "tls"
        if is_tls:
            conf["tls"]["enabled"] = True
            conf["tls"]["insecure"] = True
            conf["tls"]["server_name"] = proxy.details.get(
                "sni", ""
            ) or proxy.details.get("host", "")

        net = proxy.details.get("net") or proxy.details.get("network")
        if net == "ws":
            conf["transport"] = {
                "type": "ws",
                "path": proxy.details.get("path", "/"),
                "headers": {},
            }
            if proxy.details.get("host"):
                conf["transport"]["headers"]["Host"] = proxy.details.get("host")

    elif proxy.protocol == "trojan":
        conf["type"] = "trojan"
        conf["password"] = proxy.uuid
        conf["tls"] = {
            "enabled": True,
            "insecure": True,
            "server_name": proxy.details.get("sni", ""),
        }

    elif proxy.protocol == "vless":
        conf["type"] = "vless"
        conf["uuid"] = proxy.uuid
        conf["flow"] = proxy.details.get("flow", "")
        conf["tls"] = {
            "enabled": True,
            "insecure": True,
            "server_name": proxy.details.get("sni", ""),
        }
        if proxy.details.get("security") == "reality":
            conf["tls"]["reality"] = {
                "enabled": True,
                "public_key": proxy.details.get("pbk", ""),
                "short_id": proxy.details.get("sid", ""),
            }
            if proxy.details.get("fp"):
                conf["tls"]["utls"] = {
                    "enabled": True,
                    "fingerprint": proxy.details.get("fp"),
                }

        net = proxy.details.get("type") or proxy.details.get("net")
        if net == "ws":
            conf["transport"] = {"type": "ws", "path": proxy.details.get("path", "/")}
        elif net == "grpc":
            conf["transport"] = {
                "type": "grpc",
                "service_name": proxy.details.get("serviceName", ""),
            }

    elif proxy.protocol == "shadowsocks":
        conf["type"] = "shadowsocks"
        conf["method"] = proxy.details.get("method", "chacha20-ietf-poly1305")
        conf["password"] = proxy.details.get("password", "")
        # Sing-box SS plugins support is limited/different, typically standard SS is preferred

    elif proxy.protocol == "hysteria2":
        conf["type"] = "hysteria2"
        conf["password"] = proxy.uuid
        conf["tls"] = {
            "enabled": True,
            "insecure": True,
            "server_name": proxy.details.get("sni", ""),
        }
        if proxy.details.get("obfs"):
            conf["obfs"] = {
                "type": "salamander",  # Common H2 obfs
                "password": proxy.details.get("obfs-password", ""),
            }

    elif proxy.protocol == "tuic":
        conf["type"] = "tuic"
        conf["uuid"] = proxy.uuid
        conf["password"] = proxy.details.get("password", "")
        conf["tls"] = {
            "enabled": True,
            "insecure": True,
            "server_name": proxy.details.get("sni", ""),
        }

    elif proxy.protocol == "ssh":
        conf["type"] = "ssh"
        conf["user"] = proxy.uuid
        conf["password"] = proxy.details.get("password", "")
        # host_key, etc.

    else:
        return None

    return conf


class SurgeAdapter:
    @staticmethod
    def generate_conf(proxies: List[Proxy]) -> str:
        lines = [
            "[General]",
            "loglevel = notify",
            "dns-server = system, 8.8.8.8",
            "skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, localhost, *.local",
            "",
            "[Proxy]",
        ]
        names = []
        for i, p in enumerate(proxies):
            name = f"{p.country_code}_{p.protocol.upper()}_{i+1}"
            names.append(name)

            line = f"{name} = {p.protocol}, {p.address}, {p.port}"

            if p.protocol == "vmess":
                line += f", username={p.uuid}"
                if p.details.get("tls"):
                    line += ", tls=true"
                if p.details.get("net") == "ws":
                    line += f", ws=true, ws-path={p.details.get('path', '/')}"

            elif p.protocol == "trojan":
                line += f", password={p.uuid}"
                if p.details.get("sni"):
                    line += f", sni={p.details['sni']}"

            elif p.protocol == "ss":
                line = f"{name} = ss, {p.address}, {p.port}, encrypt-method={p.details.get('method')}, password={p.details.get('password')}"

            elif p.protocol == "snell":
                line = f"{name} = snell, {p.address}, {p.port}, psk={p.details.get('psk')}, version={p.details.get('version', 2)}"

            lines.append(line)

        lines.append("")
        lines.append("[Proxy Group]")
        lines.append(f"Proxy = select, {', '.join(names)}")
        return "\n".join(lines)


class LoonAdapter:
    @staticmethod
    def generate_conf(proxies: List[Proxy]) -> str:
        lines = ["[Proxy]"]
        for i, p in enumerate(proxies):
            name = f"{p.country_code}_{p.protocol}_{i+1}"

            # Base format: Name = Type, Host, Port, ...
            if p.protocol == "vmess":
                line = f"{name} = vmess, {p.address}, {p.port}, username={p.uuid}"
                if p.details.get("net") == "ws":
                    line += f", transport=ws, path={p.details.get('path', '/')}"
                    if p.details.get("host"):
                        line += f", host={p.details['host']}"
                if p.details.get("tls"):
                    line += ", over-tls=true"

            elif p.protocol == "trojan":
                line = f"{name} = trojan, {p.address}, {p.port}, password={p.uuid}"
                if p.details.get("sni"):
                    line += f", sni={p.details['sni']}"

            elif p.protocol == "shadowsocks":
                line = f"{name} = shadowsocks, {p.address}, {p.port}, method={p.details.get('method')}, password={p.details.get('password')}"

            else:
                continue  # Skip unsupported types for Loon for now

            lines.append(line)
        return "\n".join(lines)


class QuantumultXAdapter:
    @staticmethod
    def generate_conf(proxies: List[Proxy]) -> str:
        # Quantumult X uses URIs mostly
        lines = []
        for p in proxies:
            if p.config and "://" in p.config:
                lines.append(p.config)
        return "\n".join(lines)
