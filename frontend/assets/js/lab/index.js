// ConfigStream Laboratory - Main Orchestrator
// SPDX-License-Identifier: AGPL-3.0-or-later

import { state, PIPELINE_URLS } from './state.js';
import { 
    $, $$, 
    normalizeProtocolName, 
    compareProtocols, 
    comparePipelineProxy, 
    escapeHtml, 
    isStaticHosting, 
    joinBase 
} from './utils.js';
import { 
    goToStep, 
    showResultText, 
    showResultHTML, 
    hideResult,
    renderGauge,
    renderHealthBadges
} from './ui.js';
import { parseProxyUri } from './parser.js';
import { handleStep2Next, handleCleanIpMethodChange } from './clean-ips.js';
import { 
    buildSingboxChain, 
    buildDoubleWarpChain, 
    buildFragmentChain, 
    buildWorkerChain, 
    buildRelayChain, 
    buildCustomChain,
    buildProxyOutbound,
    makeWarpOutbound
} from './builder.js';
import { runDiagnosis } from './network.js';
import * as exporters from './exporters.js';

// --- Local Proxy Testing ---
async function testLocalProxy() {
    const typeEl = $('#localProxyType');
    const addrEl = $('#localProxyAddr');
    const type = typeEl ? typeEl.value : '';
    const addr = addrEl ? addrEl.value : '';
    
    if (!type || !addr) {
        showResultText('localProxyResult', 'error', 'Select a proxy type and enter the address.');
        return;
    }
    const safeType = escapeHtml(type);
    const safeTypeLabel = escapeHtml(String(type).toUpperCase());
    const safeAddr = escapeHtml(addr);
    showResultText('localProxyResult', 'pending', `Testing ${safeType}://${safeAddr}...`);
    
    showResultHTML('localProxyResult', 'info',
        `<strong>Browser cannot test ${safeTypeLabel} proxies directly.</strong><br>` +
        `To verify, run in terminal:<br>` +
        `<code>curl -x ${safeType}://${safeAddr} --connect-timeout 5 http://cp.cloudflare.com/generate_204</code><br><br>` +
        `If it returns HTTP 204, your proxy works. It will be added as Layer 1 of your chain.`
    );
}

// --- Pipeline Proxy Integration ---
const ROOT_PATH = window.ROOT_PATH || './';
const API_BASE = `${ROOT_PATH}api/`;
const PIPELINE_BASE_CANDIDATES = Array.from(new Set([
    ROOT_PATH,
    `${ROOT_PATH}output/`,
    './',
    'output/',
]));

async function fetchPipelineProxies() {
    if (state.pipelineLoaded) return state.pipelineProxies;
    const results = [];
    for (const file of PIPELINE_URLS) {
        for (const base of PIPELINE_BASE_CANDIDATES) {
            try {
                const resp = await fetch(joinBase(base, file), { cache: 'no-store', signal: AbortSignal.timeout(8000) });
                if (!resp.ok) continue;
                const text = await resp.text();
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
                    if (results.length >= 200) break;
                }
                if (results.length > 0) break;
            } catch { /* next */ }
        }
        if (results.length > 0) break;
    }
    results.sort(comparePipelineProxy);
    state.pipelineProxies = results;
    state.pipelineLoaded = true;
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
        showResultHTML('step1Result', 'info',
            '<strong>No pipeline proxies available.</strong> Paste your own proxy URI above, or run ' +
            '<code>python lab-scanner.py --test-proxy socks5://127.0.0.1:1080</code> to test a local proxy.');
        return;
    }

    const grouped = {};
    for (const p of proxies) {
        const key = normalizeProtocolName(p.protocol);
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(p);
    }

    if (select) {
        select.replaceChildren();
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = `-- Select a pre-tested proxy (${proxies.length} available) --`;
        select.appendChild(emptyOption);
        
        const orderedProtocols = Object.keys(grouped).sort(compareProtocols);
        for (const proto of orderedProtocols) {
            const list = grouped[proto].slice().sort(comparePipelineProxy);
            const optgroup = document.createElement('optgroup');
            optgroup.label = proto.toUpperCase() + ' (' + list.length + ')';
            for (const p of list.slice(0, 30)) {
                const opt = document.createElement('option');
                opt.value = p.uri;
                opt.textContent = p.remark.substring(0, 60) + ' (' + p.address + ':' + p.port + ')';
                optgroup.appendChild(opt);
            }
            select.appendChild(optgroup);
        }
        select.style.display = '';
        select.addEventListener('change', function () {
            if (this.value) {
                const input = $('#proxyUri');
                if (input) input.value = this.value;
            }
        });
    }
    container.style.display = '';
    showResultHTML('step1Result', 'success',
        `<strong>${proxies.length} pre-tested proxies loaded</strong> from ConfigStream pipeline output. ` +
        `Select one from the dropdown or paste your own URI above.`);
}

