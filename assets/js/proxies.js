// Page-specific logic for the proxies page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('proxiesTable')) return;

    let allProxies = [];
    let currentSort = { key: 'latency', asc: true };
    let currentPage = 1;
    let proxiesPerPage = 50; // Default value, can be changed by the user

    const protocolFilter = document.getElementById('filterProtocol');
    const countryFilter = document.getElementById('filterCountry');
    const cityFilter = document.getElementById('filterCity');
    const tableBody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    const proxiesTable = document.getElementById('proxiesTable');
    const clearFiltersBtn = document.getElementById('clearFilters');
    const copyFilteredBtn = document.getElementById('copyFiltered');
    const downloadFilteredBtn = document.getElementById('downloadFiltered');
    const filterCount = document.getElementById('filterCount');
    const latencyMinInput = document.getElementById('filterLatencyMin');
    const latencyMaxInput = document.getElementById('filterLatencyMax');
    const paginationContainer = document.getElementById('pagination-container');
    const pageSizeSelector = document.getElementById('pageSize');

    // Early return if required elements don't exist
    if (!protocolFilter || !countryFilter || !tableBody || !emptyState) return;

    const getFilteredProxies = () => {
        const protoFilter = protocolFilter.value.toLowerCase();
        const countryFilterValue = countryFilter.value.toLowerCase();
        const cityFilterValue = cityFilter.value.toLowerCase();
        const latencyMin = latencyMinInput && latencyMinInput.value ? parseInt(latencyMinInput.value) : null;
        const latencyMax = latencyMaxInput && latencyMaxInput.value ? parseInt(latencyMaxInput.value) : null;

        return allProxies.filter(p => {
            const protocol = p.protocol.toLowerCase();
            const country = p.country_code ? p.country_code.toLowerCase() : '';
            const city = p.city ? p.city.toLowerCase() : '';
            const latency = p.latency || 0;

            const matchesProtocol = protoFilter === '' || protocol.includes(protoFilter);
            const matchesCountry = countryFilterValue === '' || country.includes(countryFilterValue);
            const matchesCity = cityFilterValue === '' || city.includes(cityFilterValue);
            const matchesLatencyMin = latencyMin === null || latency >= latencyMin;
            const matchesLatencyMax = latencyMax === null || latency <= latencyMax;

            return matchesProtocol && matchesCountry && matchesCity && matchesLatencyMin && matchesLatencyMax;
        });
    };

    const renderTable = () => {
        const filteredProxies = getFilteredProxies();

        // Update filter count
        if (filterCount) {
            const fallbackMode = allProxies.some(proxy => proxy.source === 'fallback');
            const fallbackNote = fallbackMode ? ' (fallback data)' : '';
            filterCount.textContent = `Showing ${filteredProxies.length} of ${allProxies.length} proxies${fallbackNote}`;
        }

        if (filteredProxies.length === 0) {
            proxiesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
        } else {
            proxiesTable.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }

        // Sort
        filteredProxies.sort((a, b) => {
            let valA, valB;
            if (currentSort.key === 'location') {
                valA = a.country_code || '';
                valB = b.country_code || '';
            } else {
                valA = a[currentSort.key];
                valB = b[currentSort.key];
            }

            if (valA < valB) return currentSort.asc ? -1 : 1;
            if (valA > valB) return currentSort.asc ? 1 : -1;
            return 0;
        });

        // Clamp currentPage to valid range after filtering/sorting
        const maxPage = Math.ceil(filteredProxies.length / proxiesPerPage) || 1;
        currentPage = Math.max(1, Math.min(currentPage, maxPage));

        const indexOfLastProxy = currentPage * proxiesPerPage;
        const indexOfFirstProxy = indexOfLastProxy - proxiesPerPage;
        const currentProxies = filteredProxies.slice(indexOfFirstProxy, indexOfLastProxy);

        tableBody.innerHTML = currentProxies.map((p, index) => {
            // Handle XX or unknown country codes
            const countryCode = (p.country_code && p.country_code !== 'XX') ? p.country_code : null;
            const country = countryCode || 'Unknown';
            const city = p.city || '';
            const location = city ? `${city}, ${country}` : country;
            const latency = p.latency ? `${p.latency}ms` : 'N/A';
            const protocol = p.protocol || 'N/A';
            const config = p.config || '';
            const rowClasses = ['proxy-row'];
            if (p.source === 'fallback') {
                rowClasses.push('proxy-row--fallback');
            }
            if (!p.is_working) {
                rowClasses.push('proxy-row--offline');
            }
            return `
                <tr class="${rowClasses.join(' ')}" style="--delay: ${index * 0.03}s" data-source="${p.source}">
                    <td>${protocol}${p.is_working ? '' : ' <span class="status-pill status-pill--offline">Offline</span>'}</td>
                    <td class="location-cell">
                        ${countryCode ? `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" alt="${countryCode}" class="country-flag" onerror="this.onerror=null;this.outerHTML='<i data-feather=\\\'globe\\\' class=\\\'country-flag-icon\\\'></i>'">` : `<i data-feather="globe" class="country-flag-icon"></i>`}
                        <span>${location}</span>
                    </td>
                    <td>${latency}</td>
                    <td><button class="btn btn-secondary copy-btn" data-config="${encodeURIComponent(config)}" aria-label="Copy proxy link"><i data-feather="copy"></i></button></td>
                </tr>
            `;
        }).join('');
        if (window.inlineIcons) {
            window.inlineIcons.replace();
        }

        renderPagination(filteredProxies.length);
    };

    const renderPagination = (totalProxies) => {
        const totalPages = Math.ceil(totalProxies / proxiesPerPage) || 1;

        let paginationHTML = '';

        // Previous Button
        paginationHTML += `<button class="pagination-btn" id="first-btn" ${currentPage === 1 ? 'disabled' : ''}>&laquo; First</button>`;
        paginationHTML += `<button class="pagination-btn" id="prev-btn" ${currentPage === 1 ? 'disabled' : ''}>&lsaquo; Prev</button>`;

        // Page numbers with ellipsis
        const maxPagesToShow = 5;
        let startPage, endPage;

        if (totalPages <= maxPagesToShow) {
            startPage = 1;
            endPage = totalPages;
        } else {
            if (currentPage <= Math.floor(maxPagesToShow / 2)) {
                startPage = 1;
                endPage = maxPagesToShow;
            } else if (currentPage + Math.floor(maxPagesToShow / 2) >= totalPages) {
                startPage = totalPages - maxPagesToShow + 1;
                endPage = totalPages;
            } else {
                startPage = currentPage - Math.floor(maxPagesToShow / 2);
                endPage = currentPage + Math.floor(maxPagesToShow / 2);
            }
        }

        if (startPage > 1) {
            paginationHTML += `<button class="pagination-btn" data-page="1">1</button>`;
            if (startPage > 2) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
            paginationHTML += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
        }

        // Next Button
        paginationHTML += `<button class="pagination-btn" id="next-btn" ${currentPage === totalPages ? 'disabled' : ''}>Next &rsaquo;</button>`;
        paginationHTML += `<button class="pagination-btn" id="last-btn" ${currentPage === totalPages ? 'disabled' : ''}>Last &raquo;</button>`;

        paginationContainer.innerHTML = paginationHTML;
    };

    paginationContainer.addEventListener('click', (e) => {
        const totalPages = Math.ceil(getFilteredProxies().length / proxiesPerPage) || 1;
        if (e.target.matches('#first-btn')) {
            currentPage = 1;
            renderTable();
        } else if (e.target.matches('#prev-btn')) {
            currentPage = Math.max(1, currentPage - 1);
            renderTable();
        } else if (e.target.matches('#next-btn')) {
            currentPage = Math.min(totalPages, currentPage + 1);
            renderTable();
        } else if (e.target.matches('#last-btn')) {
            currentPage = totalPages;
            renderTable();
        } else if (e.target.matches('.pagination-btn[data-page]')) {
            currentPage = parseInt(e.target.dataset.page);
            renderTable();
        }
    });

    // Add event listeners for filters
    protocolFilter.addEventListener('input', renderTable);
    countryFilter.addEventListener('input', () => {
        const selectedOption = countryFilter.options[countryFilter.selectedIndex];
        const countryCode = selectedOption.dataset.countryCode || '';
        updateFlagDisplay(countryCode, 'country');
        updateBackgroundGradient(countryCode);
        renderTable();
    });
    cityFilter.addEventListener('input', () => {
        const selectedOption = cityFilter.options[cityFilter.selectedIndex];
        const countryCode = selectedOption.dataset.countryCode || '';
        updateFlagDisplay(countryCode, 'city');
        renderTable();
    });

    if (latencyMinInput) {
        latencyMinInput.addEventListener('input', renderTable);
    }
    if (latencyMaxInput) {
        latencyMaxInput.addEventListener('input', renderTable);
    }
    if (pageSizeSelector) {
        pageSizeSelector.addEventListener('change', (e) => {
            proxiesPerPage = parseInt(e.target.value);
            currentPage = 1; // Reset to first page
            renderTable();
        });
    }

    // Batch actions
    if (copyFilteredBtn) {
        copyFilteredBtn.addEventListener('click', () => {
            const proxies = getFilteredProxies();
            const configs = proxies.map(p => p.config).join('\n');
            copyToClipboard(configs, copyFilteredBtn);
        });
    }

    if (downloadFilteredBtn) {
        downloadFilteredBtn.addEventListener('click', () => {
            const proxies = getFilteredProxies();
            const configs = proxies.map(p => p.config).join('\n');
            const blob = new Blob([configs], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'filtered_proxies.txt';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
    }

    // Clear filters button
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            protocolFilter.value = '';
            countryFilter.value = '';
            cityFilter.value = '';
            if (latencyMinInput) latencyMinInput.value = '';
            if (latencyMaxInput) latencyMaxInput.value = '';
            updateFlagDisplay('', 'country');
            updateFlagDisplay('', 'city');
            updateBackgroundGradient('');
            renderTable();
        });
    }

    document.querySelectorAll('#proxiesTable th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            if (currentSort.key === sortKey) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.key = sortKey;
                currentSort.asc = true;
            }

            document.querySelectorAll('#proxiesTable th[data-sort]').forEach(header => {
                if (header !== th) {
                    header.removeAttribute('aria-sort');
                }
            });
            th.setAttribute('aria-sort', currentSort.asc ? 'ascending' : 'descending');

            renderTable();
        });
    });

    // Helper function to get country name from country code
    function getCountryName(countryCode) {
        const countryNames = {
            'XX': 'Unknown',
            'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada', 'DE': 'Germany',
            'FR': 'France', 'NL': 'Netherlands', 'SG': 'Singapore', 'JP': 'Japan',
            'AU': 'Australia', 'IN': 'India', 'BR': 'Brazil', 'RU': 'Russia',
            'CN': 'China', 'HK': 'Hong Kong', 'KR': 'South Korea', 'IT': 'Italy',
            'ES': 'Spain', 'SE': 'Sweden', 'CH': 'Switzerland', 'PL': 'Poland'
        };
        return countryNames[countryCode] || countryCode;
    }

    // Helper function to update flag displays
    function updateFlagDisplay(countryCode, type = 'country') {
        const displayEl = type === 'country'
            ? document.getElementById('countryFlagDisplay')
            : document.getElementById('cityFlagDisplay');

        if (!displayEl) return;

        if (!countryCode || countryCode === '') {
            displayEl.innerHTML = '<i data-feather="globe" class="country-flag-icon-small"></i>';
            if (window.inlineIcons) window.inlineIcons.replace();
        } else {
            displayEl.innerHTML = `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" alt="${countryCode}" onerror="this.outerHTML='<i data-feather=\\'globe\\' class=\\'country-flag-icon-small\\'></i>'">`;
        }
    }

    // Helper function to update background gradient based on country flag colors
    function updateBackgroundGradient(countryCode) {
        // Comprehensive map of country codes to their flag colors with enhanced gradients
        const countryColors = {
            // Americas
            'US': { primary: '#B22234', secondary: '#3C3B6E', accent: '#FFFFFF' }, // Red, Blue, White
            'CA': { primary: '#FF0000', secondary: '#FFFFFF', accent: '#FF0000' }, // Red and White
            'BR': { primary: '#009B3A', secondary: '#FEDD00', accent: '#002776' }, // Green, Yellow, Blue
            'MX': { primary: '#006847', secondary: '#CE1126', accent: '#FFFFFF' }, // Green, Red, White
            'AR': { primary: '#74ACDF', secondary: '#FFFFFF', accent: '#FCBF49' }, // Blue, White, Yellow
            'CL': { primary: '#0039A6', secondary: '#FFFFFF', accent: '#D52B1E' }, // Blue, White, Red
            'CO': { primary: '#FCD116', secondary: '#003893', accent: '#CE1126' }, // Yellow, Blue, Red
            'PE': { primary: '#D91023', secondary: '#FFFFFF', accent: '#D91023' }, // Red and White
            'VE': { primary: '#FFCC00', secondary: '#00247D', accent: '#CF142B' }, // Yellow, Blue, Red

            // Europe
            'GB': { primary: '#012169', secondary: '#C8102E', accent: '#FFFFFF' }, // Blue, Red, White
            'DE': { primary: '#000000', secondary: '#DD0000', accent: '#FFCE00' }, // Black, Red, Yellow
            'FR': { primary: '#002395', secondary: '#FFFFFF', accent: '#ED2939' }, // Blue, White, Red
            'IT': { primary: '#009246', secondary: '#FFFFFF', accent: '#CE2B37' }, // Green, White, Red
            'ES': { primary: '#AA151B', secondary: '#F1BF00', accent: '#AA151B' }, // Red and Yellow
            'NL': { primary: '#AE1C28', secondary: '#FFFFFF', accent: '#21468B' }, // Red, White, Blue
            'SE': { primary: '#006AA7', secondary: '#FECC00', accent: '#006AA7' }, // Blue and Yellow
            'CH': { primary: '#FF0000', secondary: '#FFFFFF', accent: '#FF0000' }, // Red and White
            'PL': { primary: '#FFFFFF', secondary: '#DC143C', accent: '#DC143C' }, // White and Red
            'BE': { primary: '#000000', secondary: '#FDDA24', accent: '#EF3340' }, // Black, Yellow, Red
            'AT': { primary: '#ED2939', secondary: '#FFFFFF', accent: '#ED2939' }, // Red and White
            'NO': { primary: '#BA0C2F', secondary: '#00205B', accent: '#FFFFFF' }, // Red, Blue, White
            'DK': { primary: '#C8102E', secondary: '#FFFFFF', accent: '#C8102E' }, // Red and White
            'FI': { primary: '#003580', secondary: '#FFFFFF', accent: '#003580' }, // Blue and White
            'PT': { primary: '#006600', secondary: '#FF0000', accent: '#FFE900' }, // Green, Red, Yellow
            'GR': { primary: '#0D5EAF', secondary: '#FFFFFF', accent: '#0D5EAF' }, // Blue and White
            'CZ': { primary: '#11457E', secondary: '#FFFFFF', accent: '#D7141A' }, // Blue, White, Red
            'HU': { primary: '#CE2939', secondary: '#FFFFFF', accent: '#477050' }, // Red, White, Green
            'RO': { primary: '#002B7F', secondary: '#FCD116', accent: '#CE1126' }, // Blue, Yellow, Red
            'IE': { primary: '#169B62', secondary: '#FFFFFF', accent: '#FF883E' }, // Green, White, Orange
            'UA': { primary: '#0057B7', secondary: '#FFDD00', accent: '#0057B7' }, // Blue and Yellow
            'RU': { primary: '#FFFFFF', secondary: '#0039A6', accent: '#D52B1E' }, // White, Blue, Red

            // Asia-Pacific
            'SG': { primary: '#EF3340', secondary: '#FFFFFF', accent: '#EF3340' }, // Red and White
            'JP': { primary: '#BC002D', secondary: '#FFFFFF', accent: '#BC002D' }, // Red and White
            'CN': { primary: '#DE2910', secondary: '#FFDE00', accent: '#DE2910' }, // Red and Yellow
            'HK': { primary: '#DE2910', secondary: '#FFFFFF', accent: '#DE2910' }, // Red and White
            'KR': { primary: '#FFFFFF', secondary: '#CD2E3A', accent: '#0047A0' }, // White, Red, Blue
            'IN': { primary: '#FF9933', secondary: '#FFFFFF', accent: '#138808' }, // Orange, White, Green
            'AU': { primary: '#012169', secondary: '#FFFFFF', accent: '#E4002B' }, // Blue, White, Red
            'NZ': { primary: '#00247D', secondary: '#FFFFFF', accent: '#CC142B' }, // Blue, White, Red
            'TH': { primary: '#A51931', secondary: '#F4F5F8', accent: '#2D2A4A' }, // Red, White, Blue
            'MY': { primary: '#CC0001', secondary: '#FFFFFF', accent: '#010066' }, // Red, White, Blue
            'ID': { primary: '#FF0000', secondary: '#FFFFFF', accent: '#FF0000' }, // Red and White
            'PH': { primary: '#0038A8', secondary: '#CE1126', accent: '#FCD116' }, // Blue, Red, Yellow
            'VN': { primary: '#DA251D', secondary: '#FFFF00', accent: '#DA251D' }, // Red and Yellow
            'PK': { primary: '#01411C', secondary: '#FFFFFF', accent: '#01411C' }, // Green and White
            'BD': { primary: '#006A4E', secondary: '#F42A41', accent: '#006A4E' }, // Green and Red
            'LK': { primary: '#8B0000', secondary: '#FFB300', accent: '#006600' }, // Maroon, Yellow, Green
            'MM': { primary: '#FECB00', secondary: '#EA2839', accent: '#34B233' }, // Yellow, Red, Green
            'KH': { primary: '#032EA1', secondary: '#E00025', accent: '#FFFFFF' }, // Blue, Red, White
            'TW': { primary: '#FE0000', secondary: '#000095', accent: '#FFFFFF' }, // Red, Blue, White

            // Middle East & Africa
            'AE': { primary: '#00732F', secondary: '#FF0000', accent: '#000000' }, // Green, Red, Black
            'SA': { primary: '#165C2B', secondary: '#FFFFFF', accent: '#165C2B' }, // Green and White
            'IL': { primary: '#0038B8', secondary: '#FFFFFF', accent: '#0038B8' }, // Blue and White
            'TR': { primary: '#E30A17', secondary: '#FFFFFF', accent: '#E30A17' }, // Red and White
            'IR': { primary: '#239F40', secondary: '#FFFFFF', accent: '#DA0000' }, // Green, White, Red
            'EG': { primary: '#CE1126', secondary: '#FFFFFF', accent: '#000000' }, // Red, White, Black
            'ZA': { primary: '#007A4D', secondary: '#FFB81C', accent: '#DE3831' }, // Green, Yellow, Red
            'NG': { primary: '#008751', secondary: '#FFFFFF', accent: '#008751' }, // Green and White
            'KE': { primary: '#000000', secondary: '#BB0000', accent: '#006600' }, // Black, Red, Green
            'MA': { primary: '#C1272D', secondary: '#006233', accent: '#C1272D' }, // Red and Green
        };

        const body = document.body;
        const colorScheme = countryColors[countryCode];

        if (colorScheme) {
            // Create sophisticated gradient with country colors
            const gradient = `linear-gradient(135deg, ${colorScheme.primary} 0%, ${colorScheme.secondary} 50%, ${colorScheme.accent} 100%)`;

            // Apply smooth transition to body background
            body.style.transition = 'background 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
            body.style.background = gradient;

            // Also update CSS custom properties for consistent theming
            const root = document.documentElement;
            root.style.setProperty('--country-primary', colorScheme.primary);
            root.style.setProperty('--country-secondary', colorScheme.secondary);
            root.style.setProperty('--country-accent', colorScheme.accent);

            // Add subtle overlay color to cards and elements
            root.style.setProperty('--country-overlay', `${colorScheme.primary}15`);
        } else {
            // Reset to default background with smooth transition
            body.style.transition = 'background 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
            body.style.background = '';

            // Reset custom properties
            const root = document.documentElement;
            root.style.removeProperty('--country-primary');
            root.style.removeProperty('--country-secondary');
            root.style.removeProperty('--country-accent');
            root.style.removeProperty('--country-overlay');
        }
    }

    // Populate filter dropdowns dynamically with only available options
    function populateFilters() {
        // Get unique protocols, countries and cities (excluding XX and invalid values)
        const protocols = new Set();
        const countries = new Set();
        const cities = new Set();
        const cityToCountry = new Map(); // Map cities to their country codes

        allProxies.forEach(p => {
            if (p.protocol) protocols.add(p.protocol);
            // Exclude empty country codes
            if (p.country_code) {
                countries.add(p.country_code);
                if (p.city) {
                    cities.add(p.city);
                    cityToCountry.set(p.city, p.country_code);
                }
            }
        });

        // Populate protocol filter
        const sortedProtocols = Array.from(protocols).sort();
        protocolFilter.length = 1; // Preserve "All Protocols"
        sortedProtocols.forEach(protocol => {
            const option = document.createElement('option');
            option.value = protocol;
            option.textContent = protocol.toUpperCase();
            protocolFilter.appendChild(option);
        });

        // Sort and populate country filter with flags
        const sortedCountries = Array.from(countries).sort();
        countryFilter.length = 1; // Preserve "All Countries"
        sortedCountries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = country; // Only show country code
            option.dataset.countryCode = country;
            countryFilter.appendChild(option);
        });

        // Sort and populate city filter
        const sortedCities = Array.from(cities).sort();
        cityFilter.length = 1; // Preserve "All Cities"
        sortedCities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            const countryCode = cityToCountry.get(city) || '';
            option.textContent = countryCode ? `${city} (${countryCode})` : city;
            option.dataset.countryCode = countryCode;
            cityFilter.appendChild(option);
        });

        // Store city to country mapping for later use
        window.cityToCountryMap = cityToCountry;
    }

    async function fetchAndRenderProxies() {
        const loadingContainer = document.getElementById('loadingContainer');
        const proxiesTable = document.getElementById('proxiesTable');

        if (loadingContainer) loadingContainer.classList.remove('hidden');
        proxiesTable.classList.add('hidden');

        try {
            allProxies = await window.api.fetchProxies();
            const fallbackMode = allProxies.some(proxy => proxy.source === 'fallback');
            if (fallbackMode && window.stateManager) {
                window.stateManager.setInfo('Showing the most recent tested proxies because no verified proxies are currently online.', true);
            }
            populateFilters();
            renderTable();
        } catch (error) {
            if (window.stateManager) {
                window.stateManager.setError('Failed to load proxies.', error);
            }
        } finally {
            if (loadingContainer) loadingContainer.classList.add('hidden');
        }
    }

    fetchAndRenderProxies();
});