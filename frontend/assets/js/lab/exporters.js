// ConfigStream Laboratory - Exporters
// SPDX-License-Identifier: AGPL-3.0-or-later

import { WARP_PUBLIC_KEY } from './state.js';

export function singboxOutboundToClash(sbOut) {
    const t = sbOut.type;
    const name = sbOut.tag;
    const tls = sbOut.tls || {};
    const transport = sbOut.transport || {};
    const sni = tls.server_name || sbOut.server || '';

    function transportLines() {
        const tType = transport.type || '';
        let lines = '';
        if (tType === 'ws') {
            lines += `\n    network: ws\n    ws-opts:\n      path: ${transport.path || '/'}`;
            if (transport.headers && transport.headers.Host) lines += `\n      headers:\n        Host: ${transport.headers.Host}`;
        } else if (tType === 'grpc') {
            lines += `\n    network: grpc\n    grpc-opts:\n      grpc-service-name: ${transport.service_name || ''}`;
        } else if (tType === 'http') {
            lines += `\n    network: h2\n    h2-opts:\n      path: ${transport.path || '/'}`;
            if (transport.host) lines += `\n      host:\n        - ${transport.host}`;
        } else if (tType === 'httpupgrade') {
            lines += `\n    network: ws\n    ws-opts:\n      path: ${transport.path || '/'}\n      v2ray-http-upgrade: true`;
        }
        if (tls.utls && tls.utls.fingerprint) lines += `\n    client-fingerprint: ${tls.utls.fingerprint}`;
        if (tls.alpn && tls.alpn.length) lines += `\n    alpn:\n${tls.alpn.map(a => '      - ' + a).join('\n')}`;
        return lines;
    }

    function realityLines() {
        if (tls.reality && tls.reality.enabled) {
            let r = `\n    reality-opts:\n      public-key: ${tls.reality.public_key || ''}`;
            if (tls.reality.short_id) r += `\n      short-id: ${tls.reality.short_id}`;
            return r;
        }
        return '';
    }

    if (t === 'vless') {
        let block = `  - name: "${name}"\n    type: vless\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    uuid: ${sbOut.uuid || ''}\n    tls: true\n    servername: ${sni}`;
        if (sbOut.flow) block += `\n    flow: ${sbOut.flow}`;
        block += realityLines() + transportLines();
        return block;
    } else if (t === 'vmess') {
        let block = `  - name: "${name}"\n    type: vmess\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    uuid: ${sbOut.uuid || ''}\n    alterId: 0\n    cipher: auto\n    tls: true\n    servername: ${sni}`;
        block += transportLines();
        return block;
    } else if (t === 'trojan') {
        let block = `  - name: "${name}"\n    type: trojan\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    password: ${sbOut.password || ''}\n    sni: ${sni}`;
        block += transportLines();
        return block;
    } else if (t === 'shadowsocks') {
        return `  - name: "${name}"\n    type: ss\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    cipher: ${sbOut.method || 'aes-128-gcm'}\n    password: ${sbOut.password || ''}`;
    } else if (t === 'socks') {
        return `  - name: "${name}"\n    type: socks5\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}`;
    } else if (t === 'http') {
        return `  - name: "${name}"\n    type: http\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}`;
    } else if (t === 'wireguard') {
        const ip = (sbOut.local_address && sbOut.local_address[0]) ? sbOut.local_address[0].split('/')[0] : '172.16.0.2';
        const reserved = sbOut.reserved ? JSON.stringify(sbOut.reserved) : '[0, 0, 0]';
        return `  - name: "${name}"\n    type: wireguard\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    ip: ${ip}\n    private-key: ${sbOut.private_key || 'YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ='}\n    public-key: ${sbOut.peer_public_key || WARP_PUBLIC_KEY}\n    reserved: ${reserved}\n    mtu: ${sbOut.mtu || 1280}\n    udp: true`;
    } else if (t === 'hysteria2') {
        let block = `  - name: "${name}"\n    type: hysteria2\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    password: ${sbOut.password || ''}`;
        if (sni) block += `\n    sni: ${sni}`;
        return block;
    } else if (t === 'tuic') {
        let block = `  - name: "${name}"\n    type: tuic\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}\n    uuid: ${sbOut.uuid || ''}\n    password: ${sbOut.password || ''}`;
        if (sni) block += `\n    sni: ${sni}`;
        return block;
    }
    return `  - name: "${name}"\n    type: ${t}\n    server: ${sbOut.server}\n    port: ${sbOut.server_port}`;
}