// --- Step Handlers ---

function handleStep1Next() {
    const uriInput = $('#proxyUri');
    const uriText = uriInput ? uriInput.value : '';
    const lines = uriText.split('\n').map(l => l.trim()).filter(Boolean);
    state.parsedProxy = null;

    for (const line of lines) {
        const parsed = parseProxyUri(line);
        if (parsed) {
            state.parsedProxy = parsed;
            state.parsedProxy.config = line;
            break;
        }
    }

    if (!state.parsedProxy) {
        showResultText('step1Result', 'error', 'Could not parse proxy URI. Ensure it starts with a valid protocol (vless://, vmess://, trojan://, ss://, etc.).');
        return;
    }

    showResultHTML('step1Result', 'success',
        `<strong>Parsed:</strong> ${escapeHtml(state.parsedProxy.protocol.toUpperCase())} @ ${escapeHtml(state.parsedProxy.address)}:${escapeHtml(state.parsedProxy.port)}` +
        (state.parsedProxy.remark ? ` (${escapeHtml(state.parsedProxy.remark)})` : '')
    );

    setTimeout(() => goToStep(2), 600);
}

function handleChainTypeChange() {
    const chainTypeEl = $('#chainType');
    const ct = chainTypeEl ? chainTypeEl.value : 'warp';
    const s = state.strategyManifest[ct];
    if (!s) return;

    const hint = $('#chainTypeHint');
    if (hint) hint.textContent = s.hint || '';

    const activePanels = new Set(s.panels || []);
    ['warpOptions', 'warpInWarpRow', 'psiphonOptions', 'fragmentOptions', 'workerOptions', 'relayChainOptions', 'customChainOptions'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = activePanels.has(id) ? '' : 'none';
    });

    const l1 = $('#chainLayer1Label');
    if (l1) l1.textContent = s.visual_label || s.label || 'WARP';
}

function getEvasionOptions() {
    return {
        fingerprint: ($('#tlsFingerprint') || {}).value || '',
        alpn: ($('#alpnProtocol') || {}).value || '',
        mux: ($('#muxProtocol') || {}).value || '',
        muxPadding: ($('#muxPadding') || {}).value === 'true',
        tfo: ($('#tcpFastOpen') || {}).value === 'true',
        mptcp: ($('#mptcp') || {}).value === 'true',
        tlsPadding: ($('#tlsPadding') || {}).value === 'true',
        ech: (($('#echConfig') || {}).value || '').trim()
    };
}

