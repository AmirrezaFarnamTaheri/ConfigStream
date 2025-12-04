const translations = {
    en: {
        "nav.home": "Home",
        "nav.proxies": "Live Proxies",
        "nav.analytics": "Analytics",
        "nav.wiki": "Wiki",
        "nav.about": "About",

        "wiki.nav.home": "Wiki Home",
        "wiki.nav.intro": "Introduction",
        "wiki.nav.arch": "Architecture",
        "wiki.nav.proto": "Protocols",
        "wiki.nav.eng": "Engineering",
        "wiki.nav.devops": "DevOps",
        "wiki.nav.frontend": "Frontend",
        "wiki.nav.security": "Security",
        "wiki.nav.api": "API Reference",
        "wiki.nav.contributing": "Contributing",
        "wiki.nav.troubleshooting": "Troubleshooting",
        "wiki.nav.page_home": "Page: Home",
        "wiki.nav.page_analytics": "Page: Analytics",
        "wiki.nav.page_proxies": "Page: Proxies",
        "wiki.nav.page_about": "Page: About",

        "hero.title": "Unlock the Internet",
        "hero.subtitle": "Access the open web with our free, auto-updating VPN configurations. We aggregate fresh proxies from over 668 sources every 6 hours, ensuring you always have a reliable connection.",
        "hero.browse": "Browse Proxies",
        "hero.get": "Get Configs",

        "pipeline.title": "Live Pipeline Status",

        "stats.sourced": "Total Sourced",
        "stats.unique": "Unique & Verified",
        "stats.online": "Online Now",
        "stats.hybrid": "Hybrid Engine",
        "stats.hybrid.desc": "Go + Python Core",
        "stats.update": "Update Frequency",
        "stats.threats": "Threats Blocked",

        "downloads.title": "Get Your Configs",
        "downloads.subtitle": "Select your preferred format below. All files contain our latest verified proxies.",
        "downloads.universal": "Universal Subscription",
        "downloads.universal.desc": "Base64 link compatible with V2Ray, Xray, and most clients. Supports auto-update.",
        "downloads.singbox": "Sing-box Config",
        "downloads.singbox.desc": "Optimized JSON for Sing-box and NekoBox clients.",
        "downloads.clash": "Clash Config",
        "downloads.clash.desc": "Ready-to-use YAML configuration for Clash.",
        "downloads.shadowrocket": "Shadowrocket",
        "downloads.shadowrocket.desc": "Optimized format for Shadowrocket on iOS.",
        "downloads.chosen.title": "🏆 Chosen Top 1000",
        "downloads.chosen.desc": "Our premium selection: Top 50 proxies per protocol, ranked by lowest latency. The best choice for most users!",
        "downloads.chosen.btn": "Copy Chosen Subscription",

        "info.start.title": "Quick Start Guide",
        "info.start.text": "1. **Select** your preferred format from the downloads section above.<br>2. **Copy** the subscription link or download the config file.<br>3. **Import** it into your VPN client (V2RayNG, Shadowrocket, Clash, etc.) and update the subscription.",

        "info.how.title": "The Engine",
        "info.how.text": "Our automated pipeline runs every 6 hours on GitHub Actions. It aggregates thousands of public proxies, filters out dead or unsafe nodes, and verifies them against real targets.",
        "info.how.highlight.title": "🚀 Smart Routing",
        "info.how.highlight.text": "We use advanced \"Proxy Washing\" to route traffic through Cloudflare WARP when necessary, bypassing IP blocks and enhancing privacy.",

        "info.security.title": "Security & Privacy",
        "info.community.title": "Open Source",

        "footer.love": "Empowering global access to information. Open Source & Forever Free. ✨",

        "formats.title": "Format Cheatsheet",
        "formats.base64": "<strong>Universal Subscription:</strong> The industry standard. Works with almost all clients (V2Ray, Xray, v2rayN). Auto-updates.",
        "formats.singbox": "<strong>Sing-box:</strong> Next-gen JSON config. Choose 'Sniper' for latency-based auto-routing or 'Tank' for maximum stability.",
        "formats.clash": "<strong>Clash YAML:</strong> A complete profile for Clash clients (Verge, Stash). Includes rule-based routing.",

        "notice.title": "Security Notice",
        "notice.text": "These are free public proxies. While we test them for safety, we cannot guarantee privacy.",
        "notice.list.1": "DO NOT use for banking or sensitive data.",
        "notice.list.2": "GREAT for unblocking content and browsing.",
        "notice.list.3": "Traffic flows through third-party servers.",
        "notice.disclaimer": "Use responsibly at your own risk.",

        "adapters.title": "🔌 New Formats",
        "adapters.subtitle": "Experimental support for additional clients.",

        "byow.title": "🚀 Turbo Mode (BYOW)",
        "byow.url.placeholder": "Paste your Cloudflare Worker URL...",
        "byow.uuid.placeholder": "Optional: UUID",
        "byow.apply": "Apply Custom Worker",
        "byow.hint": "Use your own Worker for private, high-speed connectivity.",
        "byow.download": "Download Turbo Config",

        "filters.search": "Search e.g., 'fastest US vmess' or 'Germany < 100ms'",
        "filters.protocol": "All Protocols",
        "filters.country": "All Countries",
        "filters.city": "All Cities",
        "filters.copy_all": "Copy All",
        "filters.copy_filtered": "Copy Filtered",
        "filters.download_filtered": "Download Filtered",
        "filters.empty_title": "No Matches Found",
        "filters.empty_text": "We couldn't find any proxies matching your criteria. Try adjusting your filters.",

        "table.protocol": "Protocol",
        "table.location": "Location",
        "table.latency": "Latency",
        "table.status": "Status",
        "table.copy": "Copy Link",

        "verify.local": "Turbo-Verify (Local)",
        "verify.status": "Ready to verify via WASM",

        /* About Page */
        "about.hero.title": "About ConfigStream",
        "about.subtitle": "The sovereign, resilient, and automated gateway to the open internet.",
        "about.mission.title": "Our Mission",
        "about.mission.text": "We believe access to information is a fundamental right. ConfigStream automates the discovery, testing, and optimization of censorship-resistant proxies, providing a reliable lifeline for users in restricted network environments—completely free of charge.",
        "about.arch.title": "Architecture: The \"Resilient Core\"",
        "about.arch.text": "Built on a \"Zero Budget\" philosophy, ConfigStream leverages the immense power of distributed CI/CD infrastructure (GitHub Actions) to create a self-sustaining, unstoppable pipeline. We don't rely on expensive servers that can be blocked or taken down.",
        "about.arch.hybrid": "<strong>Hybrid Engine:</strong> A fusion of Python's analytical intelligence and a high-performance <strong>Go Sidecar</strong> for massively concurrent, raw-socket network verification.",
        "about.arch.intel": "<strong>Intelligence Layer:</strong> Features \"Proxy Washing\" technology that automatically rehabilitates blocked IPs by tunneling traffic through Cloudflare WARP, creating robust \"Smart Chains\".",
        "about.arch.agg": "<strong>Global Aggregator:</strong> Scrapes, parses, and normalizes data from over 600 public sources every 6 hours.",
        "about.arch.pub": "<strong>Universal Publisher:</strong> Delivers optimized configurations for every major client: V2Ray, Clash, Sing-box ('Sniper' routing & 'Tank' tunneling), and more.",
        "about.security.title": "Security & Transparency",
        "about.security.text": "We employ automated security scanning to filter out honeypots, malware, and broken nodes. However, transparency is key: these are public proxies. While we optimize for safety, we strongly recommend using them for browsing and content access, not for sensitive banking or private communications.",
        "about.btn.source": "View Source on GitHub",

        /* Analytics Page */
        "analytics.hero.title": "Network Intelligence",
        "analytics.hero.subtitle": "Real-time insights into global proxy distribution and performance.",
        "analytics.charts.protocol": "Protocol Distribution",
        "analytics.charts.latency": "Latency Distribution",
        "analytics.charts.countries": "Top Countries",
        "analytics.charts.rejection": "Rejection Logic",
        "analytics.charts.threats": "Threat Breakdown",
        "analytics.charts.asns": "Top Internet Providers",

        /* Proxies Page */
        "proxies.hero.title": "Live Proxy List",
        "proxies.hero.subtitle": "Explore our complete list of vetted proxies. Search, sort, and find the perfect connection for your needs."
    },
    zh: {
        "nav.home": "首页",
        "nav.proxies": "实时节点",
        "nav.analytics": "数据分析",
        "nav.wiki": "百科",
        "nav.about": "关于我们",
        "wiki.nav.home": "百科首页",
        "wiki.nav.intro": "简介",
        "wiki.nav.arch": "架构设计",
        "wiki.nav.proto": "支持协议",
        "wiki.nav.eng": "工程细节",
        "wiki.nav.devops": "运维部署",
        "wiki.nav.frontend": "前端开发",
        "wiki.nav.security": "安全机制",
        "wiki.nav.api": "API 参考",
        "wiki.nav.contributing": "贡献指南",
        "wiki.nav.troubleshooting": "故障排除",
        "wiki.nav.page_home": "页面：首页",
        "wiki.nav.page_analytics": "页面：分析",
        "wiki.nav.page_proxies": "页面：节点",
        "wiki.nav.page_about": "页面：关于",
        "hero.title": "畅游无界网络",
        "hero.subtitle": "使用我们免费、自动更新的 VPN 配置访问全球网络。系统每 6 小时从 668+ 个精选源获取新鲜代理，确保您时刻拥有稳定可靠的连接。",
        "hero.browse": "浏览节点",
        "hero.get": "获取订阅",
        "pipeline.title": "实时系统状态",
        "stats.sourced": "采集源总数",
        "stats.unique": "去重后可用",
        "stats.online": "当前在线",
        "stats.hybrid": "混合引擎",
        "stats.hybrid.desc": "Go + Python 内核",
        "stats.update": "更新频率",
        "stats.threats": "已拦截威胁",
        "downloads.title": "获取配置",
        "downloads.subtitle": "选择您需要的格式。所有订阅均包含最新并通过测试的节点。",
        "downloads.universal": "通用订阅",
        "downloads.universal.desc": "Base64 格式，兼容 V2Ray、Xray 及大多数客户端。支持自动更新。",
        "downloads.singbox": "Sing-box 配置",
        "downloads.singbox.desc": "专为 Sing-box 和 NekoBox 优化的 JSON 配置文件。",
        "downloads.clash": "Clash 配置",
        "downloads.clash.desc": "开箱即用的 YAML 文件，完美适配 Clash 系列客户端。",
        "downloads.shadowrocket": "Shadowrocket",
        "downloads.shadowrocket.desc": "iOS 端 Shadowrocket 专用优化格式。",
        "downloads.chosen.title": "🏆 精选 Top 1000",
        "downloads.chosen.desc": "优选合集：按低延迟排序，每种协议精选前 50 个节点。绝大多数用户的最佳选择！",
        "downloads.chosen.btn": "复制精选订阅",
        "info.start.title": "快速上手",
        "info.start.text": "使用 ConfigStream 非常简单。复制上方的订阅链接，并在您的 VPN 客户端中导入即可。",
        "info.how.title": "工作原理",
        "info.security.title": "安全承诺",
        "info.community.title": "社区驱动",
        "footer.love": "为自由互联网而生的开源项目。✨",
        "formats.title": "格式说明",
        "formats.base64": "Base64：通用订阅链接，适用于 V2Ray, Xray, NekoBox 等。",
        "formats.singbox": "Sing-box：包含 '狙击手' (智能分流) 和 '坦克' (全局代理) 模式。",
        "formats.clash": "Clash：适用于 Clash 客户端的 YAML 配置。",
        "notice.title": "重要安全提示",
        "notice.text": "本项目提供免费公共代理。虽经安全测试，但无法保证绝对隐私。",
        "notice.list.1": "请勿用于网银或传输敏感信息。",
        "notice.list.2": "非常适合浏览网页和解锁流媒体。",
        "notice.list.3": "流量将经过第三方服务器，请知悉。",
        "notice.disclaimer": "请理性使用，风险自负。",
        "adapters.title": "🔌 更多格式",
        "adapters.subtitle": "更多客户端的实验性支持。",
        "byow.title": "🚀 极速模式 (BYOW)",
        "byow.url.placeholder": "在此输入 Cloudflare Worker 地址...",
        "byow.uuid.placeholder": "可选: UUID",
        "byow.apply": "应用设置",
        "byow.hint": "部署私人 Worker，享受私密、高速且抗封锁的连接。",
        "byow.download": "下载极速配置",
        "filters.search": "搜索示例：fastest US vmess 或 Germany < 100ms",
        "filters.protocol": "所有协议",
        "filters.country": "所有国家",
        "filters.city": "所有城市",
        "filters.copy_all": "复制全部",
        "filters.copy_filtered": "复制筛选结果",
        "filters.download_filtered": "下载筛选结果",
        "filters.empty_title": "未找到结果",
        "filters.empty_text": "没有找到符合条件的节点，请尝试调整筛选条件。",
        "table.protocol": "协议",
        "table.location": "位置",
        "table.latency": "延迟",
        "table.status": "状态",
        "table.copy": "复制链接",
        "verify.local": "本地极速验证",
        "verify.status": "WASM 组件就绪",

        /* About Page */
        "about.hero.title": "关于 ConfigStream",
        "about.subtitle": "自动化、高可用、免费访问开放互联网。",
        "about.mission.title": "使命",
        "about.mission.text": "ConfigStream 旨在为受网络限制的用户提供可靠、免费的全球互联网接入。通过每 6 小时从数百个公共源聚合代理并进行严格测试，我们确保无需人工干预的高可用性。",
        "about.arch.title": "架构：“弹性核心”",
        "about.arch.text": "我们采用“零预算”架构，完全运行在 GitHub 的基础设施上，确保可持续性和抗审查性。",
        "about.arch.hybrid": "<strong>混合引擎：</strong> 结合 Python 的灵活性（用于情报分析）与高性能 <strong>Go Sidecar</strong>（用于大规模并发网络测试）。",
        "about.arch.intel": "<strong>情报层：</strong> 我们的“代理清洗”技术通过 Cloudflare WARP 隧道自动修复被屏蔽的 IP。",
        "about.arch.agg": "<strong>聚合器：</strong> 每 6 小时从 600+ 个来源获取数据。",
        "about.arch.pub": "<strong>发布器：</strong> 为 V2Ray、Clash、Sing-box（坦克/狙击手模式）等生成优化配置。",
        "about.security.title": "安全性",
        "about.security.text": "虽然我们执行自动安全检查（拦截广告、恶意软件网站、蜜罐和 TLS 验证），但这些是公共代理。我们建议仅用于浏览，避免进行敏感交易（如银行、密码）。",
        "about.btn.source": "在 GitHub 上查看源码",

        /* Analytics Page */
        "analytics.hero.title": "网络情报",
        "analytics.hero.subtitle": "全球代理分布和性能的实时洞察。",
        "analytics.charts.protocol": "协议分布",
        "analytics.charts.latency": "延迟分布",
        "analytics.charts.countries": "热门国家",

        /* Proxies Page */
        "proxies.hero.title": "实时节点列表",
        "proxies.hero.subtitle": "探索我们完整的经过验证的代理列表。搜索、排序并找到最适合您的连接。"
    },
    fa: {
        "nav.home": "خانه",
        "nav.proxies": "پروکسی‌های زنده",
        "nav.analytics": "آمار",
        "nav.wiki": "دانشنامه",
        "nav.about": "درباره ما",
        "hero.title": "دروازه‌ای به اینترنت آزاد",
        "hero.subtitle": "با کانفیگ‌های رایگان و خودکار ما، بدون محدودیت به اینترنت دسترسی داشته باشید. سیستم ما هر ۶ ساعت پروکسی‌های تازه را از ۶۶۸+ منبع دریافت می‌کند تا اتصالی پایدار را تضمین کند.",
        "hero.browse": "مشاهده پروکسی‌ها",
        "hero.get": "دریافت کانفیگ",
        "pipeline.title": "وضعیت لحظه‌ای سیستم",
        "stats.sourced": "کل منابع",
        "stats.unique": "تست شده و سالم",
        "stats.online": "آنلاین",
        "stats.hybrid": "موتور ترکیبی",
        "stats.hybrid.desc": "هسته Go + Python",
        "stats.update": "بروزرسانی",
        "stats.threats": "تهدیدات خنثی شده",
        "downloads.title": "دریافت اشتراک",
        "downloads.subtitle": "فرمت دلخواه خود را انتخاب کنید. تمام فایل‌ها حاوی پروکسی‌های تست شده هستند.",
        "downloads.universal": "اشتراک جامع (Universal)",
        "downloads.universal.desc": "لینک Base64 سازگار با V2Ray، Xray و اکثر کلاینت‌ها. با قابلیت آپدیت خودکار.",
        "downloads.singbox": "کانفیگ Sing-box",
        "downloads.singbox.desc": "فایل JSON بهینه شده برای Sing-box و NekoBox.",
        "downloads.clash": "کانفیگ Clash",
        "downloads.clash.desc": "فایل YAML آماده برای کاربران Clash.",
        "downloads.shadowrocket": "Shadowrocket",
        "downloads.shadowrocket.desc": "فرمت اختصاصی برای کاربران iOS.",
        "downloads.chosen.title": "🏆 گلچین ۱۰۰۰ تایی",
        "downloads.chosen.desc": "انتخاب ویژه ما: ۵۰ پروکسی برتر از هر پروتکل با کمترین پینگ. بهترین گزینه برای اکثر کاربران!",
        "downloads.chosen.btn": "کپی اشتراک ویژه",
        "info.start.title": "راهنمای شروع",
        "info.start.text": "استفاده از ConfigStream ساده است. لینک اشتراک را کپی کرده و در فیلترشکن خود وارد کنید.",
        "info.how.title": "نحوه کارکرد",
        "info.security.title": "تعهد امنیتی",
        "info.community.title": "قدرت جامعه",
        "footer.love": "پروژه‌ای دلی برای آزادی اینترنت. ✨",
        "formats.title": "راهنمای فرمت‌ها",
        "formats.base64": "Base64: یک لینک ساده برای V2Ray, Xray و غیره.",
        "formats.singbox": "Sing-box: شامل حالت‌های 'اسنایپر' (هوشمند) و 'تانک' (تمام تانل).",
        "formats.clash": "Clash: فایل کانفیگ برای کلاینت‌های Clash.",
        "notice.title": "هشدار امنیتی",
        "notice.text": "این پروکسی‌ها عمومی و رایگان هستند. ما امنیت آن‌ها را بررسی می‌کنیم اما حریم خصوصی را تضمین نمی‌کنیم.",
        "notice.list.1": "برای کارهای بانکی و حساس استفاده نکنید.",
        "notice.list.2": "عالی برای وب‌گردی و عبور از فیلترینگ.",
        "notice.list.3": "ترافیک شما از سرورهای واسط عبور می‌کند.",
        "notice.disclaimer": "استفاده با مسئولیت خودتان.",
        "adapters.title": "🔌 سایر فرمت‌ها",
        "adapters.subtitle": "پشتیبانی آزمایشی برای کلاینت‌های دیگر.",
        "byow.title": "🚀 حالت توربو (BYOW)",
        "byow.url.placeholder": "آدرس Cloudflare Worker خود را وارد کنید...",
        "byow.uuid.placeholder": "اختیاری: UUID",
        "byow.apply": "اعمال تغییرات",
        "byow.hint": "با ورکر شخصی خود، سرعتی بالا و بدون قطعی را تجربه کنید.",
        "byow.download": "دانلود کانفیگ توربو",
        "filters.search": "جستجو: مثلا fastest US vmess یا Germany < 100ms",
        "filters.protocol": "همه پروتکل‌ها",
        "filters.country": "همه کشورها",
        "filters.city": "همه شهرها",
        "filters.copy_all": "کپی همه",
        "filters.copy_filtered": "کپی فیلتر شده",
        "filters.download_filtered": "دانلود فیلتر شده",
        "filters.empty_title": "نتیجه‌ای یافت نشد",
        "filters.empty_text": "پروکسی با مشخصات مورد نظر شما پیدا نشد. فیلترها را تغییر دهید.",
        "table.protocol": "پروتکل",
        "table.location": "موقعیت",
        "table.latency": "پینگ",
        "table.status": "وضعیت",
        "table.copy": "کپی",
        "verify.local": "تست سرعت (محلی)",
        "verify.status": "آماده تست با WASM",

        /* About Page */
        "about.hero.title": "درباره ConfigStream",
        "about.subtitle": "دسترسی خودکار، پایدار و رایگان به اینترنت آزاد.",
        "about.mission.title": "ماموریت",
        "about.mission.text": "ConfigStream برای فراهم کردن دسترسی قابل اعتماد و رایگان به اینترنت جهانی برای کاربران در محیط‌های محدود شبکه ساخته شده است. با جمع‌آوری پروکسی‌ها از صدها منبع عمومی و تست دقیق آنها، ما دسترسی بالا را بدون نیاز به تلاش دستی تضمین می‌کنیم.",
        "about.arch.title": "معماری: \"هسته مقاوم\"",
        "about.arch.text": "ما از معماری \"بودجه صفر\" استفاده می‌کنیم که کاملاً بر روی زیرساخت گیت‌هاب اجرا می‌شود و پایداری و مقاومت در برابر سانسور را تضمین می‌کند.",
        "about.arch.hybrid": "<strong>موتور ترکیبی:</strong> ترکیب انعطاف‌پذیری پایتون برای هوش مصنوعی با <strong>Go Sidecar</strong> قدرتمند برای تست همزمان شبکه.",
        "about.arch.intel": "<strong>لایه هوشمند:</strong> فناوری «پاکسازی پروکسی» ما به‌طور خودکار IPهای مسدود شده را از طریق تونل Cloudflare WARP بازیابی می‌کند.",
        "about.arch.agg": "<strong>جمع‌آوری‌کننده:</strong> هر ۶ ساعت از بیش از ۶۰۰ منبع اطلاعات دریافت می‌کند.",
        "about.arch.pub": "<strong>ناشر:</strong> کانفیگ‌های بهینه شده برای V2Ray، Clash، Sing-box (حالت‌های تانک/اسنایپر) و غیره تولید می‌کند.",
        "about.security.title": "امنیت",
        "about.security.text": "در حالی که ما بررسی‌های امنیتی خودکار انجام می‌دهیم (مسدود کردن تبلیغات، سایت‌های بدافزار، هانی‌پات‌ها و تایید TLS)، این‌ها پروکسی‌های عمومی هستند. توصیه می‌کنیم از آن‌ها برای وب‌گردی استفاده کنید و از انجام تراکنش‌های حساس (بانکی، رمز عبور) خودداری کنید.",
        "about.btn.source": "مشاهده سورس در گیت‌هاب",

        /* Analytics Page */
        "analytics.hero.title": "هوش شبکه",
        "analytics.hero.subtitle": "بینش لحظه‌ای از توزیع و عملکرد پروکسی‌های جهانی.",
        "analytics.charts.protocol": "توزیع پروتکل",
        "analytics.charts.latency": "توزیع تاخیر (Latency)",
        "analytics.charts.countries": "کشورهای برتر",

        /* Proxies Page */
        "proxies.hero.title": "لیست زنده پروکسی‌ها",
        "proxies.hero.subtitle": "لیست کامل پروکسی‌های تایید شده ما را کاوش کنید. جستجو کنید، مرتب کنید و اتصال مناسب نیاز خود را پیدا کنید."
    },
    ru: {
        "nav.home": "Главная",
        "nav.proxies": "Живые прокси",
        "nav.analytics": "Аналитика",
        "nav.wiki": "Вики",
        "nav.about": "О проекте",
        "hero.title": "Интернет без границ",
        "hero.subtitle": "Получите свободный доступ к сети с нашими бесплатными, автообновляемыми VPN-конфигурациями. Мы собираем свежие прокси из 668+ источников каждые 6 часов.",
        "hero.browse": "Найти прокси",
        "hero.get": "Скачать конфиги",
        "pipeline.title": "Статус системы",
        "stats.sourced": "Всего источников",
        "stats.unique": "Рабочих прокси",
        "stats.online": "Онлайн сейчас",
        "stats.hybrid": "Гибридный движок",
        "stats.hybrid.desc": "Ядро Go + Python",
        "stats.update": "Частота обновлений",
        "stats.threats": "Угроз нейтрализовано",
        "downloads.title": "Ваши конфигурации",
        "downloads.subtitle": "Выберите удобный формат. Все файлы содержат проверенные и надежные прокси.",
        "downloads.universal": "Универсальная подписка",
        "downloads.universal.desc": "Ссылка Base64 для V2Ray, Xray и других клиентов. Поддерживает автообновление.",
        "downloads.singbox": "Конфиг Sing-box",
        "downloads.singbox.desc": "Оптимизированный JSON для клиентов Sing-box и NekoBox.",
        "downloads.clash": "Конфиг Clash",
        "downloads.clash.desc": "Готовый YAML файл для пользователей Clash.",
        "downloads.shadowrocket": "Shadowrocket",
        "downloads.shadowrocket.desc": "Специальный формат для iOS (Shadowrocket).",
        "downloads.chosen.title": "🏆 Топ 1000 Лучших",
        "downloads.chosen.desc": "Наш выбор: 50 лучших прокси каждого протокола с минимальной задержкой. Идеально для большинства задач!",
        "downloads.chosen.btn": "Копировать Топ-подписку",
        "info.start.title": "Как начать",
        "info.start.text": "Всё просто: скопируйте ссылку на подписку и импортируйте её в ваш VPN-клиент.",
        "info.how.title": "Как это работает",
        "info.security.title": "Безопасность",
        "info.community.title": "Сообщество",
        "footer.love": "Сделано с любовью к свободному интернету. ✨",
        "formats.title": "О форматах",
        "formats.base64": "Base64: Единая ссылка для V2Ray, Xray, NekoBox.",
        "formats.singbox": "Sing-box: Режимы 'Снайпер' (Умный роутинг) и 'Танк' (Весь трафик).",
        "formats.clash": "Clash: Конфигурация YAML для Clash.",
        "notice.title": "Важно о безопасности",
        "notice.text": "Это бесплатные публичные прокси. Мы фильтруем опасные, но не гарантируем анонимность.",
        "notice.list.1": "НЕ используйте для банковских приложений.",
        "notice.list.2": "ОТЛИЧНО подходит для обхода блокировок.",
        "notice.list.3": "Трафик проходит через сторонние серверы.",
        "notice.disclaimer": "Используйте на свой страх и риск.",
        "adapters.title": "🔌 Другие форматы",
        "adapters.subtitle": "Экспериментальная поддержка клиентов.",
        "byow.title": "🚀 Турбо-режим (BYOW)",
        "byow.url.placeholder": "Вставьте ссылку на ваш Cloudflare Worker...",
        "byow.uuid.placeholder": "Опционально: UUID",
        "byow.apply": "Применить",
        "byow.hint": "Используйте свой Worker для максимальной скорости и приватности.",
        "byow.download": "Скачать Турбо-конфиг",
        "filters.search": "Поиск: например, fastest US vmess или Germany < 100ms",
        "filters.protocol": "Все протоколы",
        "filters.country": "Все страны",
        "filters.city": "Все города",
        "filters.copy_all": "Копировать все",
        "filters.copy_filtered": "Копировать фильтр",
        "filters.download_filtered": "Скачать фильтр",
        "filters.empty_title": "Ничего не найдено",
        "filters.empty_text": "По вашему запросу нет прокси. Попробуйте изменить фильтры.",
        "table.protocol": "Протокол",
        "table.location": "Локация",
        "table.latency": "Пинг",
        "table.status": "Статус",
        "table.copy": "Копировать",
        "verify.local": "Быстрая проверка (Local)",
        "verify.status": "WASM готов к работе",

        /* About Page */
        "about.hero.title": "О ConfigStream",
        "about.subtitle": "Автоматизированный, надежный и бесплатный доступ к открытому интернету.",
        "about.mission.title": "Миссия",
        "about.mission.text": "ConfigStream был создан для обеспечения надежного и бесплатного доступа к глобальному интернету для пользователей в сетях с ограничениями. Агрегируя прокси из сотен публичных источников и тщательно их тестируя, мы обеспечиваем высокую доступность без ручного вмешательства.",
        "about.arch.title": "Архитектура: \"Устойчивое ядро\"",
        "about.arch.text": "Мы используем архитектуру \"Нулевой бюджет\", которая полностью работает на инфраструктуре GitHub, обеспечивая устойчивость и сопротивление цензуре.",
        "about.arch.hybrid": "<strong>Гибридный движок:</strong> Сочетает гибкость Python для анализа с высокопроизводительным <strong>Go Sidecar</strong> для массового параллельного тестирования сети.",
        "about.arch.intel": "<strong>Интеллектуальный слой:</strong> Наша технология «очистки прокси» автоматически восстанавливает заблокированные IP через туннели Cloudflare WARP.",
        "about.arch.agg": "<strong>Агрегатор:</strong> Собирает данные из более чем 600 источников каждые 6 часов.",
        "about.arch.pub": "<strong>Издатель:</strong> Генерирует оптимизированные конфиги для V2Ray, Clash, Sing-box (режимы Танк/Снайпер) и других.",
        "about.security.title": "Безопасность",
        "about.security.text": "Хотя мы проводим автоматические проверки безопасности (блокировка рекламы, вредоносных сайтов, ханипотов и проверка TLS), это публичные прокси. Мы рекомендуем использовать их для просмотра веб-страниц и избегать чувствительных операций (банкинг, пароли).",
        "about.btn.source": "Исходный код на GitHub",

        /* Analytics Page */
        "analytics.hero.title": "Сетевая разведка",
        "analytics.hero.subtitle": "Аналитика в реальном времени по глобальному распределению и производительности прокси.",
        "analytics.charts.protocol": "Распределение протоколов",
        "analytics.charts.latency": "Распределение задержки",
        "analytics.charts.countries": "Топ стран",

        /* Proxies Page */
        "proxies.hero.title": "Список прокси онлайн",
        "proxies.hero.subtitle": "Изучите наш полный список проверенных прокси. Ищите, сортируйте и находите идеальное соединение для ваших нужд."
    },
    ar: {
        "nav.home": "الرئيسية",
        "nav.proxies": "الخوادم الحية",
        "nav.analytics": "الإحصائيات",
        "nav.wiki": "الموسوعة",
        "nav.about": "عن المشروع",
        "hero.title": "إنترنت بلا قيود",
        "hero.subtitle": "تصفح بحرية مع تكوينات VPN المجانية والمحدثة تلقائيًا. نجمع الخوادم من 668+ مصدرًا كل 6 ساعات لضمان أفضل أداء.",
        "hero.browse": "تصفح القائمة",
        "hero.get": "احصل على الاشتراك",
        "pipeline.title": "حالة النظام",
        "stats.sourced": "إجمالي المصادر",
        "stats.unique": "خوادم فعالة",
        "stats.online": "متصل الآن",
        "stats.hybrid": "محرك هجين",
        "stats.hybrid.desc": "نواة Go + Python",
        "stats.update": "معدل التحديث",
        "stats.threats": "تهديدات تم تحييدها",
        "downloads.title": "تحميل التكوينات",
        "downloads.subtitle": "اختر التنسيق المناسب لجهازك. جميع الملفات محدثة ومفحوصة.",
        "downloads.universal": "اشتراك شامل (Universal)",
        "downloads.universal.desc": "رابط Base64 يعمل مع V2Ray و Xray ومعظم التطبيقات. يدعم التحديث التلقائي.",
        "downloads.singbox": "تكوين Sing-box",
        "downloads.singbox.desc": "ملف JSON مخصص لتطبيقات Sing-box و NekoBox.",
        "downloads.clash": "تكوين Clash",
        "downloads.clash.desc": "ملف YAML جاهز للاستخدام مع تطبيق Clash.",
        "downloads.shadowrocket": "Shadowrocket",
        "downloads.shadowrocket.desc": "تنسيق مخصص لتطبيق Shadowrocket على iOS.",
        "downloads.chosen.title": "🏆 قائمة الـ 1000 المميزة",
        "downloads.chosen.desc": "اختيارنا الأفضل: أسرع 50 خادم لكل بروتوكول. الخيار الأمثل لمعظم المستخدمين!",
        "downloads.chosen.btn": "نسخ الاشتراك المميز",
        "info.start.title": "كيف تبدأ",
        "info.start.text": "الأمر بسيط. انسخ رابط الاشتراك وقم باستيراده في تطبيق VPN الخاص بك.",
        "info.how.title": "كيف نعمل",
        "info.security.title": "الأمان",
        "info.community.title": "المجتمع",
        "footer.love": "مشروع شغوف لإنترنت حر ومفتوح. ✨",
        "formats.title": "دليل التنسيقات",
        "formats.base64": "Base64: رابط واحد لـ V2Ray, Xray, NekoBox.",
        "formats.singbox": "Sing-box: يشمل وضع 'القناص' (توجيه ذكي) و 'الدبابة' (VPN كامل).",
        "formats.clash": "Clash: ملف YAML لتطبيقات Clash.",
        "notice.title": "تنبيه أمني",
        "notice.text": "هذه خوادم عامة ومجانية. نحن نفحصها للأمان، لكن لا نضمن الخصوصية التامة.",
        "notice.list.1": "لا تستخدمها للمعاملات البنكية.",
        "notice.list.2": "ممتازة لتجاوز الحجب والتصفح.",
        "notice.list.3": "بياناتك تمر عبر خوادم طرف ثالث.",
        "notice.disclaimer": "الاستخدام على مسؤوليتك الشخصية.",
        "adapters.title": "🔌 تنسيقات أخرى",
        "adapters.subtitle": "دعم تجريبي لتطبيقات إضافية.",
        "byow.title": "🚀 وضع التيربو (BYOW)",
        "byow.url.placeholder": "رابط Cloudflare Worker...",
        "byow.uuid.placeholder": "اختياري: UUID",
        "byow.apply": "تفعيل",
        "byow.hint": "استخدم Worker خاص بك لاتصال سريع، خاص، وغير قابل للحجب.",
        "byow.download": "تحميل تكوين التيربو",
        "filters.search": "بحث: مثلاً fastest US vmess أو Germany < 100ms",
        "filters.protocol": "كل البروتوكولات",
        "filters.country": "كل الدول",
        "filters.city": "كل المدن",
        "filters.copy_all": "نسخ الكل",
        "filters.copy_filtered": "نسخ النتائج",
        "filters.download_filtered": "تحميل النتائج",
        "filters.empty_title": "لا توجد نتائج",
        "filters.empty_text": "لم نجد خوادم مطابقة لبحثك. جرب تغيير الفلاتر.",
        "table.protocol": "البروتوكول",
        "table.location": "الموقع",
        "table.latency": "السرعة",
        "table.status": "الحالة",
        "table.copy": "نسخ",
        "verify.local": "فحص محلي (WASM)",
        "verify.status": "جاهز للفحص",

        /* About Page */
        "about.hero.title": "عن ConfigStream",
        "about.subtitle": "وصول آلي، مرن، ومجاني للإنترنت المفتوح.",
        "about.mission.title": "المهمة",
        "about.mission.text": "تم بناء ConfigStream لتوفير وصول موثوق ومجاني للإنترنت العالمي للمستخدمين في بيئات الشبكات المقيدة. من خلال تجميع الخوادم من مئات المصادر العامة واختبارها بصرامة، نضمن توافرية عالية دون جهد يدوي.",
        "about.arch.title": "الهندسة: \"النواة المرنة\"",
        "about.arch.text": "نستخدم هندسة \"الميزانية الصفرية\" التي تعمل بالكامل على البنية التحتية لـ GitHub، مما يضمن الاستدامة ومقاومة الرقابة.",
        "about.arch.hybrid": "<strong>المحرك الهجين:</strong> يجمع بين مرونة Python للذكاء مع <strong>Go Sidecar</strong> عالي الأداء لاختبار الشبكة بشكل متزامن هائل.",
        "about.arch.intel": "<strong>طبقة الذكاء:</strong> تقنية \"تنظيف البروكسي\" الخاصة بنا تقوم بإصلاح عناوين IP المحظورة تلقائيًا عن طريق تمريرها عبر نفق Cloudflare WARP.",
        "about.arch.agg": "<strong>المجمع:</strong> يجلب من أكثر من 600 مصدر كل 6 ساعات.",
        "about.arch.pub": "<strong>الناشر:</strong> يولد تكوينات محسنة لـ V2Ray، Clash، Sing-box (أوضاع الدبابة/القناص)، والمزيد.",
        "about.security.title": "الأمان",
        "about.security.text": "بينما نقوم بإجراء فحوصات أمان تلقائية (حظر الإعلانات، ومواقع البرمجيات الخبيثة، ومصائد الجذب، والتحقق من TLS)، فهذه خوادم عامة. نوصي باستخدامها للتصفح وتجنب المعاملات الحساسة (البنوك، كلمات المرور).",
        "about.btn.source": "عرض المصدر على GitHub",

        /* Analytics Page */
        "analytics.hero.title": "ذكاء الشبكة",
        "analytics.hero.subtitle": "رؤى في الوقت الفعلي حول توزيع وأداء البروكسي العالمي.",
        "analytics.charts.protocol": "توزيع البروتوكول",
        "analytics.charts.latency": "توزيع سرعة الاستجابة",
        "analytics.charts.countries": "أهم الدول",

        /* Proxies Page */
        "proxies.hero.title": "قائمة الخوادم الحية",
        "proxies.hero.subtitle": "استكشف قائمتنا الكاملة من الخوادم التي تم فحصها. ابحث، ورتب، واعثر على الاتصال المثالي لاحتياجاتك."
    }
};