export function buildClashYaml(chainConfig) {
    if (!chainConfig || !chainConfig.outbounds) return '# Error: missing chain config';
    const proxyOuts = chainConfig.outbounds.filter(o => o.type !== 'direct' && o.type !== 'block');
    const blocks = [];
    for (const out of proxyOuts) {
        let block = singboxOutboundToClash(out);
        if (out.detour) {
            block += `\n    dialer-proxy: "${out.detour}"`;
        }
        blocks.push(block);
    }
    const primaryTag = proxyOuts.length > 0 ? proxyOuts[0].tag : 'DIRECT';
    let vwarpComment = '';
    if (chainConfig._vwarp) {
        vwarpComment = `\n# VWARP Metadata: ${JSON.stringify(chainConfig._vwarp)}`;
    }
    return `# ConfigStream Chain Config (Clash/Mihomo)
# Generated by ConfigStream Laboratory${vwarpComment}
mixed-port: 2080
allow-lan: false

proxies:
${blocks.join('\n\n')}

proxy-groups:
  - name: "Chain"
    type: select
    proxies:
      - "${primaryTag}"
      - DIRECT

rules:
  - MATCH,Chain
`;
}

export function singboxOutboundToXray(sbOut) {
    const xOut = { tag: sbOut.tag };
    const t = sbOut.type;

    function buildStreamSettings(sbOut) {
        const tls = sbOut.tls || {};
        const transport = sbOut.transport || {};
        const sni = tls.server_name || sbOut.server || '';
        const security = tls.enabled !== false && (tls.enabled || tls.server_name) ? 'tls' : 'none';

        const stream = { network: 'tcp', security: security };
        if (security === 'tls') {
            stream.tlsSettings = { serverName: sni };
            if (tls.insecure) stream.tlsSettings.allowInsecure = true;
            if (tls.alpn && tls.alpn.length) stream.tlsSettings.alpn = tls.alpn;
            if (tls.utls && tls.utls.fingerprint) stream.tlsSettings.fingerprint = tls.utls.fingerprint;
        }
        if (tls.reality && tls.reality.enabled) {
            stream.security = 'reality';
            stream.realitySettings = {
                serverName: sni,
                publicKey: tls.reality.public_key || '',
                shortId: tls.reality.short_id || '',
                fingerprint: (tls.utls && tls.utls.fingerprint) || 'chrome'
            };
            delete stream.tlsSettings;
        }
        const tType = transport.type || '';
        if (tType === 'ws') {
            stream.network = 'ws';
            stream.wsSettings = { path: transport.path || '/', headers: transport.headers || {} };
        } else if (tType === 'grpc') {
            stream.network = 'grpc';
            stream.grpcSettings = { serviceName: transport.service_name || '' };
        } else if (tType === 'httpupgrade') {
            stream.network = 'httpupgrade';
            stream.httpupgradeSettings = { path: transport.path || '/', host: transport.host || sni };
        } else if (tType === 'http') {
            stream.network = 'h2';
            stream.httpSettings = { path: transport.path || '/', host: transport.host ? [transport.host] : [sni] };
        }
        return stream;
    }

    if (t === 'vless') {
        xOut.protocol = 'vless';
        const user = { id: sbOut.uuid || '', encryption: 'none' };
        if (sbOut.flow) user.flow = sbOut.flow;
        xOut.settings = { vnext: [{ address: sbOut.server, port: sbOut.server_port, users: [user] }] };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (t === 'vmess') {
        xOut.protocol = 'vmess';
        xOut.settings = { vnext: [{ address: sbOut.server, port: sbOut.server_port, users: [{ id: sbOut.uuid || '', alterId: 0, security: 'auto' }] }] };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (t === 'trojan') {
        xOut.protocol = 'trojan';
        xOut.settings = { servers: [{ address: sbOut.server, port: sbOut.server_port, password: sbOut.password || '' }] };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (t === 'shadowsocks') {
        xOut.protocol = 'shadowsocks';
        xOut.settings = { servers: [{ address: sbOut.server, port: sbOut.server_port, method: sbOut.method || 'aes-128-gcm', password: sbOut.password || '' }] };
    } else if (t === 'socks') {
        xOut.protocol = 'socks';
        xOut.settings = { servers: [{ address: sbOut.server, port: sbOut.server_port }] };
    } else if (t === 'http') {
        xOut.protocol = 'http';
        xOut.settings = { servers: [{ address: sbOut.server, port: sbOut.server_port }] };
    } else if (t === 'wireguard') {
        xOut.protocol = 'wireguard';
        xOut.settings = {
            secretKey: sbOut.private_key || '',
            address: sbOut.local_address || ['172.16.0.2/32'],
            peers: [{
                endpoint: sbOut.server + ':' + sbOut.server_port,
                publicKey: sbOut.peer_public_key || ''
            }],
            reserved: sbOut.reserved || [0, 0, 0],
            mtu: sbOut.mtu || 1280
        };
    } else if (t === 'hysteria2') {
        xOut.protocol = 'freedom';
        xOut._note = 'Hysteria2 is not supported by Xray/V2Ray. Use sing-box for this protocol.';
    } else if (t === 'tuic') {
        xOut.protocol = 'freedom';
        xOut._note = 'TUIC is not supported by Xray/V2Ray. Use sing-box for this protocol.';
    } else {
        xOut.protocol = t || 'freedom';
    }
    if (sbOut.detour) {
        xOut.proxySettings = { tag: sbOut.detour };
    }
    return xOut;
}

export function buildXrayJson(chainConfig) {
    if (!chainConfig || !chainConfig.outbounds) return '{}';
    const xray = {
        log: { loglevel: 'warning' },
        inbounds: [{ tag: 'socks', port: 2080, listen: '127.0.0.1', protocol: 'socks', settings: { udp: true } }],
        outbounds: [],
        routing: { rules: [{ type: 'field', inboundTag: ['socks'], outboundTag: chainConfig.outbounds[0].tag }] }
    };
    if (chainConfig._vwarp) {
        xray._vwarp = chainConfig._vwarp;
    }
    for (const sbOut of chainConfig.outbounds) {
        if (sbOut.type === 'direct') {
            xray.outbounds.push({ tag: sbOut.tag, protocol: 'freedom' });
        } else if (sbOut.type === 'block') {
            xray.outbounds.push({ tag: sbOut.tag, protocol: 'blackhole' });
        } else {
            xray.outbounds.push(singboxOutboundToXray(sbOut));
        }
    }
    return JSON.stringify(xray, null, 2);
}

export function buildNekoboxLink(chainConfig) {
    if (!chainConfig) return '';
    const configStr = JSON.stringify(chainConfig, null, 2);
    return 'nekobox://import-singbox?config=' + encodeURIComponent(btoa(configStr));
}

export function buildPythonScript(chainConfig) {
    const configB64 = btoa(unescape(encodeURIComponent(JSON.stringify(chainConfig))));
    const vwarpPrint = chainConfig._vwarp ? `\n    print("[*] Note: Config uses Vwarp metadata:", CONFIG.get("_vwarp"))` : '';
    return `#!/usr/bin/env python3
"""ConfigStream Chain Runner - Generated by Laboratory
Downloads sing-box if needed and runs the chain config.
"""
import json, os, shutil, subprocess, tempfile, base64

CONFIG = json.loads(base64.b64decode('${configB64}').decode('utf-8'))

def get_singbox():
    if shutil.which("sing-box"):
        return "sing-box"
    raise RuntimeError(
        "sing-box is required but was not found in PATH. "
        "Install sing-box from an official release and re-run this script."
    )

def main():
    binary = get_singbox()
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(CONFIG, f)
        cfg_path = f.name

    print(f"[*] Starting chain proxy on 127.0.0.1:2080")
    print(f"[*] Set your browser/system proxy to socks5://127.0.0.1:2080")${vwarpPrint}
    try:
        subprocess.run([binary, "run", "-c", cfg_path], check=True)
    except KeyboardInterrupt:
        print("\\n[*] Stopped.")
    except Exception as e:
        print(f"\\n[*] Error: {e}")
    finally:
        if os.path.exists(cfg_path):
            os.unlink(cfg_path)

if __name__ == "__main__":
    main()
`;
}

export function buildBashScript(chainConfig) {
    const configB64 = btoa(unescape(encodeURIComponent(JSON.stringify(chainConfig))));
    const vwarpEcho = chainConfig._vwarp ? `\necho "[*] Note: Config uses Vwarp metadata: ${JSON.stringify(chainConfig._vwarp).replace(/"/g, '\\"')}"` : '';
    return `#!/usr/bin/env bash
# ConfigStream Chain Runner - Generated by Laboratory
set -euo pipefail

CONFIG_B64='${configB64}'
CONFIG=$(echo "$CONFIG_B64" | base64 -d)
LISTEN_PORT=2080

if ! command -v sing-box >/dev/null 2>&1; then
    echo "[!] sing-box not found in PATH."
    echo "[!] Install sing-box from the official release source, then re-run this script."
    exit 1
fi

CFG=$(mktemp -t cs-chain.XXXXXX.json)
echo "$CONFIG" > "$CFG"
echo "[*] Starting chain proxy on 127.0.0.1:$LISTEN_PORT"
echo "[*] Set your proxy to socks5://127.0.0.1:$LISTEN_PORT"${vwarpEcho}
trap "rm -f $CFG" EXIT
sing-box run -c "$CFG"
`;
}