function handleEvasionPresetChange() {
    const preset = ($('#evasionPreset') || {}).value || 'custom';
    if (preset === 'custom') return;

    const fp = $('#tlsFingerprint');
    const alpn = $('#alpnProtocol');
    const mux = $('#muxProtocol');
    const muxPad = $('#muxPadding');
    const tfo = $('#tcpFastOpen');
    const mptcp = $('#mptcp');
    const padding = $('#tlsPadding');
    const ech = $('#echConfig');

    if (preset === 'default') {
        if (fp) fp.value = 'chrome';
        if (alpn) alpn.value = '';
        if (mux) mux.value = '';
        if (muxPad) muxPad.value = 'false';
        if (tfo) tfo.value = 'false';
        if (mptcp) mptcp.value = 'false';
        if (padding) padding.value = 'false';
        if (ech) ech.value = '';
    } else if (preset === 'hardened') {
        if (fp) fp.value = 'randomized';
        if (alpn) alpn.value = 'h2,http/1.1';
        if (mux) mux.value = 'h2mux';
        if (muxPad) muxPad.value = 'true';
        if (tfo) tfo.value = 'true';
        if (mptcp) mptcp.value = 'true';
        if (padding) padding.value = 'true';
        if (ech) ech.value = '';
    } else if (preset === 'latency') {
        if (fp) fp.value = 'chrome';
        if (alpn) alpn.value = 'h2';
        if (mux) mux.value = 'yamux';
        if (muxPad) muxPad.value = 'true';
        if (tfo) tfo.value = 'true';
        if (mptcp) mptcp.value = 'true';
        if (padding) padding.value = 'false';
        if (ech) ech.value = '';
    } else if (preset === 'strict') {
        if (fp) fp.value = 'random';
        if (alpn) alpn.value = 'h2';
        if (mux) mux.value = '';
        if (muxPad) muxPad.value = 'false';
        if (tfo) tfo.value = 'true';
        if (mptcp) mptcp.value = 'false';
        if (padding) padding.value = 'true';
        if (ech) ech.value = 'QH46SgAhBgAQA2VjaC1wYXRjaC1zYW1wbGUAAAEAAQABAQAA';
    }
}

function setupPresetResetListeners() {
    const selectors = [
        '#tlsFingerprint', '#alpnProtocol', '#muxProtocol',
        '#muxPadding', '#tcpFastOpen', '#mptcp', '#tlsPadding', '#echConfig'
    ];
    selectors.forEach(sel => {
        $(sel)?.addEventListener('change', () => {
            const preset = $('#evasionPreset');
            if (preset) preset.value = 'custom';
        });
    });
}