class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('lang') || 'en';
        this.observers = [];
    }

    setLanguage(lang) {
        if (!translations[lang]) {
            console.warn(`Language ${lang} not supported`);
            return;
        }
        this.currentLang = lang;
        localStorage.setItem('lang', lang);
        this.updatePage();

        // Set direction for RTL languages
        if (lang === 'fa' || lang === 'ar') {
            document.documentElement.setAttribute('dir', 'rtl');
        } else {
            document.documentElement.setAttribute('dir', 'ltr');
        }

        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
    }

    t(key) {
        return translations[this.currentLang][key] || translations['en'][key] || key;
    }

    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);

            if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
                 el.setAttribute('placeholder', translation);
            } else if (el.dataset.i18nHtml === 'true') {
                 // Allow HTML for specific keys if explicitly marked
                 // Sanitize translation before injecting as HTML to prevent XSS
                 const sanitized = this.sanitize(translation);
                 el.innerHTML = sanitized;
            } else {
                 el.textContent = translation;
            }
        });
    }

    sanitize(input) {
        // Minimal sanitizer: remove script/style, on* attrs, and javascript: URLs
        const tmp = document.createElement('div');
        tmp.innerHTML = input;

        const walker = document.createTreeWalker(tmp, NodeFilter.SHOW_ELEMENT, null);
        const disallowedTags = new Set(['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'LINK', 'META']);
        const allowedAttrs = new Set(['href', 'title', 'alt', 'src', 'class', 'id', 'role', 'aria-label', 'aria-hidden']);

        const toRemove = [];
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (disallowedTags.has(node.tagName)) {
                toRemove.push(node);
                continue;
            }
            // Remove event handlers and disallowed attributes
            [...node.attributes].forEach(attr => {
                const name = attr.name.toLowerCase();
                const value = attr.value || '';
                if (name.startsWith('on') || (!allowedAttrs.has(name) && !name.startsWith('data-'))) {
                    node.removeAttribute(attr.name);
                    return;
                }
                if ((name === 'href' || name === 'src') && value.trim().toLowerCase().startsWith('javascript:')) {
                    node.removeAttribute(attr.name);
                }
            });
        }
        toRemove.forEach(n => n.remove());
        return tmp.innerHTML;
    }
}

window.i18n = new I18n();
document.addEventListener('DOMContentLoaded', () => {
    window.i18n.setLanguage(window.i18n.currentLang);
});
