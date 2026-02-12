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

    // Pipeline proxy cache
    let pipelineProxies = [];   // [{ uri, protocol, address, port, remark, country, latency }]
    let pipelineLoaded = false;

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

    // --- Censorship Gauge ---
    function renderGauge(score, total) {
        const gaugeWrap = $('#diagGauge');
        const arc = $('#gaugeArc');
        const label = $('#gaugeScore');
        const caption = $('#gaugeCaption');
        const detail = $('#gaugeDetail');
        if (!gaugeWrap || !arc) return;

        gaugeWrap.style.display = 'flex';
        const pct = Math.round((score / total) * 100);
        // Arc length for a semicircle of radius 75: pi * 75 ≈ 235.6
        const arcLen = 235.6;
        const offset = arcLen - (arcLen * pct / 100);
        arc.style.strokeDasharray = arcLen;
        arc.style.strokeDashoffset = offset;

        // Color: green (>70) -> yellow (40-70) -> red (<40)
        let color, captionText, detailText;
        if (pct >= 75) {
            color = '#10b981';
            captionText = 'Minimal Censorship';
            detailText = 'Your network has good access. All strategies work: WARP, Proxy Cascade, Fragment, Worker, or direct.';
        } else if (pct >= 50) {
            color = '#3b82f6';
            captionText = 'Moderate Filtering';
            detailText = 'Some services are blocked. Try WARP, TLS Fragment, or Proxy Cascade through a local tool.';
        } else if (pct >= 25) {
            color = '#f59e0b';
            captionText = 'Heavy Censorship';
            detailText = 'Significant blocking. Try Proxy Cascade, Intranet Relay, Double WARP, or CDN Worker. Run lab-scanner.py --auto-chain.';
        } else {
            color = '#ef4444';
            captionText = 'Severe Restrictions';
            detailText = 'Very little is reachable. Use a local proxy as Layer 1, find a LAN relay (--scan-lan), or download lab-scanner.py for offline scanning.';
        }
        arc.style.stroke = color;
        if (label) { label.textContent = pct + '%'; label.style.color = color; }
        if (caption) { caption.textContent = captionText; caption.style.color = color; }
        if (detail) detail.textContent = detailText;
    }

    function renderHealthBadges(results) {
        const container = $('#diagBadges');
        if (!container) return;
        container.style.display = 'flex';
        container.innerHTML = '';
        const badges = [
            { key: 'cf', label: 'Cloudflare' },
            { key: 'google', label: 'Google' },
            { key: 'cf_tls', label: 'CF TLS' },
            { key: 'github', label: 'GitHub' },
            { key: 'wikipedia', label: 'Wikipedia' },
            { key: 'doh', label: 'DoH DNS' },
        ];
        for (const b of badges) {
            if (!(b.key in results)) continue;
            const cls = results[b.key] ? 'ok' : 'fail';
            const badge = document.createElement('span');
            badge.className = 'chain-health-badge ' + cls;
            badge.innerHTML = `<span class="dot"></span>${b.label}`;
            container.appendChild(badge);
        }
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
            { name: 'Wikipedia', url: 'https://en.wikipedia.org/w/api.php?action=sitematrix&format=json', key: 'wikipedia' },
            { name: 'Cloudflare DoH', url: 'https://cloudflare-dns.com/dns-query?dns=AAABAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE', key: 'doh' },
        ];
        const results = {};
        tbody.innerHTML = '';

        for (const t of tests) {
            const tr = document.createElement('tr');
            const start = performance.now();
            try {
                await fetch(t.url, { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(6000) });
                const lat = Math.round(performance.now() - start);
                results[t.key] = true;
                tr.innerHTML = `<td>${t.name}</td><td>${lat}ms</td><td class="status-ok">Reachable</td>`;
            } catch {
                results[t.key] = false;
                tr.innerHTML = `<td>${t.name}</td><td>-</td><td class="status-fail">Blocked</td>`;
            }
            tbody.appendChild(tr);
        }

        // Render gauge + badges
        const reachable = Object.values(results).filter(Boolean).length;
        renderGauge(reachable, tests.length);
        renderHealthBadges(results);

        // Advice — multi-strategy aware
        if (advice) {
            if (reachable >= 5) {
                showResult('diagAdvice', 'success',
                    '<strong>Excellent connectivity!</strong> All strategies work: ' +
                    'WARP, Proxy Cascade, TLS Fragment, CDN Worker, or direct connection. ' +
                    'Pick whichever is most convenient.');
            } else if (reachable >= 3) {
                showResult('diagAdvice', 'success',
                    '<strong>Good connectivity</strong> with some filtering. ' +
                    'Best strategies: <strong>WARP</strong>, <strong>Proxy Cascade</strong>, or <strong>TLS Fragment</strong>. ' +
                    'If you have a working local proxy (Psiphon, V2RayN), cascade through it.');
            } else if (results.cf || results.cf_tls) {
                showResult('diagAdvice', 'info',
                    '<strong>Cloudflare reachable</strong> but other sites are filtered. ' +
                    'Strategies: <strong>WARP chain</strong>, <strong>TLS Fragment</strong>, or <strong>Double WARP</strong>. ' +
                    'If you have a local proxy with broader access, try <strong>Proxy Cascade</strong> instead.');
            } else if (results.doh) {
                showResult('diagAdvice', 'info',
                    '<strong>DNS-over-HTTPS works</strong> but direct HTTPS is blocked. ' +
                    'Strategies: <strong>CDN Worker relay</strong>, <strong>Proxy Cascade</strong> through a local tool, ' +
                    'or <strong>Intranet Relay</strong> if a LAN host has less-filtered access. ' +
                    'Run <code>python lab-scanner.py --scan-lan</code> to find LAN relays.');
            } else if (reachable > 0) {
                showResult('diagAdvice', 'info',
                    '<strong>Limited access.</strong> Most services are blocked. ' +
                    'Strategies: Use a local proxy (Psiphon, Lantern, V2RayN, Tor) as Layer 1, ' +
                    'then <strong>cascade</strong> your destination proxy on top. ' +
                    'Or find a <strong>LAN relay</strong> with internet: <code>python lab-scanner.py --scan-lan</code>. ' +
                    'WARP may also work if stacked on top of the local proxy.');
            } else {
                showResult('diagAdvice', 'error',
                    '<strong>No direct internet detected.</strong> ' +
                    'Strategies: 1) Install Psiphon/Lantern/Tor as Layer 1, then cascade. ' +
                    '2) Find a LAN machine with internet: <code>python lab-scanner.py --scan-lan</code>. ' +
                    '3) Ask your network admin for proxy settings. ' +
                    '4) Run <code>python lab-scanner.py --auto-chain</code> for automatic path discovery (tries 6 strategies).');
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

    // --- Pipeline Proxy Integration ---
    const ROOT_PATH = window.ROOT_PATH || './';
    const API_BASE = `${ROOT_PATH}api/`;
    const STATIC_HOST_SUFFIXES = ['github.io', 'pages.dev', 'netlify.app'];
    const PIPELINE_BASE_CANDIDATES = Array.from(new Set([
        ROOT_PATH,
        `${ROOT_PATH}output/`,
        './',
        'output/',
    ]));

    function isStaticHosting() {
        const host = (window.location && window.location.hostname) || '';
        return STATIC_HOST_SUFFIXES.some((suffix) => host.includes(suffix));
    }

    function joinBase(base, file) {
        const cleanBase = String(base || '').replace(/\/+$/, '');
        const cleanFile = String(file || '').replace(/^\/+/, '');
        return `${cleanBase}/${cleanFile}`;
    }
    const PIPELINE_URLS = [
        'base64.txt',           // Base64-encoded URI list
        'base64-dns-safe.txt',  // DNS-safe variant (IP-only)
    ];

    async function fetchPipelineProxies() {
        if (pipelineLoaded) return pipelineProxies;
        const results = [];
        for (const file of PIPELINE_URLS) {
            for (const base of PIPELINE_BASE_CANDIDATES) {
                try {
                    const resp = await fetch(joinBase(base, file), { cache: 'no-store', signal: AbortSignal.timeout(8000) });
                    if (!resp.ok) continue;
                    const text = await resp.text();
                    // Decode base64
                    let decoded;
                    try { decoded = atob(text.trim()); } catch { decoded = text; }
                    const lines = decoded.split('\n').map(l => l.trim()).filter(Boolean);
                    for (const line of lines) {
                        const parsed = parseProxyUri(line);
                        if (parsed) {
                            results.push({
                                uri: line,
                                protocol: parsed.protocol,
                                address: parsed.address,
                                port: parsed.port,
                                remark: parsed.remark || `${parsed.protocol}@${parsed.address}`,
                            });
                        }
                        if (results.length >= 200) break; // Cap to avoid memory bloat
                    }
                    if (results.length > 0) break; // Got proxies from first successful location
                } catch { /* network error, try next */ }
            }
            if (results.length > 0) break; // Got proxies from first successful file
        }
        pipelineProxies = results;
        pipelineLoaded = true;
        return results;
    }

    async function handleLoadPipelineProxies() {
        const btn = document.getElementById('loadPipelineBtn');
        const select = document.getElementById('pipelineProxySelect');
        const container = document.getElementById('pipelineProxyPicker');
        if (!container) return;

        if (btn) btn.textContent = 'Loading...';
        const proxies = await fetchPipelineProxies();
        if (btn) btn.textContent = 'Load Pre-Tested Proxies';

        if (proxies.length === 0) {
            showResult('step1Result', 'info',
                '<strong>No pipeline proxies available.</strong> Paste your own proxy URI above, or run ' +
                '<code>python lab-scanner.py --test-proxy socks5://127.0.0.1:1080</code> to test a local proxy.');
            return;
        }

        // Group by protocol for easier browsing
        const grouped = {};
        for (const p of proxies) {
            const key = p.protocol.toUpperCase();
            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(p);
        }

        // Build select dropdown
        if (select) {
            select.innerHTML = '<option value="">-- Select a pre-tested proxy (' + proxies.length + ' available) --</option>';
            for (const [proto, list] of Object.entries(grouped)) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = proto + ' (' + list.length + ')';
                for (const p of list.slice(0, 30)) { // Show up to 30 per protocol
                    const opt = document.createElement('option');
                    opt.value = p.uri;
                    opt.textContent = p.remark.substring(0, 60) + ' (' + p.address + ':' + p.port + ')';
                    optgroup.appendChild(opt);
                }
                select.appendChild(optgroup);
            }
            select.style.display = '';
            select.onchange = function () {
                if (this.value) {
                    const input = $('#proxyUri');
                    if (input) input.value = this.value;
                }
            };
        }
        container.style.display = '';
        showResult('step1Result', 'success',
            '<strong>' + proxies.length + ' pre-tested proxies loaded</strong> from ConfigStream pipeline output. ' +
            'Select one from the dropdown or paste your own URI above.');
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
        'warp-psiphon': 'WARP + Psiphon: uses vwarp\'s --cfon to change the WARP exit country. Requires the vwarp binary.',
        'relay-chain': 'Up to 4 intermediate hops of any protocol (SOCKS5, HTTP, VLESS, VMess, Trojan, SS, WARP). Use local proxies, LAN relays, or pipeline proxies.',
        'fragment': 'Splits TLS handshake into small fragments to bypass stateless DPI. No tunnel needed.',
        'worker': 'Routes traffic through your own Cloudflare Worker. Unblockable private relay.',
        'custom': 'Define your own outbound chain in raw Sing-box JSON format.'
    };

    function handleChainTypeChange() {
        const ct = ($('#chainType') || {}).value || 'warp';
        const hint = $('#chainTypeHint');
        if (hint) hint.textContent = CHAIN_HINTS[ct] || '';

        const showWarp = ct === 'warp' || ct === 'warp-in-warp' || ct === 'warp-psiphon';
        const el = (id) => document.getElementById(id);
        if (el('warpOptions')) el('warpOptions').style.display = showWarp ? '' : 'none';
        if (el('warpInWarpRow')) el('warpInWarpRow').style.display = ct === 'warp-in-warp' ? '' : 'none';
        if (el('psiphonOptions')) el('psiphonOptions').style.display = ct === 'warp-psiphon' ? '' : 'none';
        if (el('fragmentOptions')) el('fragmentOptions').style.display = ct === 'fragment' ? '' : 'none';
        if (el('workerOptions')) el('workerOptions').style.display = ct === 'worker' ? '' : 'none';
        if (el('relayChainOptions')) el('relayChainOptions').style.display = ct === 'relay-chain' ? '' : 'none';
        if (el('customChainOptions')) el('customChainOptions').style.display = ct === 'custom' ? '' : 'none';

        // Update chain visual layer1 label
        const l1 = $('#chainLayer1Label');
        if (l1) {
            const labels = {
                'warp': 'WARP', 'warp-in-warp': 'WARP x2', 'warp-psiphon': 'WARP+Psiphon',
                'fragment': 'Fragment', 'worker': 'Worker', 'relay-chain': 'Relay', 'custom': 'Custom'
            };
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
        if (chainType === 'warp' || chainType === 'warp-in-warp' || chainType === 'warp-psiphon') {
            if (!selectedCleanIp) {
                showResult('step3Result', 'error', 'Please select a clean IP.');
                return;
            }
            const [warpIp, warpPort] = selectedCleanIp.split(':');
            if (chainType === 'warp-psiphon') {
                const psiphonCountry = ($('#psiphonCountry') || {}).value || 'US';
                chainConfig = buildSingboxChain(parsedProxy, warpIp, parseInt(warpPort) || 2408, warpKey, evasion);
                chainConfig._vwarp = {
                    psiphon: { enabled: true, country: psiphonCountry },
                    cli_hint: 'vwarp --cfon --country ' + psiphonCountry + ' --bind 127.0.0.1:8086'
                };
            } else if (chainType === 'warp-in-warp') {
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
        } else if (chainType === 'relay-chain') {
            const layers = collectRelayLayers();
            if (layers.length === 0) {
                showResult('step3Result', 'error', 'Please configure at least Layer 1 for the relay chain.');
                return;
            }
            chainConfig = buildRelayChain(parsedProxy, layers, evasion);
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

    // --- Relay Layer Helpers ---
    function collectRelayLayers() {
        // Read up to 4 layer slots from the relay chain UI
        const layers = [];
        for (let i = 1; i <= 4; i++) {
            const typeEl = document.querySelector(`.relay-layer-type[data-layer="${i}"]`);
            const addrEl = document.querySelector(`.relay-layer-addr[data-layer="${i}"]`);
            if (!typeEl || !addrEl) continue;
            const layerType = typeEl.value;
            const addr = (addrEl.value || '').trim();
            if (!layerType || !addr) continue;
            layers.push({ layerType, addr });
        }
        return layers;
    }

    function layerToOutbound(layerType, addr, tag) {
        // Convert a relay layer definition to a sing-box outbound object
        if (layerType === 'uri') {
            // Parse full proxy URI → full outbound
            const parsed = parseProxyUri(addr);
            if (parsed) {
                const out = buildProxyOutbound(parsed);
                out.tag = tag;
                return out;
            }
            // Fallback: treat as socks5 host:port
            layerType = 'socks5';
        }

        if (layerType === 'warp') {
            const parts = addr.includes(':') ? addr.split(':') : [addr, '2408'];
            return makeWarpOutbound(tag, parts[0], parseInt(parts[1]) || 2408, warpKey);
        }

        // socks5 or http
        const parts = addr.includes(':') ? addr.split(':') : [addr, '1080'];
        const out = {
            type: layerType === 'socks5' ? 'socks' : 'http',
            tag: tag,
            server: parts[0],
            server_port: parseInt(parts[1]) || 1080
        };
        if (layerType === 'socks5') out.version = '5';
        return out;
    }

    function buildRelayChain(proxy, layers, evasion) {
        // Chain: [You] → Layer1 → Layer2 → ... → Destination Proxy → Internet
        // layers: [{ layerType, addr }, ...] — up to 4 intermediate hops
        const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
        const outbounds = [proxyOut];

        // Build outbounds from innermost (closest to proxy) to outermost (closest to you)
        // The proxy detours through the first layer (closest to it), which detours through the next, etc.
        const layerOuts = layers.map((l, i) => layerToOutbound(l.layerType, l.addr, 'relay-layer' + (i + 1)));

        // Wire the chain: proxy → layerN → layerN-1 → ... → layer1 → Internet
        // layers[0] = outermost (closest to you), layers[last] = closest to proxy
        if (layerOuts.length > 0) {
            proxyOut.detour = layerOuts[layerOuts.length - 1].tag;
        }
        for (let i = layerOuts.length - 1; i > 0; i--) {
            layerOuts[i].detour = layerOuts[i - 1].tag;
        }
        // Layer 1 (outermost) has no detour — it connects directly to the network

        outbounds.push(...layerOuts.reverse()); // reverse so outermost is last in array
        return wrapConfig(outbounds, proxyOut.tag);
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

        if (isStaticHosting()) {
            showManualTestInstructions();
            return;
        }

        showResult('step4Result', 'pending', 'Testing chain connectivity... This may take up to 15 seconds.');
        const testBtn = $('#step4Test');
        if (testBtn) testBtn.disabled = true;

        try {
            // Try the backend test API if available
            const resp = await fetch(joinBase(API_BASE, 'lab/test-chain'), {
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

    function singboxOutboundToClash(sbOut) {
        // Convert a single sing-box outbound to Clash Meta/Mihomo YAML proxy block
        const t = sbOut.type;
        const name = sbOut.tag;
        const tls = sbOut.tls || {};
        const transport = sbOut.transport || {};
        const sni = tls.server_name || sbOut.server || '';

        // Helper: append transport lines for Mihomo (ws, grpc, h2, httpupgrade)
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
            // uTLS fingerprint
            if (tls.utls && tls.utls.fingerprint) lines += `\n    client-fingerprint: ${tls.utls.fingerprint}`;
            // ALPN
            if (tls.alpn && tls.alpn.length) lines += `\n    alpn:\n${tls.alpn.map(a => '      - ' + a).join('\n')}`;
            return lines;
        }

        // Reality block for Mihomo
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

    function buildClashYaml() {
        if (!chainConfig || !chainConfig.outbounds) return '# Error: missing chain config';
        // Filter out direct/block, build proxy blocks with dialer-proxy for chaining
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
        return `# ConfigStream Chain Config (Clash/Mihomo)
# Generated by ConfigStream Laboratory
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

    function singboxOutboundToXray(sbOut) {
        // Convert a single sing-box outbound to Xray/V2Ray format
        const xOut = { tag: sbOut.tag };
        const t = sbOut.type;

        // Helper: build Xray streamSettings from sing-box tls + transport
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
            // Reality support (VLESS)
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
            // Transport: ws, grpc, httpupgrade, h2
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
            // Xray-core supports WireGuard outbound natively (secretKey + peers format)
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
            // Xray does not support Hysteria2 natively — note for user
            xOut.protocol = 'freedom';
            xOut._note = 'Hysteria2 is not supported by Xray/V2Ray. Use sing-box for this protocol.';
        } else if (t === 'tuic') {
            xOut.protocol = 'freedom';
            xOut._note = 'TUIC is not supported by Xray/V2Ray. Use sing-box for this protocol.';
        } else {
            xOut.protocol = t || 'freedom';
        }
        // Chain: sing-box "detour" → Xray "proxySettings.tag"
        if (sbOut.detour) {
            xOut.proxySettings = { tag: sbOut.detour };
        }
        return xOut;
    }

    function buildXrayJson() {
        if (!chainConfig || !chainConfig.outbounds) return '{}';
        const xray = {
            log: { loglevel: 'warning' },
            inbounds: [{ tag: 'socks', port: 2080, listen: '127.0.0.1', protocol: 'socks', settings: { udp: true } }],
            outbounds: [],
            routing: { rules: [{ type: 'field', inboundTag: ['socks'], outboundTag: chainConfig.outbounds[0].tag }] }
        };
        // Convert each sing-box outbound to Xray format, preserving chain via proxySettings
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
        const loadPipeline = document.getElementById('loadPipelineBtn');
        if (loadPipeline) loadPipeline.addEventListener('click', handleLoadPipelineProxies);

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

        // Relay layer pipeline picker buttons
        document.querySelectorAll('.relay-pipeline-btn').forEach(btn => {
            btn.addEventListener('click', async function () {
                const layerIdx = this.dataset.layer;
                const addrInput = document.querySelector(`.relay-layer-addr[data-layer="${layerIdx}"]`);
                const typeSelect = document.querySelector(`.relay-layer-type[data-layer="${layerIdx}"]`);
                if (!addrInput) return;
                this.textContent = 'Loading...';
                const proxies = await fetchPipelineProxies();
                this.textContent = '\u{1F4E6} Pipeline';
                if (proxies.length === 0) {
                    showResult('step3Result', 'info', 'No pipeline proxies available. Paste a URI manually.');
                    return;
                }
                // Show a simple prompt with first 20 proxies
                const labels = proxies.slice(0, 20).map((p, i) => `${i + 1}. ${p.protocol.toUpperCase()} ${p.remark.substring(0, 40)} (${p.address}:${p.port})`);
                const choice = prompt('Select a pipeline proxy (enter number 1-' + Math.min(20, proxies.length) + '):\n\n' + labels.join('\n'));
                const idx = parseInt(choice);
                if (idx >= 1 && idx <= proxies.length) {
                    addrInput.value = proxies[idx - 1].uri;
                    if (typeSelect) typeSelect.value = 'uri';
                }
            });
        });

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