function collectRelayLayers() {
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
    if (layerType === 'uri') {
        const parsed = parseProxyUri(addr);
        if (parsed) {
            const out = buildProxyOutbound(parsed);
            out.tag = tag;
            return out;
        }
        layerType = 'socks5';
    }

    if (layerType === 'warp') {
        const parts = addr.includes(':') ? addr.split(':') : [addr, '2408'];
        return makeWarpOutbound(tag, parts[0], parseInt(parts[1]) || 2408, state.warpKey);
    }

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

function handleStep3Next() {
    const chainType = ($('#chainType') || {}).value || 'warp';
    state.selectedCleanIp = ($('#warpCleanIp') || {}).value || '';
    state.warpKey = ($('#warpKeyInput') || {}).value || '';

    if (!state.parsedProxy) {
        showResultText('step3Result', 'error', 'No base proxy configured. Go back to Step 1.');
        return;
    }

    const evasion = getEvasionOptions();
    const localType = ($('#localProxyType') || {}).value || '';
    const localAddr = ($('#localProxyAddr') || {}).value || '';

    if (['warp', 'vwarp-masque', 'vwarp-atomic', 'warp-in-warp', 'warp-psiphon'].includes(chainType)) {
        if (!state.selectedCleanIp) {
            showResultText('step3Result', 'error', 'Please select a clean IP.');
            return;
        }
        const [warpIp, warpPort] = state.selectedCleanIp.split(':');
        if (chainType === 'vwarp-masque') {
            state.chainConfig = buildSingboxChain(state.parsedProxy, warpIp, parseInt(warpPort) || 2408, state.warpKey, evasion);
            state.chainConfig._vwarp = { masque: { enabled: true, noize: 'gfw' }, cli_hint: 'vwarp --gfw --bind 127.0.0.1:8086' };
        } else if (chainType === 'vwarp-atomic') {
            state.chainConfig = buildSingboxChain(state.parsedProxy, warpIp, parseInt(warpPort) || 2408, state.warpKey, evasion);
            state.chainConfig._vwarp = { atomic_noize: { enabled: true, preset: 'moderate' }, cli_hint: 'vwarp --noise moderate --bind 127.0.0.1:8086' };
        } else if (chainType === 'warp-psiphon') {
            const psiphonCountry = ($('#psiphonCountry') || {}).value || 'US';
            state.chainConfig = buildSingboxChain(state.parsedProxy, warpIp, parseInt(warpPort) || 2408, state.warpKey, evasion);
            state.chainConfig._vwarp = { psiphon: { enabled: true, country: psiphonCountry }, cli_hint: 'vwarp --cfon --country ' + psiphonCountry + ' --bind 127.0.0.1:8086' };
        } else if (chainType === 'warp-in-warp') {
            const outer = ($('#warp2CleanIp') || {}).value || state.selectedCleanIp;
            const outerKey = ($('#warp2Key') || {}).value || '';
            state.chainConfig = buildDoubleWarpChain(state.parsedProxy, warpIp, parseInt(warpPort) || 2408, state.warpKey, outer, outerKey, evasion);
        } else {
            state.chainConfig = buildSingboxChain(state.parsedProxy, warpIp, parseInt(warpPort) || 2408, state.warpKey, evasion);
        }
        const wd = $('#chainWarpIp');
        if (wd) wd.textContent = warpIp + ':' + (warpPort || 2408);
    } else if (chainType === 'fragment') {
        const fragSize = ($('#fragSize') || {}).value || '10-30';
        const fragDelay = ($('#fragDelay') || {}).value || '5-10';
        state.chainConfig = buildFragmentChain(state.parsedProxy, fragSize, fragDelay, evasion);
    } else if (chainType === 'worker') {
        const workerUrl = ($('#workerUrl') || {}).value || '';
        if (!workerUrl) {
            showResultText('step3Result', 'error', 'Please enter your Worker URL.');
            return;
        }
        state.chainConfig = buildWorkerChain(state.parsedProxy, workerUrl, evasion);
    } else if (chainType === 'relay-chain') {
        const layers = collectRelayLayers();
        if (layers.length === 0) {
            showResultText('step3Result', 'error', 'Please configure at least Layer 1.');
            return;
        }
        const layerOuts = layers.map((l, i) => layerToOutbound(l.layerType, l.addr, 'relay-layer' + (i + 1)));
        state.chainConfig = buildRelayChain(state.parsedProxy, layerOuts, evasion);
    } else if (chainType === 'custom') {
        try {
            const raw = ($('#customOutboundsJson') || {}).value || '[]';
            const custom = JSON.parse(raw);
            state.chainConfig = buildCustomChain(state.parsedProxy, custom, evasion);
        } catch (e) {
            showResultText('step3Result', 'error', 'Invalid JSON: ' + escapeHtml(e.message));
            return;
        }
    } else {
        showResultText('step3Result', 'error', 'Unsupported chain strategy: ' + escapeHtml(chainType));
        return;
    }

    if (localType && localAddr && state.chainConfig && state.chainConfig.outbounds) {
        const [lHost, lPort] = localAddr.includes(':') ? localAddr.split(':') : [localAddr, '1080'];
        const localOut = { type: localType === 'socks5' ? 'socks' : 'http', tag: 'layer1-local', server: lHost, server_port: parseInt(lPort) || 1080 };
        if (localType === 'socks5') localOut.version = '5';
        const tunnelOuts = state.chainConfig.outbounds.filter(o => o.tag !== 'direct' && o.tag !== 'block' && o.tag !== 'proxy-chain');
        if (tunnelOuts.length > 0) {
            tunnelOuts[tunnelOuts.length - 1].detour = 'layer1-local';
        }
        state.chainConfig.outbounds.push(localOut);
    }

    const pl = $('#chainProxyLabel');
    const pd = $('#chainProxyDetail');
    if (pl) pl.textContent = state.parsedProxy.protocol.toUpperCase();
    if (pd) pd.textContent = state.parsedProxy.address;

    showResultText('step3Result', 'success', 'Chain configuration generated! Proceed to test it.');
    setTimeout(() => {
        goToStep(4);
        updateStep4TestMode();
        const preview = $('#chainConfigPreview');
        const code = $('#chainConfigCode');
        if (preview && code) {
            code.textContent = JSON.stringify(state.chainConfig, null, 2);
            preview.style.display = 'block';
        }
    }, 500);
}

function updateStep4TestMode() {
    const mode = $('#step4Mode');
    const testBtn = $('#step4Test');
    if (!mode) return;

    if (isStaticHosting()) {
        mode.className = 'lab-test-result info';
        showResultHTML('step4Mode', 'info', '<strong>Manual test mode.</strong> Static hosting cannot run server-side proxy tests; use the sing-box instructions below.');
        if (testBtn) testBtn.textContent = 'Show Manual Test';
    } else {
        mode.className = 'lab-test-result success';
        showResultHTML('step4Mode', 'success', '<strong>Live test mode.</strong> This page can try the backend Lab endpoint.');
        if (testBtn) testBtn.textContent = 'Run Live Test';
    }
}

async function handleStep4Test() {
    if (!state.chainConfig) {
        showResultText('step4Result', 'error', 'No chain config. Go back to Step 3.');
        return;
    }
    if (isStaticHosting()) {
        showManualTestInstructions();
        return;
    }
    showResultText('step4Result', 'pending', 'Testing chain connectivity... (max 15s)');
    const testBtn = $('#step4Test');
    if (testBtn) testBtn.disabled = true;

    try {
        const resp = await fetch(joinBase(API_BASE, 'lab/test-chain'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: state.chainConfig })
        });
        if (resp.ok) {
            const result = await resp.json();
            if (result.success) {
                showResultHTML('step4Result', 'success', `<strong>Chain is working!</strong> Latency: ${escapeHtml(result.latency || 'N/A')}ms` + (result.exit_ip ? ` | Exit IP: ${escapeHtml(result.exit_ip)}` : ''));
                const nextBtn = $('#step4Next');
                if (nextBtn) nextBtn.disabled = false;
            } else {
                showResultHTML('step4Result', 'error', `<strong>Test failed:</strong> ${escapeHtml(result.error || 'Unknown error')}`);
            }
        } else {
            showManualTestInstructions();
        }
    } catch {
        showManualTestInstructions();
    }
    if (testBtn) testBtn.disabled = false;
}

