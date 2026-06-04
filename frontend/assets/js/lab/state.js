// ConfigStream Laboratory - State Management
// SPDX-License-Identifier: AGPL-3.0-or-later

export const state = {
    currentStep: 1,
    totalSteps: 5,
    parsedProxy: null,       // { protocol, address, port, uuid, config, details }
    cleanIps: [],            // [{ ip, port, latency, status }]
    selectedCleanIp: null,   // "ip:port"
    chainConfig: null,       // Generated sing-box JSON object
    warpKey: '',
    pipelineProxies: [],
    pipelineLoaded: false,
    strategyManifest: {}
};

export const DEFAULT_CLEAN_IPS = [
    '162.159.192.1:2408', '188.114.98.224:854', '162.159.192.166:5956',
    '188.114.99.73:2506', '162.159.192.253:7103', '188.114.99.153:5956',
    '188.114.96.101:2506', '162.159.192.83:890', '188.114.98.224:500',
    '162.159.192.4:3854', '162.159.192.5:854', '162.159.195.2:864',
];

export const WARP_PUBLIC_KEY = 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=';

export const PROTOCOL_PRIORITY = [
    'hysteria2', 'hysteria', 'tuic', 'wireguard', 'vmess', 'vless', 'trojan',
    'shadowsocks', 'ss2022', 'ssr', 'socks5', 'socks4', 'http', 'https', 'ssh',
    'naive', 'anytls', 'snell', 'brook', 'juicity', 'xray', 'xtls', 'v2ray',
    'exclave', 'openvpn', 'revived', 'unknown',
];

export const PROTOCOL_PRIORITY_INDEX = PROTOCOL_PRIORITY.reduce((acc, proto, idx) => {
    acc[proto] = idx;
    return acc;
}, {});

export const STATIC_HOST_SUFFIXES = ['github.io', 'pages.dev', 'netlify.app'];

export const PIPELINE_URLS = [
    'base64.txt',           // Base64-encoded URI list
    'base64-dns-safe.txt',  // DNS-safe variant (IP-only)
];
