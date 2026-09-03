/**
 * Render the shared public-artifact trust banner.
 *
 * Callers retain ownership of their data state and may override copy or the
 * retry callback, while all routes use the same DOM and accessibility contract.
 */
export function renderTrustState(state, metadata, options = {}) {
    let banner = document.getElementById('trustStateBanner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'trustStateBanner';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'polite');
        banner.style.cssText = 'position:sticky;top:0;z-index:9999;padding:0.65rem 1rem;text-align:center;font:600 0.875rem/1.4 system-ui,sans-serif;display:none;';
        const main = document.querySelector('main') || document.body;
        if (main && main.firstChild) {
            main.insertBefore(banner, main.firstChild);
        } else if (main) {
            main.appendChild(banner);
        }
    }

    banner.className = `trust-banner trust-banner--${state}`;
    if (state === 'stale') {
        const updatedAt = metadata?.last_updated_utc;
        const parsedUpdatedAt = updatedAt ? new Date(updatedAt) : null;
        const generatedAt = parsedUpdatedAt && !Number.isNaN(parsedUpdatedAt.getTime())
            ? parsedUpdatedAt.toISOString()
            : (metadata?.generated_at || 'Unknown');
        banner.textContent = `Warning: Showing cached telemetry generated at ${generatedAt}.`;
        banner.style.background = '#d97706';
        banner.style.color = '#fff';
        banner.style.display = 'block';
        return;
    }

    if (state === 'invalid') {
        banner.textContent = 'Security Alert: Detached cryptographic verification failed. Feeds blocked.';
        banner.style.background = '#dc2626';
        banner.style.color = '#fff';
        banner.style.display = 'block';
        return;
    }

    if (state === 'error' || state === 'empty') {
        banner.replaceChildren();
        const message = document.createElement('span');
        message.textContent = options.errorMessage || (
            state === 'empty' ? 'No telemetry data available.' : 'Failed to initialize page data.'
        );
        banner.appendChild(message);
        if (typeof options.onRetry === 'function') {
            const retryButton = document.createElement('button');
            retryButton.className = 'btn btn-secondary trust-banner-retry';
            retryButton.style.cssText = 'margin-left:12px;padding:2px 8px;font-size:0.8rem;cursor:pointer;';
            retryButton.textContent = 'Retry';
            retryButton.addEventListener('click', (event) => {
                event.preventDefault();
                options.onRetry();
            });
            banner.appendChild(retryButton);
        }
        banner.style.background = '#4b5563';
        banner.style.color = '#fff';
        banner.style.display = 'block';
        return;
    }

    banner.style.display = 'none';
}