function showManualTestInstructions() {
    showResultHTML('step4Result', 'info',
        '<strong>Live test unavailable.</strong><br><br>' +
        'To test manually:<br>' +
        '1. Save config to <code>chain.json</code><br>' +
        '2. Run: <code>sing-box run -c chain.json</code><br>' +
        '3. Browser proxy to <code>127.0.0.1:2080</code><br><br>' +
        'If it works, click "Continue to Export".'
    );
    const nextBtn = $('#step4Next');
    if (nextBtn) nextBtn.disabled = false;
}

function handleStep5Export() {
    if (!state.chainConfig) {
        showResultText('step5Result', 'error', 'No chain config.');
        return;
    }
    const format = ($('#exportFormat') || {}).value || 'singbox';
    
    if (format === 'qr') {
        generateQR(state.parsedProxy ? state.parsedProxy.config : '');
        showResultText('step5Result', 'success', 'Offline QR payload ready. Copy it into a trusted local QR tool or VPN client.');
        return;
    }

    let content = '';
    let filename = 'configstream-chain';

    switch (format) {
        case 'singbox': content = JSON.stringify(state.chainConfig, null, 2); filename += '.json'; break;
        case 'clash': content = exporters.buildClashYaml(state.chainConfig); filename += '.yaml'; break;
        case 'xray': content = exporters.buildXrayJson(state.chainConfig); filename += '-xray.json'; break;
        case 'nekobox': content = exporters.buildNekoboxLink(state.chainConfig); filename += '-nekobox.txt'; break;
        case 'uri': content = state.parsedProxy ? state.parsedProxy.config : ''; filename += '.txt'; break;
        case 'script-python': content = exporters.buildPythonScript(state.chainConfig); filename += '.py'; break;
        case 'script-bash': content = exporters.buildBashScript(state.chainConfig); filename += '.sh'; break;
        default: content = JSON.stringify(state.chainConfig, null, 2); filename += '.json';
    }

    const codeEl = $('#exportCode');
    if (codeEl) {
        codeEl.textContent = content;
        $('#exportOutput').style.display = 'block';
    }
    $('#qrOutput').style.display = 'none';
    window._labExportContent = content;
    window._labExportFilename = filename;
    showResultText('step5Result', 'success', `${escapeHtml(format.toUpperCase())} export ready.`);
}

