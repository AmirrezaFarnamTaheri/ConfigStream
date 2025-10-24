/**
 * Health Score Calculator for Proxies
 * Calculates a 0-100 health score based on multiple factors
 */

function calculateHealthScore(proxy) {
    let score = 0;

    // Historical success rate (40 points) - default to neutral if no history
    score += 20.0; // Default neutral score

    // Latency score (30 points)
    if (proxy.latency !== null && proxy.latency !== undefined) {
        const latency = proxy.latency;
        const softCap = 5000; // milliseconds
        const center = Math.max(1.0, softCap * 0.6);
        const slope = Math.max(50.0, softCap * 0.2);
        const latencyPoints = 30.0 * (1.0 / (1.0 + Math.exp((latency - center) / slope)));
        score += latencyPoints;
    } else {
        score += 15.0; // Default neutral
    }

    // Security features (20 points)
    let securityScore = 0;
    if (proxy.details) {
        if (proxy.details.tls) securityScore += 10.0;
        if (proxy.details.aead) securityScore += 5.0;
        if (proxy.details.encryption) securityScore += 3.0;
    }
    if (proxy.dns_over_https_ok) securityScore += 2.0;
    score += Math.min(securityScore, 20.0);

    // Current working status (10 points)
    if (proxy.is_working) {
        score += 10.0;
    }

    // Ensure score is between 0 and 100
    return Math.round(Math.min(Math.max(score, 0.0), 100.0));
}

function getHealthScoreBadge(score) {
    if (score >= 80) {
        return {
            class: 'health-excellent',
            label: 'Excellent',
            icon: '⭐'
        };
    } else if (score >= 60) {
        return {
            class: 'health-good',
            label: 'Good',
            icon: '✓'
        };
    } else if (score >= 40) {
        return {
            class: 'health-fair',
            label: 'Fair',
            icon: '~'
        };
    } else {
        return {
            class: 'health-poor',
            label: 'Poor',
            icon: '⚠'
        };
    }
}

function renderHealthScoreBadge(score) {
    const badge = getHealthScoreBadge(score);
    return `
        <span class="health-score-badge ${badge.class}" title="Health Score: ${score}/100">
            <span class="health-score-icon">${badge.icon}</span>
            <span class="health-score-value">${score}</span>
        </span>
    `;
}
