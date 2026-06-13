// SPDX-License-Identifier: AGPL-3.0-or-later

/**
 * I18n Manager for ConfigStream
 * 
 * Performance: Dictionaries are loaded on-demand from assets/i18n/[lang].json
 * to keep the main bundle light.
 */

class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('lang') || 'en';
        this.translations = {};
        this.loadedLangs = new Set();
        this.initialized = false;
        this.initPromise = null;
    }

    async init() {
        if (this.initPromise) return this.initPromise;
        
        this.initPromise = (async () => {
            // Load English as fallback and the current selected language
            const loads = [this.loadLanguage('en')];
            if (this.currentLang !== 'en') {
                loads.push(this.loadLanguage(this.currentLang));
            }
            await Promise.all(loads);
            this.initialized = true;
            this.updatePage();
            
            // Re-apply language settings (RTL, attributes)
            this.applyLanguageSettings(this.currentLang);

            // Notify listeners that translations are ready so any text rendered
            // before init completed (e.g. the hero subtitle) can re-render.
            window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: this.currentLang } }));
        })();
        
        return this.initPromise;
    }

    async loadLanguage(lang) {
        if (this.loadedLangs.has(lang)) return;
        try {
            const response = await fetch(`assets/i18n/${lang}.json`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            this.translations[lang] = data;
            this.loadedLangs.add(lang);
        } catch (e) {
            console.error(`[I18n] Could not load language ${lang}:`, e);
        }
    }

    async setLanguage(lang) {
        await this.loadLanguage(lang);
        if (!this.translations[lang] && lang !== 'en') {
            console.warn(`[I18n] Language ${lang} not supported or load failed`);
            return;
        }
        
        this.currentLang = lang;
        localStorage.setItem('lang', lang);
        
        this.applyLanguageSettings(lang);
        this.updatePage();
        
        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
    }

    applyLanguageSettings(lang) {
        document.documentElement.setAttribute('lang', lang);

        // Set direction for RTL languages
        if (lang === 'fa' || lang === 'ar') {
            document.documentElement.setAttribute('dir', 'rtl');
        } else {
            document.documentElement.setAttribute('dir', 'ltr');
        }

        // Update current language label in the language button
        const langNames = {
            'en': 'EN',
            'zh': '中文',
            'ru': 'RU',
            'fa': 'فا',
            'ar': 'ع'
        };
        const currentLangLabel = document.getElementById('current-lang-label');
        if (currentLangLabel) {
            currentLangLabel.textContent = langNames[lang] || lang.toUpperCase();
        }

        // Update active state in language menu
        const langButtons = document.querySelectorAll('.lang-menu button, .lang-select-btn');
        langButtons.forEach(btn => {
            const btnLang = btn.getAttribute('data-lang');
            if (btnLang === lang) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    t(key) {
        return (this.translations[this.currentLang] && this.translations[this.currentLang][key]) || 
               (this.translations['en'] && this.translations['en'][key]) || 
               key;
    }

    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);

            if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
                 el.setAttribute('placeholder', translation);
            } else if (el.dataset.i18nHtml === 'true') {
                 el.replaceChildren(this.sanitizeToFragment(translation));
            } else {
                 el.textContent = translation;
            }
        });
    }

    sanitizeToFragment(input) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(String(input || ''), 'text/html');
        const allowedTags = new Set(['STRONG', 'EM', 'B', 'I', 'U', 'BR', 'P', 'SPAN', 'DIV', 'A', 'UL', 'LI']);
        const allowedAttrs = new Set(['href', 'title', 'alt', 'class', 'id', 'target', 'role', 'aria-label', 'aria-hidden']);
        const toRemove = [];

        doc.body.querySelectorAll('*').forEach(node => {
            if (!allowedTags.has(node.tagName)) {
                toRemove.push(node);
                return;
            }
            [...node.attributes].forEach(attr => {
                const name = attr.name.toLowerCase();
                const value = attr.value || '';
                if (!allowedAttrs.has(name) && !name.startsWith('data-')) {
                    node.removeAttribute(attr.name);
                    return;
                }
                if (name.startsWith('on')) {
                    node.removeAttribute(attr.name);
                    return;
                }
                if (name === 'href' || name === 'src') {
                    const normalized = value.replace(/[\u0000-\u0020]/g, '').toLowerCase();
                    if (/^(javascript|data|vbscript):/.test(normalized)) {
                        node.removeAttribute(attr.name);
                    }
                }
            });
        });
        toRemove.forEach(node => node.remove());

        const fragment = document.createDocumentFragment();
        Array.from(doc.body.childNodes).forEach(node => {
            fragment.appendChild(document.importNode(node, true));
        });
        return fragment;
    }

    sanitize(input) {
        return this.sanitizeToFragment(input).textContent || '';
    }

    formatNumber(num) {
        if (!num && num !== 0) return '';
        const number = typeof num === 'string' ? parseFloat(num.replace(/,/g, '')) : num;
        
        try {
            const locales = {
                'fa': 'fa-IR',
                'ar': 'ar-EG',
                'ru': 'ru-RU',
                'zh': 'zh-CN',
                'en': 'en-US'
            };
            return number.toLocaleString(locales[this.currentLang] || 'en-US');
        } catch (e) {
            return number.toString();
        }
    }
}

window.i18n = new I18n();
document.addEventListener('DOMContentLoaded', () => {
    window.i18n.init();

    // Add event listeners for language selection buttons
    const langButtons = document.querySelectorAll('.lang-select-btn');
    langButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const lang = e.currentTarget.getAttribute('data-lang');
            if (lang) {
                window.i18n.setLanguage(lang);
            }
        });
    });
});