function handleStep5Download() {
    const content = window._labExportContent;
    const filename = window._labExportFilename;
    if (!content) return;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'configstream-chain.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

function setupCopyButton(btnId, codeId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener('click', () => {
        const code = document.getElementById(codeId);
        if (!code) return;
        navigator.clipboard.writeText(code.textContent).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
        });
    });
}

async function handleLoadFromSub() {
    try {
        const resp = await fetch((window.ROOT_PATH || '') + 'proxies.txt?cb=' + Date.now());
        if (!resp.ok) throw new Error();
        const text = await resp.text();
        const lines = text.split('\n').filter(l => l.trim());
        if (lines.length > 0) {
            $('#proxyUri').value = lines[0];
            showResultText('step1Result', 'info', `Loaded ${lines.length} proxy(s). First selected.`);
        }
    } catch {
        showResultText('step1Result', 'error', 'Could not load subscription.');
    }
}

function generateQR(text) {
    const qrDiv = $('#qrOutput');
    if (!qrDiv) return;
    qrDiv.replaceChildren();
    const payload = text || '';
    const panel = document.createElement('div');
    panel.className = 'lab-result info';

    const title = document.createElement('strong');
    title.textContent = 'Offline QR payload';
    const note = document.createElement('p');
    note.textContent = 'External QR services are disabled so proxy material never leaves your browser. Copy this payload or scan the offline QR code below.';

    // QR Code SVG rendering
    const qrWrapper = document.createElement('div');
    qrWrapper.className = 'lab-qr-wrapper';
    qrWrapper.style.background = '#fff';
    qrWrapper.style.padding = '10px';
    qrWrapper.style.display = 'inline-block';
    qrWrapper.style.marginTop = '1rem';
    qrWrapper.style.borderRadius = '5px';

    try {
        if (typeof QRCode !== 'undefined') {
            const qr = new QRCode({
                content: payload,
                padding: 2,
                width: 256,
                height: 256,
                color: '#000000',
                background: '#ffffff',
                ecl: 'M'
            });
            appendSafeSvg(qrWrapper, qr.svg());
        } else {
            qrWrapper.textContent = 'QR renderer unavailable offline.';
        }
    } catch (e) {
        console.error('QR rendering failed:', e);
        qrWrapper.textContent = 'Error rendering QR code.';
    }

    const code = document.createElement('pre');
    code.className = 'lab-code';
    code.style.whiteSpace = 'pre-wrap';
    code.style.wordBreak = 'break-all';
    code.textContent = payload;

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'lab-btn lab-btn-secondary';
    copyBtn.textContent = 'Copy Payload';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(payload).then(() => {
            copyBtn.textContent = 'Copied';
            setTimeout(() => { copyBtn.textContent = 'Copy Payload'; }, 1500);
        }).catch(() => {
            const range = document.createRange();
            range.selectNodeContents(code);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            document.execCommand('copy');
            copyBtn.textContent = 'Copied';
            setTimeout(() => { copyBtn.textContent = 'Copy Payload'; }, 1500);
        });
    });

    panel.append(title, note, qrWrapper, code, copyBtn);
    qrDiv.appendChild(panel);
    qrDiv.style.display = 'block';
    $('#exportOutput').style.display = 'none';
}

