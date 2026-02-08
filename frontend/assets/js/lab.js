// ConfigStream Laboratory - Chain Builder Logic
// Handles step navigation, proxy parsing, clean IP discovery, chain building, testing, and export.

(function () {
    'use strict';

    // --- State ---
    let currentStep = 1;
    const totalSteps = 5;
    let parsedProxy = null;       // { protocol, address, port, uuid, config, details }
    let cleanIps = [];            // [{ ip, port, latency, status }]
    let selectedCleanIp = null;   // "ip:port"
    let chainConfig = null;       // Generated sing-box JSON object
    let warpKey = '';

    // Default clean IPs from ConfigStream (fallback)
    const DEFAULT_CLEAN_IPS = [
        '162.159.192.1:2408', '188.114.98.224:854', '162.159.192.166:5956',
        '188.114.99.73:2506', '162.159.192.253:7103', '188.114.99.153:5956',
        '188.114.96.101:2506', '162.159.192.83:890', '188.114.98.224:500',
        '162.159.192.4:3854', '162.159.192.5:854', '162.159.195.2:864',
    ];

    const WARP_PUBLIC_KEY = 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=';

    // --- DOM Helpers ---
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    function showResult(elId, type, message) {
        const el = document.getElementById(elId);
        if (!el) return;
        el.className = 'lab-test-result ' + type;
        el.innerHTML = message;
        el.style.display = 'block';
    }

    function hideResult(elId) {
        const el = document.getElementById(elId);
        if (el) el.style.display = 'none';
    }

    // --- Step Navigation ---
    function goToStep(step) {
        if (step < 1 || step > totalSteps) return;
        currentStep = step;

        // Update panels
        $$('.lab-step-panel').forEach((panel, i) => {
            panel.classList.toggle('active', i + 1 === step);
        });

        // Update stepper dots
        $$('.lab-step-dot').forEach((dot) => {
            const s = parseInt(dot.dataset.step);
            dot.classList.remove('active', 'completed');
            if (s === step) dot.classList.add('active');
            else if (s < step) dot.classList.add('completed');
        });

        // Update connector lines
        $$('.lab-step-line').forEach((line, i) => {
            line.classList.toggle('completed', i + 1 < step);
        });

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- Network Diagnosis ---
    async function runDiagnosis() {
        const tbody = $('#diagTableBody');
        const container = $('#diagResults');
        const advice = $('#diagAdvice');
        if (!tbody || !container) return;
        container.style.display = 'block';
        tbody.innerHTML = '<tr><td colspan="3">Running tests...</td></tr>';

        const tests = [
            { name: 'Cloudflare HTTP', url: 'https://cp.cloudflare.com/generate_204', key: 'cf' },
            { name: 'Google HTTP', url: 'https://connectivitycheck.gstatic.com/generate_204', key: 'google' },
            { name: 'Cloudflare TLS', url: 'https://1.1.1.1/cdn-cgi/trace', key: 'cf_tls' },
            { name: 'GitHub API', url: 'https://api.github.com', key: 'github' },
        ];
        const results = {};
        tbody.innerHTML = '';

        for (const t of tests) {
            const tr = document.createElement('tr');
            const start = performance.now();
            try {
                const resp = await fetch(t.url, { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(6000) });
                const lat = Math.round(performance.now() - start);
                results[t.key] = true;
                tr.innerHTML = `<td>${t.name}</td><td>${lat}ms</td><td class="status-ok">Reachable</td>`;
            } catch {
                results[t.key] = false;
                tr.innerHTML = `<td>${t.name}</td><td>-</td><td class="status-fail">Blocked</td>`;
            }
            tbody.appendChild(tr);
        }

        // Advice
        if (advice) {
            const reachable = Object.values(results).filter(Boolean).length;
            if (reachable >= 3) {
                showResult('diagAdvice', 'success', '<strong>Good connectivity!</strong> You can use WARP, Fragment, or Worker chains directly.');
            } else if (results.cf || results.cf_tls) {
                showResult('diagAdvice', 'info', '<strong>Cloudflare reachable</strong> but other sites filtered. WARP chain is your best bet.');
            } else if (reachable > 0) {
                showResult('diagAdvice', 'info', '<strong>Limited access.</strong> Try TLS Fragment or CDN Worker strategy. If you have a local proxy, use it as Layer 1.');
            } else {
                showResult('diagAdvice', 'error', '<strong>No direct internet detected.</strong> You need a local proxy (Psiphon, Lantern, V2RayN) as Layer 1. Then stack WARP on top. Download <code>lab-scanner.py</code> below for offline scanning.');
            }
        }
    }

    async function testLocalProxy() {
        const type = ($('#localProxyType') || {}).value;
        const addr = ($('#localProxyAddr') || {}).value || '';
        if (!type || !addr) {
            showResult('localProxyResult', 'error', 'Select a proxy type and enter the address.');
            return;
        }
        showResult('localProxyResult', 'pending', `Testing ${type}://${addr}...`);
        // Browser can't directly test SOCKS/HTTP proxies, so provide guidance
        showResult('localProxyResult', 'info',
            `<strong>Browser cannot test ${type.toUpperCase()} proxies directly.</strong><br>` +
            `To verify, run in terminal:<br>` +
            `<code>curl -x ${type}://${addr} --connect-timeout 5 http://cp.cloudflare.com/generate_204</code><br><br>` +
            `If it returns HTTP 204, your proxy works. It will be added as Layer 1 of your chain.`
        );
    }

    // --- Step 1: Parse Proxy ---
    function parseProxyUri(uri) {
        uri = (uri || '').trim();
        if (!uri) return null;

        // Extract protocol
        const schemeMatch = uri.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):\/\//);
        if (!schemeMatch) return null;

        let protocol = schemeMatch[1].toLowerCase();
        // Normalize
        if (protocol === 'hy2') protocol = 'hysteria2';
        if (protocol === 'wg') protocol = 'wireguard';
        if (protocol === 'socks') protocol = 'socks5';

        // Try to extract address:port from URI
        let address = '', port = 443, uuid = '', remark = '';
        try {
            // Remove fragment (remark)
            const fragIdx = uri.indexOf('#');
            if (fragIdx !== -1) {
                remark = decodeURIComponent(uri.substring(fragIdx + 1));
                uri = uri.substring(0, fragIdx);
            }

            if (protocol === 'vmess') {
                // VMess uses base64-encoded JSON
                const b64 = uri.replace(/^vmess:\/\//, '');
                try {
                    const json = JSON.parse(atob(b64));
                    address = json.add || json.addr || '';
                    port = parseInt(json.port) || 443;
                    uuid = json.id || '';
                    remark = remark || json.ps || '';
                } catch {
                    return null;
                }
            } else {
                // Standard URI parsing for vless, trojan, ss, etc.
                const url = new URL(uri);
                address = url.hostname || '';
                port = parseInt(url.port) || 443;
                uuid = url.username ? decodeURIComponent(url.username) : '';
            }
        } catch {
            return null;
        }

        if (!address) return null;

        return {
            protocol,
            address,
            port,
            uuid,
            remark: remark || `${protocol}@${address}`,
            config: (uri.indexOf('#') !== -1 ? uri : uri) // preserve original
        };
    }

    function handleStep1Next() {
        const uriText = ($('#proxyUri') || {}).value || '';
        // Support multiple lines - take first valid
        const lines = uriText.split('\n').map(l => l.trim()).filter(Boolean);
        parsedProxy = null;

        for (const line of lines) {
            const parsed = parseProxyUri(line);
            if (parsed) {
                parsedProxy = parsed;
                parsedProxy.config = line;
                break;
            }
        }

        if (!parsedProxy) {
            showResult('step1Result', 'error', 'Could not parse proxy URI. Ensure it starts with a valid protocol (vless://, vmess://, trojan://, ss://, etc.).');
            return;
        }

        showResult('step1Result', 'success',
            `<strong>Parsed:</strong> ${parsedProxy.protocol.toUpperCase()} @ ${parsedProxy.address}:${parsedProxy.port}` +
            (parsedProxy.remark ? ` (${parsedProxy.remark})` : '')
        );

        setTimeout(() => goToStep(2), 600);
    }

    // --- Step 2: Clean IP Discovery ---
    function handleCleanIpMethodChange() {
        const method = ($('#cleanIpMethod') || {}).value;
        const manualDiv = $('#manualIpInput');
        if (manualDiv) manualDiv.style.display = method === 'manual' ? 'block' : 'none';
    }

    async function handleStep2Next() {
        const method = ($('#cleanIpMethod') || {}).value;
        cleanIps = [];

        if (method === 'manual') {
            const raw = ($('#manualCleanIps') || {}).value || '';
            const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
            cleanIps = lines.map(l => {
                const parts = l.split(':');
                return {
                    ip: parts[0] || l,
                    port: parseInt(parts[1]) || 443,
                    latency: null,
                    status: 'untested'
                };
            });
        } else if (method === 'auto') {
            // Try fetching from ConfigStream API first, fallback to defaults
            showResult('step2Result', 'pending', 'Fetching clean IPs from ConfigStream...');
            try {
                const resp = await fetch('data/clean_ips.json?cb=' + Date.now());
                if (resp.ok) {
                    const data = await resp.json();
                    if (Array.isArray(data) && data.length > 0) {
                        cleanIps = data.slice(0, 20).map(entry => {
                            const str = typeof entry === 'string' ? entry : (entry.ip + ':' + entry.port);
                            const parts = str.split(':');
                            return { ip: parts[0], port: parseInt(parts[1]) || 443, latency: null, status: 'ok' };
                        });
                    }
                }
            } catch { /* fallback below */ }

            if (cleanIps.length === 0) {
                cleanIps = DEFAULT_CLEAN_IPS.map(s => {
                    const parts = s.split(':');
                    return { ip: parts[0], port: parseInt(parts[1]) || 443, latency: null, status: 'ok' };
                });
            }
        } else if (method === 'scan') {
            showResult('step2Result', 'info',
                '<strong>Local Scan:</strong> Open a terminal and run:<br>' +
                '<code>for ip in 162.159.192.1 188.114.98.224 162.159.195.2; do ' +
                'for port in 854 890 2408 500; do ' +
                'curl -x socks5://$ip:$port --connect-timeout 3 -o /dev/null -w "%{http_code} %{time_total}s $ip:$port\\n" https://cp.cloudflare.com/generate_204 2>/dev/null; ' +
                'done; done</code><br><br>Paste the working IP:port pairs into the Manual input above.'
            );
            handleCleanIpMethodChange();
            $('#cleanIpMethod').value = 'manual';
            $('#manualIpInput').style.display = 'block';
            return;
        }

        if (cleanIps.length === 0) {
            showResult('step2Result', 'error', 'No clean IPs found. Try manual input or local scan.');
            return;
        }

        // Display results table
        renderCleanIpTable();
        populateWarpIpSelect();

        showResult('step2Result', 'success', `Found ${cleanIps.length} clean IP(s). Select one in the next step.`);
        setTimeout(() => goToStep(3), 600);
    }

    function renderCleanIpTable() {
        const tbody = $('#cleanIpTableBody');
        const container = $('#cleanIpResults');
        if (!tbody || !container) return;

        tbody.innerHTML = '';
        cleanIps.forEach(ip => {
            const tr = document.createElement('tr');
            const statusCls = ip.status === 'ok' ? 'status-ok' : (ip.status === 'fail' ? 'status-fail' : '');
            tr.innerHTML = `<td>${ip.ip}:${ip.port}</td>` +
                `<td>${ip.latency !== null ? ip.latency + 'ms' : '-'}</td>` +
                `<td class="${statusCls}">${ip.status === 'ok' ? 'OK' : ip.status === 'fail' ? 'Failed' : 'Untested'}</td>`;
            tbody.appendChild(tr);
        });
        container.style.display = 'block';
    }

    function populateWarpIpSelect() {
        const select = $('#warpCleanIp');
        if (!select) return;
        select.innerHTML = '';
        cleanIps.forEach((ip, i) => {
            const opt = document.createElement('option');
            opt.value = ip.ip + ':' + ip.port;
            opt.textContent = ip.ip + ':' + ip.port + (ip.latency ? ` (${ip.latency}ms)` : '');
            if (i === 0) opt.selected = true;
            select.appendChild(opt);
        });
    }

    // --- Chain Type UI Toggle ---
    const CHAIN_HINTS = {
        'warp': 'Traffic flows through Cloudflare WARP to hide the proxy from your ISP.',
        'warp-in-warp': 'Double encapsulation: outer WARP wraps inner WARP wraps your proxy. Maximum obfuscation.',
        'fragment': 'Splits TLS handshake into small fragments to bypass stateless DPI. No tunnel needed.',
        'worker': 'Routes traffic through your own Cloudflare Worker. Unblockable private relay.',
        'custom': 'Define your own outbound chain in raw Sing-box JSON format.'
    };

    function handleChainTypeChange() {
        const ct = ($('#chainType') || {}).value || 'warp';
        const hint = $('#chainTypeHint');
        if (hint) hint.textContent = CHAIN_HINTS[ct] || '';

        const showWarp = ct === 'warp' || ct === 'warp-in-warp';
        const el = (id) => document.getElementById(id);
        if (el('warpOptions')) el('warpOptions').style.display = showWarp ? '' : 'none';
        if (el('warpInWarpRow')) el('warpInWarpRow').style.display = ct === 'warp-in-warp' ? '' : 'none';
        if (el('fragmentOptions')) el('fragmentOptions').style.display = ct === 'fragment' ? '' : 'none';
        if (el('workerOptions')) el('workerOptions').style.display = ct === 'worker' ? '' : 'none';
        if (el('customChainOptions')) el('customChainOptions').style.display = ct === 'custom' ? '' : 'none';

        // Update chain visual layer1 label
        const l1 = $('#chainLayer1Label');
        if (l1) {
            const labels = { 'warp': 'WARP', 'warp-in-warp': 'WARP x2', 'fragment': 'Fragment', 'worker': 'Worker', 'custom': 'Custom' };
            l1.textContent = labels[ct] || 'WARP';
        }
    }

    function getEvasionOptions() {
        return {
            fingerprint: ($('#tlsFingerprint') || {}).value || '',
            alpn: ($('#alpnProtocol') || {}).value || '',
            mux: ($('#muxProtocol') || {}).value || '',
            muxPadding: ($('#muxPadding') || {}).value === 'true'
        };
    }

    // --- Step 3: Build Chain ---
    function handleStep3Next() {
        const chainType = ($('#chainType') || {}).value || 'warp';
        selectedCleanIp = ($('#warpCleanIp') || {}).value || '';
        warpKey = ($('#warpKeyInput') || {}).value || '';

        if (!parsedProxy) {
            showResult('step3Result', 'error', 'No base proxy configured. Go back to Step 1.');
            return;
        }

        const evasion = getEvasionOptions();

        // Check if user has a local proxy (Layer 1)
        const localType = ($('#localProxyType') || {}).value || '';
        const localAddr = ($('#localProxyAddr') || {}).value || '';

        // Build config based on chain type
        if (chainType === 'warp' || chainType === 'warp-in-warp') {
            if (!selectedCleanIp) {
                showResult('step3Result', 'error', 'Please select a clean IP.');
                return;
            }
            const [warpIp, warpPort] = selectedCleanIp.split(':');
            if (chainType === 'warp-in-warp') {
                const outer = ($('#warp2CleanIp') || {}).value || selectedCleanIp;
                const outerKey = ($('#warp2Key') || {}).value || '';
                chainConfig = buildDoubleWarpChain(parsedProxy, warpIp, parseInt(warpPort) || 2408, warpKey, outer, outerKey, evasion);
            } else {
                chainConfig = buildSingboxChain(parsedProxy, warpIp, parseInt(warpPort) || 2408, warpKey, evasion);
            }
            const wd = $('#chainWarpIp');
            if (wd) wd.textContent = warpIp + ':' + (warpPort || 2408);
        } else if (chainType === 'fragment') {
            const fragSize = ($('#fragSize') || {}).value || '10-30';
            const fragDelay = ($('#fragDelay') || {}).value || '5-10';
            chainConfig = buildFragmentChain(parsedProxy, fragSize, fragDelay, evasion);
        } else if (chainType === 'worker') {
            const workerUrl = ($('#workerUrl') || {}).value || '';
            if (!workerUrl) {
                showResult('step3Result', 'error', 'Please enter your Worker URL.');
                return;
            }
            chainConfig = buildWorkerChain(parsedProxy, workerUrl, evasion);
        } else if (chainType === 'custom') {
            try {
                const raw = ($('#customOutboundsJson') || {}).value || '[]';
                const custom = JSON.parse(raw);
                chainConfig = buildCustomChain(parsedProxy, custom, evasion);
            } catch (e) {
                showResult('step3Result', 'error', 'Invalid JSON: ' + e.message);
                return;
            }
        }

        // If local proxy Layer 1 is set, inject it as the outermost detour
        if (localType && localAddr && chainConfig && chainConfig.outbounds) {
            const [lHost, lPort] = localAddr.includes(':') ? localAddr.split(':') : [localAddr, '1080'];
            const localOut = {
                type: localType === 'socks5' ? 'socks' : 'http',
                tag: 'layer1-local',
                server: lHost,
                server_port: parseInt(lPort) || 1080
            };
            if (localType === 'socks5') localOut.version = '5';
            // Find the outermost tunnel outbound and set its detour
            const tunnelOuts = chainConfig.outbounds.filter(o => o.tag !== 'direct' && o.tag !== 'block' && o.tag !== 'proxy-chain');
            if (tunnelOuts.length > 0) {
                const outermost = tunnelOuts[tunnelOuts.length - 1];
                outermost.detour = 'layer1-local';
            }
            chainConfig.outbounds.push(localOut);
        }

        // Update visualization
        const pl = $('#chainProxyLabel');
        const pd = $('#chainProxyDetail');
        if (pl) pl.textContent = parsedProxy.protocol.toUpperCase();
        if (pd) pd.textContent = parsedProxy.address;

        showResult('step3Result', 'success', 'Chain configuration generated! Proceed to test it.');
        setTimeout(() => {
            goToStep(4);
            const preview = $('#chainConfigPreview');
            const code = $('#chainConfigCode');
            if (preview && code) {
                code.textContent = JSON.stringify(chainConfig, null, 2);
                preview.style.display = 'block';
            }
        }, 500);
    }

    // --- Shared Config Skeleton ---
    function wrapConfig(outbounds, primaryTag) {
        return {
            log: { level: 'info' },
            inbounds: [{ type: 'mixed', tag: 'mixed-in', listen: '127.0.0.1', listen_port: 2080 }],
            outbounds: [...outbounds, { type: 'direct', tag: 'direct' }, { type: 'block', tag: 'block' }],
            route: { rules: [{ inbound: ['mixed-in'], outbound: primaryTag }], final: primaryTag }
        };
    }

    function makeWarpOutbound(tag, ip, port, key) {
        const o = {
            type: 'wireguard', tag: tag, server: ip, server_port: port,
            local_address: ['172.16.0.2/32', 'fd01:db8:85a3::2/128'],
            private_key: 'YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=',
            peer_public_key: WARP_PUBLIC_KEY, mtu: 1280
        };
        if (key) o.reserved = [0, 0, 0];
        return o;
    }

    function applyEvasion(outbound, evasion) {
        if (!evasion) return outbound;
        if (outbound.tls && typeof outbound.tls === 'object') {
            if (evasion.fingerprint) outbound.tls.utls = { enabled: true, fingerprint: evasion.fingerprint };
            if (evasion.alpn) outbound.tls.alpn = evasion.alpn.split(',').map(s => s.trim());
        }
        if (evasion.mux) {
            outbound.multiplex = { enabled: true, protocol: evasion.mux, max_connections: 4, padding: evasion.muxPadding };
        }
        return outbound;
    }

    // --- Chain Builders ---
    function buildSingboxChain(proxy, warpIp, warpPort, key, evasion) {
        const warp = makeWarpOutbound('warp-out', warpIp, warpPort, key);
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        proxyOut.detour = 'warp-out';
        return wrapConfig([proxyOut, warp], proxyOut.tag);
    }

    function buildDoubleWarpChain(proxy, innerIp, innerPort, innerKey, outerSpec, outerKey, evasion) {
        const [outerIp, outerPortStr] = (outerSpec || innerIp + ':' + innerPort).split(':');
        const outerPort = parseInt(outerPortStr) || 2408;
        const outerWarp = makeWarpOutbound('warp-outer', outerIp, outerPort, outerKey);
        const innerWarp = makeWarpOutbound('warp-inner', innerIp, innerPort, innerKey);
        innerWarp.detour = 'warp-outer';
        innerWarp.local_address = ['172.16.0.3/32', 'fd01:db8:85a3::3/128'];
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        proxyOut.detour = 'warp-inner';
        return wrapConfig([proxyOut, innerWarp, outerWarp], proxyOut.tag);
    }

    function buildFragmentChain(proxy, fragSize, fragDelay, evasion) {
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        if (proxyOut.tls && typeof proxyOut.tls === 'object') {
            const [minS, maxS] = (fragSize || '10-30').split('-').map(Number);
            const [minD, maxD] = (fragDelay || '5-10').split('-').map(Number);
            proxyOut.tls.fragment = { enabled: true, size: (minS || 10) + '-' + (maxS || 30), sleep: (minD || 5) + '-' + (maxD || 10) };
        }
        return wrapConfig([proxyOut], proxyOut.tag);
    }

    function buildWorkerChain(proxy, workerUrl, evasion) {
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        // Route proxy through worker by rewriting the server to the worker host
        try {
            const u = new URL(workerUrl);
            proxyOut.server = u.hostname;
            proxyOut.server_port = u.port ? parseInt(u.port) : 443;
            if (proxyOut.tls && typeof proxyOut.tls === 'object') {
                proxyOut.tls.server_name = u.hostname;
            }
            // Use ws transport to the worker
            proxyOut.transport = { type: 'ws', path: '/' + proxy.address + ':' + proxy.port, headers: { Host: u.hostname } };
        } catch { /* keep as-is if URL invalid */ }
        return wrapConfig([proxyOut], proxyOut.tag);
    }

    function buildCustomChain(proxy, customOutbounds, evasion) {
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        if (Array.isArray(customOutbounds) && customOutbounds.length > 0) {
            // Chain proxy through the first custom outbound
            const lastCustomTag = customOutbounds[customOutbounds.length - 1].tag || 'custom-out';
            proxyOut.detour = lastCustomTag;
        }
        return wrapConfig([proxyOut, ...customOutbounds], proxyOut.tag);
    }

    function buildProxyOutbound(proxy) {
        const p = proxy;
        const base = { tag: 'proxy-chain', server: p.address, server_port: p.port };
        switch (p.protocol) {
            case 'vless':
                return { ...base, type: 'vless', uuid: p.uuid || '', flow: '', tls: { enabled: true, server_name: p.address }, packet_encoding: 'xudp' };
            case 'vmess':
                return { ...base, type: 'vmess', uuid: p.uuid || '', security: 'auto', tls: { enabled: true, server_name: p.address } };
            case 'trojan':
                return { ...base, type: 'trojan', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
            case 'shadowsocks': case 'ss':
                return { ...base, type: 'shadowsocks', method: 'aes-128-gcm', password: p.uuid || '' };
            case 'hysteria2':
                return { ...base, type: 'hysteria2', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
            case 'tuic':
                return { ...base, type: 'tuic', uuid: p.uuid || '', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
            case 'wireguard':
                return { ...base, type: 'wireguard', local_address: ['172.16.0.4/32'], private_key: p.uuid || '', peer_public_key: '', mtu: 1280 };
            default:
                return { ...base, type: p.protocol, uuid: p.uuid || '' };
        }
    }

    // --- Step 4: Test ---
    async function handleStep4Test() {
        if (!chainConfig) {
            showResult('step4Result', 'error', 'No chain config generated. Go back to Step 3.');
            return;
        }

        showResult('step4Result', 'pending', 'Testing chain connectivity... This may take up to 15 seconds.');
        const testBtn = $('#step4Test');
        if (testBtn) testBtn.disabled = true;

        try {
            // Try the backend test API if available
            const resp = await fetch('/api/lab/test-chain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: chainConfig })
            });

            if (resp.ok) {
                const result = await resp.json();
                if (result.success) {
                    showResult('step4Result', 'success',
                        `<strong>Chain is working!</strong> Latency: ${result.latency || 'N/A'}ms` +
                        (result.exit_ip ? ` | Exit IP: ${result.exit_ip}` : '')
                    );
                    const nextBtn = $('#step4Next');
                    if (nextBtn) nextBtn.disabled = false;
                } else {
                    showResult('step4Result', 'error',
                        `<strong>Test failed:</strong> ${result.error || 'Unknown error'}. Check troubleshooting below.`
                    );
                }
            } else {
                // API not available (static hosting) - show manual test instructions
                showManualTestInstructions();
            }
        } catch {
            // API not available - show manual test instructions
            showManualTestInstructions();
        }

        if (testBtn) testBtn.disabled = false;
    }

    function showManualTestInstructions() {
        const configStr = JSON.stringify(chainConfig, null, 2);
        showResult('step4Result', 'info',
            '<strong>Live test unavailable</strong> (static hosting detected).<br><br>' +
            'To test manually:<br>' +
            '1. Save the config above to a file (e.g. <code>chain.json</code>)<br>' +
            '2. Run: <code>sing-box run -c chain.json</code><br>' +
            '3. Set your browser proxy to <code>127.0.0.1:2080</code><br>' +
            '4. Visit <a href="https://ip.gs" target="_blank" rel="noopener">ip.gs</a> to verify your exit IP<br><br>' +
            'If it works, click "Continue to Export" below.'
        );
        const nextBtn = $('#step4Next');
        if (nextBtn) nextBtn.disabled = false;
    }

    // --- Step 5: Export ---
    function handleStep5Export() {
        if (!chainConfig) {
            showResult('step5Result', 'error', 'No chain config. Go back and complete previous steps.');
            return;
        }

        const format = ($('#exportFormat') || {}).value || 'singbox';
        let content = '';
        let filename = 'configstream-chain';

        switch (format) {
            case 'singbox':
                content = JSON.stringify(chainConfig, null, 2);
                filename += '.json';
                break;
            case 'clash':
                content = buildClashYaml();
                filename += '.yaml';
                break;
            case 'xray':
                content = buildXrayJson();
                filename += '-xray.json';
                break;
            case 'nekobox':
                content = buildNekoboxLink();
                filename += '-nekobox.txt';
                break;
            case 'uri':
                content = parsedProxy ? parsedProxy.config : '';
                filename += '.txt';
                break;
            case 'qr':
                generateQR(parsedProxy ? parsedProxy.config : '');
                showResult('step5Result', 'success', 'QR code generated. Scan with your mobile VPN client.');
                return;
            case 'script-python':
                content = buildPythonScript();
                filename += '.py';
                break;
            case 'script-bash':
                content = buildBashScript();
                filename += '.sh';
                break;
            default:
                content = JSON.stringify(chainConfig, null, 2);
                filename += '.json';
        }

        const outputEl = $('#exportOutput');
        const codeEl = $('#exportCode');
        if (outputEl && codeEl) {
            codeEl.textContent = content;
            outputEl.style.display = 'block';
        }
        $('#qrOutput').style.display = 'none';

        // Store for download
        window._labExportContent = content;
        window._labExportFilename = filename;

        showResult('step5Result', 'success', `${format.toUpperCase()} export ready. Copy or download the config.`);
    }

    function buildClashYaml() {
        if (!parsedProxy || !selectedCleanIp) return '# Error: missing data';
        const [warpIp, warpPort] = selectedCleanIp.split(':');
        const p = parsedProxy;

        let proxyBlock = '';
        switch (p.protocol) {
            case 'vless':
                proxyBlock = `  - name: "chain-proxy"\n    type: vless\n    server: ${p.address}\n    port: ${p.port}\n    uuid: ${p.uuid}\n    tls: true\n    servername: ${p.address}`;
                break;
            case 'vmess':
                proxyBlock = `  - name: "chain-proxy"\n    type: vmess\n    server: ${p.address}\n    port: ${p.port}\n    uuid: ${p.uuid}\n    alterId: 0\n    cipher: auto\n    tls: true\n    servername: ${p.address}`;
                break;
            case 'trojan':
                proxyBlock = `  - name: "chain-proxy"\n    type: trojan\n    server: ${p.address}\n    port: ${p.port}\n    password: ${p.uuid}\n    sni: ${p.address}`;
                break;
            default:
                proxyBlock = `  - name: "chain-proxy"\n    type: ${p.protocol}\n    server: ${p.address}\n    port: ${p.port}`;
        }

        return `# ConfigStream Chain Config (Clash/Mihomo)
# Generated by ConfigStream Laboratory
mixed-port: 2080
allow-lan: false

proxies:
  - name: "warp"
    type: wireguard
    server: ${warpIp}
    port: ${warpPort || 2408}
    ip: 172.16.0.2
    private-key: YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=
    public-key: ${WARP_PUBLIC_KEY}
    mtu: 1280

${proxyBlock}
    dialer-proxy: "warp"

proxy-groups:
  - name: "Chain"
    type: select
    proxies:
      - "chain-proxy"
      - DIRECT

rules:
  - MATCH,Chain
`;
    }

    function buildXrayJson() {
        if (!parsedProxy) return '{}';
        const p = parsedProxy;
        const xray = {
            log: { loglevel: 'warning' },
            inbounds: [{ tag: 'socks', port: 2080, listen: '127.0.0.1', protocol: 'socks', settings: { udp: true } }],
            outbounds: []
        };
        const base = { tag: 'proxy', protocol: p.protocol === 'shadowsocks' ? 'shadowsocks' : p.protocol };
        if (p.protocol === 'vless') {
            base.settings = { vnext: [{ address: p.address, port: p.port, users: [{ id: p.uuid, encryption: 'none' }] }] };
            base.streamSettings = { network: 'tcp', security: 'tls', tlsSettings: { serverName: p.address } };
        } else if (p.protocol === 'vmess') {
            base.settings = { vnext: [{ address: p.address, port: p.port, users: [{ id: p.uuid, alterId: 0, security: 'auto' }] }] };
            base.streamSettings = { network: 'tcp', security: 'tls', tlsSettings: { serverName: p.address } };
        } else if (p.protocol === 'trojan') {
            base.settings = { servers: [{ address: p.address, port: p.port, password: p.uuid }] };
            base.streamSettings = { network: 'tcp', security: 'tls', tlsSettings: { serverName: p.address } };
        } else if (p.protocol === 'shadowsocks' || p.protocol === 'ss') {
            base.protocol = 'shadowsocks';
            base.settings = { servers: [{ address: p.address, port: p.port, method: 'aes-128-gcm', password: p.uuid }] };
        }
        xray.outbounds.push(base, { tag: 'direct', protocol: 'freedom' }, { tag: 'block', protocol: 'blackhole' });
        return JSON.stringify(xray, null, 2);
    }

    function buildNekoboxLink() {
        if (!parsedProxy) return '';
        // Nekobox uses sing-box JSON format, base64 encode the config
        const configStr = JSON.stringify(chainConfig, null, 2);
        return 'nekobox://import-singbox?config=' + encodeURIComponent(btoa(configStr));
    }

    function buildPythonScript() {
        const configJson = JSON.stringify(chainConfig).replace(/'/g, "\\'");
        return `#!/usr/bin/env python3
"""ConfigStream Chain Runner - Generated by Laboratory
Downloads sing-box if needed and runs the chain config.
"""
import json, os, platform, shutil, subprocess, sys, tempfile, urllib.request

CONFIG = json.loads('${configJson}')
SINGBOX_VERSION = "1.11.0"

def get_singbox():
    if shutil.which("sing-box"):
        return "sing-box"
    print("[*] sing-box not found, downloading...")
    machine = platform.machine().lower()
    goos = {"linux": "linux", "darwin": "darwin", "win32": "windows"}.get(sys.platform, "linux")
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(machine, "amd64")
    ext = ".exe" if goos == "windows" else ""
    name = f"sing-box-{SINGBOX_VERSION}-{goos}-{arch}"
    url = f"https://github.com/SagerNet/sing-box/releases/download/v{SINGBOX_VERSION}/{name}.tar.gz"
    tmp = tempfile.mkdtemp()
    archive = os.path.join(tmp, "singbox.tar.gz")
    urllib.request.urlretrieve(url, archive)
    import tarfile
    with tarfile.open(archive) as tf:
        tf.extractall(tmp)
    binary = os.path.join(tmp, name, "sing-box" + ext)
    os.chmod(binary, 0o755)
    return binary

def main():
    binary = get_singbox()
    cfg_path = tempfile.mktemp(suffix=".json")
    with open(cfg_path, "w") as f:
        json.dump(CONFIG, f)
    print(f"[*] Starting chain proxy on 127.0.0.1:2080")
    print(f"[*] Set your browser/system proxy to socks5://127.0.0.1:2080")
    try:
        subprocess.run([binary, "run", "-c", cfg_path], check=True)
    except KeyboardInterrupt:
        print("\\n[*] Stopped.")
    finally:
        os.unlink(cfg_path)

if __name__ == "__main__":
    main()
`;
    }

    function buildBashScript() {
        const configJson = JSON.stringify(chainConfig);
        return `#!/usr/bin/env bash
# ConfigStream Chain Runner - Generated by Laboratory
set -euo pipefail

CONFIG='${configJson}'
LISTEN_PORT=2080

command -v sing-box >/dev/null 2>&1 || {
    echo "[*] sing-box not found. Installing..."
    VERSION="1.11.0"
    ARCH=$(uname -m)
    case "$ARCH" in x86_64|amd64) ARCH=amd64;; aarch64|arm64) ARCH=arm64;; esac
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    URL="https://github.com/SagerNet/sing-box/releases/download/v\${VERSION}/sing-box-\${VERSION}-\${OS}-\${ARCH}.tar.gz"
    TMP=$(mktemp -d)
    curl -sL "$URL" | tar xz -C "$TMP"
    BINARY="$TMP/sing-box-\${VERSION}-\${OS}-\${ARCH}/sing-box"
    chmod +x "$BINARY"
    alias sing-box="$BINARY"
}

CFG=$(mktemp /tmp/cs-chain-XXXX.json)
echo "$CONFIG" > "$CFG"
echo "[*] Starting chain proxy on 127.0.0.1:$LISTEN_PORT"
echo "[*] Set your proxy to socks5://127.0.0.1:$LISTEN_PORT"
trap "rm -f $CFG" EXIT
sing-box run -c "$CFG"
`;
    }

    function generateQR(text) {
        const qrDiv = $('#qrOutput');
        if (!qrDiv) return;
        // Simple fallback using a public QR API (no dependency)
        const encoded = encodeURIComponent(text || '');
        qrDiv.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encoded}" alt="QR Code" style="border-radius: 12px; max-width: 250px;">`;
        qrDiv.style.display = 'block';
        $('#exportOutput').style.display = 'none';
    }

    function handleStep5Download() {
        const content = window._labExportContent;
        const filename = window._labExportFilename;
        if (!content) {
            showResult('step5Result', 'error', 'Generate an export first.');
            return;
        }
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'configstream-chain.json';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
    }

    // --- Copy Buttons ---
    function setupCopyButton(btnId, codeId) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        btn.addEventListener('click', () => {
            const code = document.getElementById(codeId);
            if (!code) return;
            navigator.clipboard.writeText(code.textContent).then(() => {
                btn.textContent = 'Copied!';
                setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
            }).catch(() => {
                // Fallback
                const range = document.createRange();
                range.selectNodeContents(code);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                document.execCommand('copy');
                btn.textContent = 'Copied!';
                setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
            });
        });
    }

    // --- Load from Subscription ---
    async function handleLoadFromSub() {
        try {
            const resp = await fetch('proxies.txt?cb=' + Date.now());
            if (!resp.ok) throw new Error('Not found');
            const text = await resp.text();
            const lines = text.split('\n').filter(l => l.trim());
            if (lines.length > 0) {
                const textarea = $('#proxyUri');
                if (textarea) textarea.value = lines[0];
                showResult('step1Result', 'info', `Loaded ${lines.length} proxy(s) from subscription. First one selected.`);
            }
        } catch {
            showResult('step1Result', 'error', 'Could not load subscription. Try pasting a proxy URI manually.');
        }
    }

    // --- Init ---
    document.addEventListener('DOMContentLoaded', () => {
        // Step navigation via dots
        $$('.lab-step-dot').forEach(dot => {
            dot.addEventListener('click', () => {
                const step = parseInt(dot.dataset.step);
                if (step <= currentStep) goToStep(step);
            });
        });

        // Step 1
        const diagBtn = $('#runDiagnosis');
        if (diagBtn) diagBtn.addEventListener('click', runDiagnosis);
        const testLP = $('#testLocalProxy');
        if (testLP) testLP.addEventListener('click', testLocalProxy);
        const step1Next = $('#step1Next');
        if (step1Next) step1Next.addEventListener('click', handleStep1Next);
        const loadSub = $('#loadFromSub');
        if (loadSub) loadSub.addEventListener('click', handleLoadFromSub);

        // Step 2
        const method = $('#cleanIpMethod');
        if (method) method.addEventListener('change', handleCleanIpMethodChange);
        const step2Next = $('#step2Next');
        if (step2Next) step2Next.addEventListener('click', handleStep2Next);
        const step2Back = $('#step2Back');
        if (step2Back) step2Back.addEventListener('click', () => goToStep(1));

        // Step 3
        const chainTypeEl = $('#chainType');
        if (chainTypeEl) chainTypeEl.addEventListener('change', handleChainTypeChange);
        const step3Next = $('#step3Next');
        if (step3Next) step3Next.addEventListener('click', handleStep3Next);
        const step3Back = $('#step3Back');
        if (step3Back) step3Back.addEventListener('click', () => goToStep(2));

        // Step 4
        const step4Test = $('#step4Test');
        if (step4Test) step4Test.addEventListener('click', handleStep4Test);
        const step4Back = $('#step4Back');
        if (step4Back) step4Back.addEventListener('click', () => goToStep(3));
        const step4Next = $('#step4Next');
        if (step4Next) step4Next.addEventListener('click', () => goToStep(5));

        // Step 5
        const step5Export = $('#step5Export');
        if (step5Export) step5Export.addEventListener('click', handleStep5Export);
        const step5Back = $('#step5Back');
        if (step5Back) step5Back.addEventListener('click', () => goToStep(4));
        const step5Download = $('#step5Download');
        if (step5Download) step5Download.addEventListener('click', handleStep5Download);

        // Copy buttons
        setupCopyButton('copyChainConfig', 'chainConfigCode');
        setupCopyButton('copyExport', 'exportCode');
    });
})();
