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
    const copyAllBtn = document.getElementById('copyAll');
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
            } else if (currentSort.key === 'health') {
                valA = a.uptime || 0;
                valB = b.uptime || 0;
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
            const remarks = p.remarks || 'N/A';
            const uptime = p.uptime !== undefined ? (p.uptime * 100).toFixed(2) : 'N/A';
            let healthStatus = 'na';
            if (uptime > 95) healthStatus = 'high';
            else if (uptime > 80) healthStatus = 'medium';
            else if (uptime !== 'N/A') healthStatus = 'low';

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
                    <td class="proxy-name-cell" title="${remarks}">${remarks}</td>
                    <td class="location-cell">
                        ${countryCode ? `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" alt="${countryCode}" class="country-flag" onerror="this.onerror=null;this.outerHTML='<i data-feather=\\\'globe\\\' class=\\\'country-flag-icon\\\'></i>'">` : `<i data-feather="globe" class="country-flag-icon"></i>`}
                        <span>${location}</span>
                    </td>
                    <td>${latency}</td>
                    <td class="health-cell">
                        <span class="health-indicator health-indicator--${healthStatus}"></span>
                        <span>${uptime}%</span>
                    </td>
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

        // If a city is selected, automatically select the corresponding country
        if (countryCode) {
            countryFilter.value = countryCode;
            // Manually trigger the input event to update the country flag and background
            countryFilter.dispatchEvent(new Event('input'));
        }

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
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', () => {
            const configs = allProxies.map(p => p.config).join('\n');
            copyToClipboard(configs, copyAllBtn);
        });
    }

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
            'AF': 'Afghanistan',
            'AX': 'Åland Islands',
            'AL': 'Albania',
            'DZ': 'Algeria',
            'AS': 'American Samoa',
            'AD': 'Andorra',
            'AO': 'Angola',
            'AI': 'Anguilla',
            'AQ': 'Antarctica',
            'AG': 'Antigua and Barbuda',
            'AR': 'Argentina',
            'AM': 'Armenia',
            'AW': 'Aruba',
            'AU': 'Australia',
            'AT': 'Austria',
            'AZ': 'Azerbaijan',
            'BS': 'Bahamas',
            'BH': 'Bahrain',
            'BD': 'Bangladesh',
            'BB': 'Barbados',
            'BY': 'Belarus',
            'BE': 'Belgium',
            'BZ': 'Belize',
            'BJ': 'Benin',
            'BM': 'Bermuda',
            'BT': 'Bhutan',
            'BO': 'Bolivia',
            'BQ': 'Bonaire, Sint Eustatius and Saba',
            'BA': 'Bosnia and Herzegovina',
            'BW': 'Botswana',
            'BV': 'Bouvet Island',
            'BR': 'Brazil',
            'IO': 'British Indian Ocean Territory',
            'BN': 'Brunei Darussalam',
            'BG': 'Bulgaria',
            'BF': 'Burkina Faso',
            'BI': 'Burundi',
            'CV': 'Cabo Verde',
            'KH': 'Cambodia',
            'CM': 'Cameroon',
            'CA': 'Canada',
            'KY': 'Cayman Islands',
            'CF': 'Central African Republic',
            'TD': 'Chad',
            'CL': 'Chile',
            'CN': 'China',
            'CX': 'Christmas Island',
            'CC': 'Cocos (Keeling) Islands',
            'CO': 'Colombia',
            'KM': 'Comoros',
            'CD': 'Congo (the Democratic Republic of the)',
            'CG': 'Congo',
            'CK': 'Cook Islands',
            'CR': 'Costa Rica',
            'CI': 'Côte d\'Ivoire',
            'HR': 'Croatia',
            'CU': 'Cuba',
            'CW': 'Curaçao',
            'CY': 'Cyprus',
            'CZ': 'Czechia',
            'DK': 'Denmark',
            'DJ': 'Djibouti',
            'DM': 'Dominica',
            'DO': 'Dominican Republic',
            'EC': 'Ecuador',
            'EG': 'Egypt',
            'SV': 'El Salvador',
            'GQ': 'Equatorial Guinea',
            'ER': 'Eritrea',
            'EE': 'Estonia',
            'SZ': 'Eswatini',
            'ET': 'Ethiopia',
            'FK': 'Falkland Islands (Malvinas)',
            'FO': 'Faroe Islands',
            'FJ': 'Fiji',
            'FI': 'Finland',
            'FR': 'France',
            'GF': 'French Guiana',
            'PF': 'French Polynesia',
            'TF': 'French Southern Territories',
            'GA': 'Gabon',
            'GM': 'Gambia',
            'GE': 'Georgia',
            'DE': 'Germany',
            'GH': 'Ghana',
            'GI': 'Gibraltar',
            'GR': 'Greece',
            'GL': 'Greenland',
            'GD': 'Grenada',
            'GP': 'Guadeloupe',
            'GU': 'Guam',
            'GT': 'Guatemala',
            'GG': 'Guernsey',
            'GN': 'Guinea',
            'GW': 'Guinea-Bissau',
            'GY': 'Guyana',
            'HT': 'Haiti',
            'HM': 'Heard Island and McDonald Islands',
            'VA': 'Holy See',
            'HN': 'Honduras',
            'HK': 'Hong Kong',
            'HU': 'Hungary',
            'IS': 'Iceland',
            'IN': 'India',
            'ID': 'Indonesia',
            'IR': 'Iran',
            'IQ': 'Iraq',
            'IE': 'Ireland',
            'IM': 'Isle of Man',
            'IL': 'Israel',
            'IT': 'Italy',
            'JM': 'Jamaica',
            'JP': 'Japan',
            'JE': 'Jersey',
            'JO': 'Jordan',
            'KZ': 'Kazakhstan',
            'KE': 'Kenya',
            'KI': 'Kiribati',
            'KP': 'Korea (the Democratic People\'s Republic of)',
            'KR': 'Korea (the Republic of)',
            'KW': 'Kuwait',
            'KG': 'Kyrgyzstan',
            'LA': 'Lao People\'s Democratic Republic',
            'LV': 'Latvia',
            'LB': 'Lebanon',
            'LS': 'Lesotho',
            'LR': 'Liberia',
            'LY': 'Libya',
            'LI': 'Liechtenstein',
            'LT': 'Lithuania',
            'LU': 'Luxembourg',
            'MO': 'Macao',
            'MG': 'Madagascar',
            'MW': 'Malawi',
            'MY': 'Malaysia',
            'MV': 'Maldives',
            'ML': 'Mali',
            'MT': 'Malta',
            'MH': 'Marshall Islands',
            'MQ': 'Martinique',
            'MR': 'Mauritania',
            'MU': 'Mauritius',
            'YT': 'Mayotte',
            'MX': 'Mexico',
            'FM': 'Micronesia (Federated States of)',
            'MD': 'Moldova',
            'MC': 'Monaco',
            'MN': 'Mongolia',
            'ME': 'Montenegro',
            'MS': 'Montserrat',
            'MA': 'Morocco',
            'MZ': 'Mozambique',
            'MM': 'Myanmar',
            'NA': 'Namibia',
            'NR': 'Nauru',
            'NP': 'Nepal',
            'NL': 'Netherlands',
            'NC': 'New Caledonia',
            'NZ': 'New Zealand',
            'NI': 'Nicaragua',
            'NE': 'Niger',
            'NG': 'Nigeria',
            'NU': 'Niue',
            'NF': 'Norfolk Island',
            'MK': 'North Macedonia',
            'MP': 'Northern Mariana Islands',
            'NO': 'Norway',
            'OM': 'Oman',
            'PK': 'Pakistan',
            'PW': 'Palau',
            'PS': 'Palestine, State of',
            'PA': 'Panama',
            'PG': 'Papua New Guinea',
            'PY': 'Paraguay',
            'PE': 'Peru',
            'PH': 'Philippines',
            'PN': 'Pitcairn',
            'PL': 'Poland',
            'PT': 'Portugal',
            'PR': 'Puerto Rico',
            'QA': 'Qatar',
            'RE': 'Réunion',
            'RO': 'Romania',
            'RU': 'Russian Federation',
            'RW': 'Rwanda',
            'BL': 'Saint Barthélemy',
            'SH': 'Saint Helena, Ascension and Tristan da Cunha',
            'KN': 'Saint Kitts and Nevis',
            'LC': 'Saint Lucia',
            'MF': 'Saint Martin (French part)',
            'PM': 'Saint Pierre and Miquelon',
            'VC': 'Saint Vincent and the Grenadines',
            'WS': 'Samoa',
            'SM': 'San Marino',
            'ST': 'Sao Tome and Principe',
            'SA': 'Saudi Arabia',
            'SN': 'Senegal',
            'RS': 'Serbia',
            'SC': 'Seychelles',
            'SL': 'Sierra Leone',
            'SG': 'Singapore',
            'SX': 'Sint Maarten (Dutch part)',
            'SK': 'Slovakia',
            'SI': 'Slovenia',
            'SB': 'Solomon Islands',
            'SO': 'Somalia',
            'ZA': 'South Africa',
            'GS': 'South Georgia and the South Sandwich Islands',
            'SS': 'South Sudan',
            'ES': 'Spain',
            'LK': 'Sri Lanka',
            'SD': 'Sudan',
            'SR': 'Suriname',
            'SJ': 'Svalbard and Jan Mayen',
            'SE': 'Sweden',
            'CH': 'Switzerland',
            'SY': 'Syrian Arab Republic',
            'TW': 'Taiwan (Province of China)',
            'TJ': 'Tajikistan',
            'TZ': 'Tanzania, United Republic of',
            'TH': 'Thailand',
            'TL': 'Timor-Leste',
            'TG': 'Togo',
            'TK': 'Tokelau',
            'TO': 'Tonga',
            'TT': 'Trinidad and Tobago',
            'TN': 'Tunisia',
            'TR': 'Türkiye',
            'TM': 'Turkmenistan',
            'TC': 'Turks and Caicos Islands',
            'TV': 'Tuvalu',
            'UG': 'Uganda',
            'UA': 'Ukraine',
            'AE': 'United Arab Emirates',
            'GB': 'United Kingdom of Great Britain and Northern Ireland',
            'UM': 'United States Minor Outlying Islands',
            'US': 'United States of America',
            'UY': 'Uruguay',
            'UZ': 'Uzbekistan',
            'VU': 'Vanuatu',
            'VE': 'Venezuela (Bolivarian Republic of)',
            'VN': 'Viet Nam',
            'VG': 'Virgin Islands (British)',
            'VI': 'Virgin Islands (U.S.)',
            'WF': 'Wallis and Futuna',
            'EH': 'Western Sahara',
            'YE': 'Yemen',
            'ZM': 'Zambia',
            'ZW': 'Zimbabwe'
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
            'AE': ['#00732F', '#FFFFFF', '#FF0000', '#000000'],
            'AF': ['#000000', '#FFFFFF', '#C00000', '#009900'],
            'AG': ['#000000', '#FFFFFF', '#CF142B', '#FFC72C', '#0072C6'],
            'AI': ['#00205B', '#FFFFFF', '#CF142B'],
            'AL': ['#FF0000', '#000000'],
            'AM': ['#D90012', '#0033A0', '#F2A800'],
            'AO': ['#C8102E', '#FFC90E', '#000000'],
            'AR': ['#74ACDF', '#FFFFFF'],
            'AT': ['#ED2939', '#FFFFFF'],
            'AU': ['#00008B', '#FFFFFF', '#FF0000'],
            'AW': ['#0062E1', '#FCD116'],
            'AZ': ['#009EAA', '#ED2939', '#3F9C35'],
            'BA': ['#003882', '#FECB00', '#FFFFFF'],
            'BB': ['#00267F', '#FFC72C', '#000000'],
            'BD': ['#006A4E', '#F42A41'],
            'BE': ['#000000', '#FAE042', '#ED2939'],
            'BF': ['#EF2B2D', '#009E49', '#FCD116'],
            'BG': ['#FFFFFF', '#00966E', '#D62612'],
            'BH': ['#FFFFFF', '#CE1126'],
            'BI': ['#CE1126', '#1EB53A', '#FFFFFF'],
            'BJ': ['#008751', '#FCD116', '#E8112D'],
            'BM': ['#CF142B', '#FFFFFF', '#00205B'],
            'BN': ['#FFFFFF', '#FCE300', '#000000'],
            'BO': ['#D52B1E', '#F9E300', '#007934'],
            'BR': ['#009B3A', '#FFCC29', '#002776'],
            'BS': ['#00778B', '#FFC72C', '#000000'],
            'BT': ['#FF9933', '#FFC500', '#FFFFFF'],
            'BW': ['#000000', '#FFFFFF', '#75AADB'],
            'BY': ['#CF142B', '#009A44', '#FFFFFF'],
            'BZ': ['#00388E', '#D9002C', '#FFFFFF'],
            'CA': ['#FF0000', '#FFFFFF'],
            'CD': ['#007FFF', '#F7D618', '#CE1021'],
            'CF': ['#003082', '#FFFFFF', '#FFCE00', '#289728', '#D21034'],
            'CG': ['#009543', '#FBDE4A', '#DC241F'],
            'CH': ['#FF0000', '#FFFFFF'],
            'CI': ['#FF8F00', '#FFFFFF', '#009E60'],
            'CL': ['#0033A0', '#FFFFFF', '#DA291C'],
            'CM': ['#007A5E', '#FCD116', '#CE1126'],
            'CN': ['#EE1C25', '#FFFF00'],
            'CO': ['#FCD116', '#003893', '#CE1126'],
            'CR': ['#002B7F', '#FFFFFF', '#CE1126'],
            'CU': ['#002A8F', '#FFFFFF', '#CF142B'],
            'CV': ['#003881', '#FFFFFF', '#CF2027', '#F7D116'],
            'CY': ['#D47600', '#FFFFFF', '#4D5600'],
            'CZ': ['#FFFFFF', '#D7141A', '#11457E'],
            'DE': ['#000000', '#DD0000', '#FFCE00'],
            'DJ': ['#6AB2E7', '#12AD2B', '#FFFFFF'],
            'DK': ['#C60C30', '#FFFFFF'],
            'DM': ['#006B3F', '#FFFFFF', '#000000', '#FFC72C', '#D41C30'],
            'DO': ['#002D62', '#FFFFFF', '#CE1126'],
            'DZ': ['#006233', '#FFFFFF', '#D21034'],
            'EC': ['#FFD100', '#0033A0', '#EC1C24'],
            'EE': ['#0072CE', '#000000', '#FFFFFF'],
            'EG': ['#CE1126', '#FFFFFF', '#000000'],
            'EH': ['#000000', '#FFFFFF', '#007A3D', '#C4111B'],
            'ER': ['#EA0437', '#4189DD', '#12AD2B', '#FFB900'],
            'ES': ['#AA151B', '#F1BF00'],
            'ET': ['#078930', '#FCDD09', '#DA121A', '#0F47AF'],
            'FI': ['#003580', '#FFFFFF'],
            'FJ': ['#68B4E1', '#FFFFFF', '#002868', '#CF142B'],
            'FM': ['#75AADB', '#FFFFFF'],
            'FR': ['#002395', '#FFFFFF', '#ED2939'],
            'GA': ['#009E60', '#FCD116', '#3A75C4'],
            'GB': ['#00247D', '#FFFFFF', '#CF142B'],
            'GD': ['#007A5E', '#FCD116', '#CE1126'],
            'GE': ['#FFFFFF', '#FF0000'],
            'GF': ['#289728', '#FFD100'],
            'GG': ['#E8112D', '#FFFFFF'],
            'GH': ['#CF142B', '#FCD116', '#006B3F', '#000000'],
            'GI': ['#FFFFFF', '#CE1126'],
            'GL': ['#FFFFFF', '#D00C33'],
            'GM': ['#CE1126', '#FFFFFF', '#0C1C8C', '#009739'],
            'GN': ['#CE1126', '#FCD116', '#009460'],
            'GP': ['#000000', '#FFFFFF', '#E8112D', '#FFD100'],
            'GQ': ['#3E9A00', '#FFFFFF', '#E32118', '#0073CF'],
            'GR': ['#004C98', '#FFFFFF'],
            'GT': ['#4997D0', '#FFFFFF'],
            'GU': ['#003265', '#FFFFFF', '#BF0A30', '#E07C2F', '#FFD100', '#009B3A'],
            'GW': ['#CE1126', '#FCD116', '#009E49', '#000000'],
            'GY': ['#009E49', '#FFFFFF', '#FCD116', '#000000', '#CE1126'],
            'HK': ['#DE2910', '#FFFFFF'],
            'HN': ['#0073CF', '#FFFFFF'],
            'HR': ['#FF0000', '#FFFFFF', '#0000FF'],
            'HT': ['#00209F', '#D21034'],
            'HU': ['#CD2A3E', '#FFFFFF', '#436F4D'],
            'ID': ['#CE1126', '#FFFFFF'],
            'IE': ['#169B62', '#FFFFFF', '#FF883E'],
            'IL': ['#0038B8', '#FFFFFF'],
            'IM': ['#D41119', '#FFFFFF'],
            'IN': ['#FF9933', '#FFFFFF', '#138808'],
            'IQ': ['#CE1126', '#FFFFFF', '#000000'],
            'IR': ['#239F40', '#FFFFFF', '#DA0000'],
            'IS': ['#003897', '#FFFFFF', '#DC1E35'],
            'IT': ['#009246', '#FFFFFF', '#CE2B37'],
            'JE': ['#FFFFFF', '#D21034'],
            'JM': ['#009B3A', '#FED100', '#000000'],
            'JO': ['#000000', '#FFFFFF', '#007A3D', '#CE1126'],
            'JP': ['#BC002D', '#FFFFFF'],
            'KE': ['#000000', '#FFFFFF', '#BB0000', '#006600'],
            'KG': ['#F00000', '#FFD700'],
            'KH': ['#032EA1', '#FFFFFF', '#E00025'],
            'KI': ['#E8112D', '#FFD100', '#0032A0'],
            'KM': ['#FFC800', '#FFFFFF', '#3B7827', '#002B7F'],
            'KN': ['#009E49', '#000000', '#FFFFFF', '#CE1126', '#FCD116'],
            'KP': ['#024FA2', '#FFFFFF', '#ED1C27'],
            'KR': ['#FFFFFF', '#CD2E3A', '#0047A0'],
            'KW': ['#007A5E', '#FFFFFF', '#000000', '#CE1126'],
            'KY': ['#00205B', '#FFFFFF', '#CF142B'],
            'KZ': ['#00AFCA', '#FCE300'],
            'LA': ['#CE1126', '#002868', '#FFFFFF'],
            'LB': ['#ED1C24', '#FFFFFF', '#00A651'],
            'LC': ['#6CF', '#FFCE00', '#000000', '#FFFFFF'],
            'LI': ['#002B7F', '#CE1126', '#FFD700'],
            'LK': ['#FFD700', '#8D1B3D', '#FF7F00', '#00594C'],
            'LR': ['#002868', '#FFFFFF', '#BF0A30'],
            'LS': ['#00209F', '#FFFFFF', '#009A44', '#000000'],
            'LT': ['#FDB913', '#006A44', '#C1272D'],
            'LU': ['#00A1DE', '#FFFFFF', '#ED2939'],
            'LV': ['#9E3039', '#FFFFFF'],
            'LY': ['#E70013', '#000000', '#239E46', '#FFFFFF'],
            'MA': ['#C1272D', '#006233'],
            'MC': ['#CE1126', '#FFFFFF'],
            'MD': ['#0047AB', '#FFD100', '#CC092F'],
            'ME': ['#C40308', '#D4AF37'],
            'MG': ['#FFFFFF', '#FC3D32', '#007E3A'],
            'MH': ['#00388E', '#FFFFFF', '#E77C1E'],
            'MK': ['#D20000', '#FFE600'],
            'ML': ['#14B53A', '#FCD116', '#CE1126'],
            'MM': ['#FECB00', '#EA2839', '#34B233', '#FFFFFF'],
            'MN': ['#DA2032', '#0066B3', '#FFD700'],
            'MO': ['#009966', '#FFFFFF', '#FFD700'],
            'MP': ['#0033A0', '#FFFFFF'],
            'MQ': ['#002868', '#FFFFFF', '#EF3B2D'],
            'MR': ['#00A170', '#FFD700'],
            'MS': ['#00205B', '#FFFFFF', '#CF142B'],
            'MT': ['#FFFFFF', '#CF142B'],
            'MU': ['#EA2839', '#1A206D', '#FFD500', '#00A551'],
            'MV': ['#D21034', '#007E3A', '#FFFFFF'],
            'MW': ['#000000', '#D21034', '#007E3A'],
            'MX': ['#006847', '#FFFFFF', '#CE1126'],
            'MY': ['#0032A0', '#FFFFFF', '#F7D117', '#C8102E'],
            'MZ': ['#009A44', '#FFFFFF', '#000000', '#FCD116', '#CF142B'],
            'NA': ['#0033A0', '#FFFFFF', '#CF142B', '#009A44', '#FFC72C'],
            'NC': ['#0032A0', '#FFFFFF', '#D21034'],
            'NE': ['#E05206', '#FFFFFF', '#1DBE2E'],
            'NF': ['#006A4E', '#FFFFFF'],
            'NG': ['#008751', '#FFFFFF'],
            'NI': ['#0067C6', '#FFFFFF'],
            'NL': ['#21468B', '#FFFFFF', '#AE1C28'],
            'NO': ['#EF2B2D', '#FFFFFF', '#002868'],
            'NP': ['#DC143C', '#0033A0', '#FFFFFF'],
            'NR': ['#002B7F', '#FFFFFF', '#FFC72C'],
            'NZ': ['#00247D', '#FFFFFF', '#CF142B'],
            'OM': ['#FFFFFF', '#D21034', '#008000'],
            'PA': ['#005293', '#FFFFFF', '#D21034'],
            'PE': ['#D91023', '#FFFFFF'],
            'PF': ['#CE1126', '#FFFFFF'],
            'PG': ['#000000', '#D21034', '#FFE600', '#FFFFFF'],
            'PH': ['#0038A8', '#FFFFFF', '#CE1126', '#FCD116'],
            'PK': ['#00401A', '#FFFFFF'],
            'PL': ['#DC143C', '#FFFFFF'],
            'PM': ['#002395', '#FFFFFF', '#ED2939'],
            'PR': ['#ED0026', '#FFFFFF', '#0050F0'],
            'PS': ['#000000', '#FFFFFF', '#009639', '#DE2129'],
            'PT': ['#046A38', '#DA291C', '#FFE500'],
            'PW': ['#4AADD6', '#FFDE00'],
            'PY': ['#D52B1E', '#FFFFFF', '#0038A8'],
            'QA': ['#8D1B3D', '#FFFFFF'],
            'RE': ['#002868', '#FFFFFF', '#EF4135'],
            'RO': ['#002B7F', '#FCD116', '#CE1126'],
            'RS': ['#0C4076', '#FFFFFF', '#C6363C'],
            'RU': ['#FFFFFF', '#0039A6', '#D52B1E'],
            'RW': ['#00A1DE', '#FFD700', '#20603D'],
            'SA': ['#006C35', '#FFFFFF'],
            'SB': ['#0051BA', '#FFFFFF', '#215B33', '#FCD116'],
            'SC': ['#003D88', '#FCD856', '#D62828', '#FFFFFF', '#007A3D'],
            'SD': ['#D21034', '#FFFFFF', '#000000', '#007229'],
            'SE': ['#006AA7', '#FECC00'],
            'SG': ['#EF3340', '#FFFFFF'],
            'SH': ['#00205B', '#FFFFFF', '#CF142B'],
            'SI': ['#FFFFFF', '#0000FF', '#FF0000'],
            'SK': ['#FFFFFF', '#0B4EA2', '#EE1C25'],
            'SL': ['#1EB53A', '#FFFFFF', '#0072C6'],
            'SM': ['#FFFFFF', '#5EB6E4'],
            'SN': ['#00853F', '#FDEF42', '#E31B23'],
            'SO': ['#4189DD', '#FFFFFF'],
            'SR': ['#377E3F', '#FFFFFF', '#B40A2D', '#ECC81D'],
            'SS': ['#000000', '#FFFFFF', '#D21034', '#007229', '#0F47AF', '#FFC72C'],
            'ST': ['#12AD2B', '#FFD100', '#D21034', '#000000'],
            'SV': ['#0047AB', '#FFFFFF'],
            'SX': ['#ED2939', '#002B7F', '#FFFFFF'],
            'SY': ['#CE1126', '#FFFFFF', '#000000', '#007A3D'],
            'SZ': ['#3E5EB6', '#FFD700', '#B10D18', '#000000', '#FFFFFF'],
            'TC': ['#00205B', '#FFFFFF', '#CF142B'],
            'TD': ['#002664', '#FECB00', '#C60C30'],
            'TG': ['#006A4E', '#FFCE00', '#D21034', '#FFFFFF'],
            'TH': ['#A51931', '#FFFFFF', '#2D2A4A'],
            'TJ': ['#D22027', '#FFFFFF', '#006633', '#F89D29'],
            'TK': ['#00247D', '#FFFFFF', '#FFCC00'],
            'TL': ['#DA291C', '#FFC72C', '#000000', '#FFFFFF'],
            'TM': ['#009A44', '#FFFFFF', '#D21034'],
            'TN': ['#E70013', '#FFFFFF'],
            'TO': ['#C10000', '#FFFFFF'],
            'TR': ['#E30A17', '#FFFFFF'],
            'TT': ['#E00000', '#FFFFFF', '#000000'],
            'TV': ['#00388E', '#FFFFFF', '#CF142B', '#FFD100'],
            'TW': ['#000095', '#FFFFFF', '#FE0000'],
            'TZ': ['#00A3DD', '#000000', '#1EB53A', '#FCD116'],
            'UA': ['#0057B7', '#FFDD00'],
            'UG': ['#000000', '#FCDC04', '#D90000'],
            'US': ['#B22234', '#FFFFFF', '#3C3B6E'],
            'UY': ['#0038A8', '#FFFFFF', '#FCD116'],
            'UZ': ['#0072CE', '#FFFFFF', '#DA291C', '#009A44'],
            'VC': ['#0072C6', '#FCD116', '#009E60'],
            'VE': ['#FFCC00', '#0033A0', '#CF142B', '#FFFFFF'],
            'VG': ['#00205B', '#FFFFFF', '#CF142B'],
            'VI': ['#002B7F', '#FFFFFF', '#FECB00'],
            'VN': ['#DA251D', '#FFFF00'],
            'VU': ['#009543', '#FDCE12', '#D21034', '#000000'],
            'WF': ['#CE1126', '#FFFFFF'],
            'WS': ['#C8102E', '#FFFFFF', '#002B7F'],
            'YE': ['#CE1126', '#FFFFFF', '#000000'],
            'ZA': ['#007749', '#FFB612', '#DE3831', '#000000', '#FFFFFF'],
            'ZM': ['#198D44', '#DE2028', '#FF921E', '#000000'],
            'ZW': ['#008000', '#FFFF00', '#FF0000', '#000000', '#FFFFFF'],
        };

        const root = document.documentElement;
        const colorScheme = countryColors[countryCode];
        const downloadBtn = document.getElementById('downloadFiltered');

        // Countries with light flags that need inverted button text
        const lightFlagCountries = [
            'AR', 'AT', 'CA', 'CH', 'CY', 'DK', 'EE', 'FI', 'GE', 'GR', 'HK', 'ID', 'IL',
            'JP', 'KR', 'LT', 'LV', 'NG', 'PL', 'PT', 'SA', 'SG', 'TR', 'UA', 'UY'
        ];

        if (colorScheme) {
            document.body.classList.add('country-selected');
            root.style.setProperty('--brand-primary', colorScheme[0]);
            root.style.setProperty('--brand-secondary', colorScheme[1] || colorScheme[0]);
            root.style.setProperty('--brand-tertiary', colorScheme[2] || colorScheme[1] || colorScheme[0]);

            if (lightFlagCountries.includes(countryCode.toUpperCase())) {
                downloadBtn.classList.add('btn-primary-inverted');
            } else {
                downloadBtn.classList.remove('btn-primary-inverted');
            }

        } else {
            document.body.classList.remove('country-selected');
            // Reset to default theme colors
            root.style.removeProperty('--brand-primary');
            root.style.removeProperty('--brand-secondary');
            root.style.removeProperty('--brand-tertiary');
            downloadBtn.classList.remove('btn-primary-inverted');
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
            option.textContent = getCountryName(country);
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