function appendSafeSvg(container, svgMarkup) {
    const parsed = new DOMParser().parseFromString(String(svgMarkup || ''), 'image/svg+xml');
    if (parsed.querySelector('parsererror')) {
        throw new Error('QR SVG parser rejected generated markup.');
    }

    const svg = parsed.documentElement;
    if (!svg || svg.localName !== 'svg') {
        throw new Error('QR renderer returned a non-SVG payload.');
    }

    svg.querySelectorAll('script, foreignObject, iframe, object, embed').forEach(node => node.remove());
    svg.querySelectorAll('*').forEach(node => {
        [...node.attributes].forEach(attr => {
            const name = attr.name.toLowerCase();
            const value = attr.value || '';
            if (name.startsWith('on')) {
                node.removeAttribute(attr.name);
                return;
            }
            if ((name === 'href' || name.endsWith(':href')) && /^(javascript|data|vbscript):/i.test(value.replace(/[\u0000-\u0020]/g, ''))) {
                node.removeAttribute(attr.name);
            }
        });
    });

    container.appendChild(document.importNode(svg, true));
}

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const resp = await fetch((window.ROOT_PATH || '') + 'assets/data/lab_strategies.json?cb=' + Date.now());
        if (resp.ok) {
            const data = await resp.json();
            const select = $('#chainType');
            if (select) {
                select.replaceChildren();
                data.strategies.forEach(s => {
                    state.strategyManifest[s.id] = s;
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = s.label;
                    select.appendChild(opt);
                });
                handleChainTypeChange();
            }
        }
    } catch (e) { console.error(e); }

    updateStep4TestMode();
    $$('.lab-step-dot').forEach(dot => {
        dot.addEventListener('click', () => {
            const step = parseInt(dot.dataset.step);
            if (step <= state.currentStep) goToStep(step);
        });
    });

    $('#runDiagnosis')?.addEventListener('click', runDiagnosis);
    $('#testLocalProxy')?.addEventListener('click', testLocalProxy);
    $('#step1Next')?.addEventListener('click', handleStep1Next);
    $('#loadFromSub')?.addEventListener('click', handleLoadFromSub);
    document.getElementById('loadPipelineBtn')?.addEventListener('click', handleLoadPipelineProxies);
    $('#cleanIpMethod')?.addEventListener('change', handleCleanIpMethodChange);
    $('#step2Next')?.addEventListener('click', handleStep2Next);
    $('#step2Back')?.addEventListener('click', () => goToStep(1));
    $('#chainType')?.addEventListener('change', handleChainTypeChange);
    $('#step3Next')?.addEventListener('click', handleStep3Next);
    $('#step3Back')?.addEventListener('click', () => goToStep(2));
    $('#step4Test')?.addEventListener('click', handleStep4Test);
    $('#step4Back')?.addEventListener('click', () => goToStep(3));
    $('#step4Next')?.addEventListener('click', () => goToStep(5));
    $('#step5Export')?.addEventListener('click', handleStep5Export);
    $('#step5Back')?.addEventListener('click', () => goToStep(4));
    $('#step5Download')?.addEventListener('click', handleStep5Download);
    setupCopyButton('copyChainConfig', 'chainConfigCode');
    setupCopyButton('copyExport', 'exportCode');
    
    // Evasion Presets Setup
    $('#evasionPreset')?.addEventListener('change', handleEvasionPresetChange);
    setupPresetResetListeners();

    // Relay layer pipeline picker
    document.querySelectorAll('.relay-pipeline-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const layerIdx = this.dataset.layer;
            const addrInput = document.querySelector(`.relay-layer-addr[data-layer="${layerIdx}"]`);
            const typeSelect = document.querySelector(`.relay-layer-type[data-layer="${layerIdx}"]`);
            if (!addrInput) return;
            this.textContent = 'Loading...';
            const proxies = await fetchPipelineProxies();
            this.textContent = '\u{1F4E6} Pipeline';
            if (proxies.length === 0) return;
            const labels = proxies.slice(0, 20).map((p, i) => `${i + 1}. ${p.protocol.toUpperCase()} ${p.remark.substring(0, 40)}`);
            const choice = prompt('Select (1-' + labels.length + '):\n\n' + labels.join('\n'));
            const idx = parseInt(choice);
            if (idx >= 1 && idx <= proxies.length) {
                addrInput.value = proxies[idx - 1].uri;
                if (typeSelect) typeSelect.value = 'uri';
            }
        });
    });
});
