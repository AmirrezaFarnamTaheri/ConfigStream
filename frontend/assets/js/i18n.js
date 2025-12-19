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
        "hero.subtitle.prefix": "Access the open web with our free, auto-updating VPN configurations. We aggregate fresh proxies from",
        "hero.subtitle.middle": "sources every",
        "hero.subtitle.suffix": "hours, ensuring you always have a reliable connection.",
        "hero.subtitle.powered": "Powered by the <strong>Resilient Core</strong> hybrid engine for maximum reliability.",
        "hero.browse": "Browse Proxies",
        "hero.get": "Get Configs",

        "pipeline.title": "Live Pipeline Status",

        "stats.sourced": "Total Sourced",
        "stats.unique": "Unique & Verified",
        "stats.online": "Online Now",
        "stats.clean": "Clean (Native)",
        "stats.revived": "Revived (Washed)",
        "stats.hybrid": "Hybrid Engine",
        "stats.hybrid.desc": "Go + Python Core",
        "stats.update": "Update Frequency",
        "stats.threats": "Threats Blocked",
        "stats.chains": "Smart Chains",
        "stats.vwarp": "Vwarp Efficiency",

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
        "downloads.chosen.title": "Chosen Top 1000",
        "downloads.chosen.desc": "Our premium selection: Top 50 proxies per protocol, ranked by lowest latency. The best choice for most users!",
        "downloads.chosen.btn": "Copy Chosen Subscription",
        "downloads.sniper": "Sniper",
        "downloads.tank": "Tank",
        "downloads.download": "Download",

        "info.start.title": "Getting Started",
        "info.start.text": "It's simple: 1. Choose your preferred format above. 2. Copy the subscription link. 3. Import it into your VPN client (V2Ray, Clash, Sing-box, etc.).",
        "info.start.step1": "<strong>Choose a format</strong> from the subscription links above based on your VPN client (V2Ray, Clash, Sing-box, etc.)",
        "info.start.step2": "<strong>Copy the link</strong> by clicking the copy button",
        "info.start.step3": "<strong>Import</strong> the subscription into your VPN client's subscription manager",
        "info.start.step4": "<strong>Update</strong> the subscription to fetch the latest proxies",
        "info.start.step5": "<strong>Connect</strong> to any proxy from the list and enjoy!",
        "info.start.tip": "💡 <em>Tip: Subscriptions auto-update, so you'll always have fresh, working proxies!</em>",
        "info.how.title": "How It Works",
        "info.how.text": "ConfigStream uses a fully automated, zero-cost pipeline running on GitHub Actions:",
        "info.how.collection": "Collection:",
        "info.how.collection.text": "Every",
        "info.how.collection.hours": "hours, we aggregate proxies from over",
        "info.how.collection.sources": "public sources worldwide",
        "info.how.dedup": "<strong>Deduplication:</strong> Advanced filtering removes duplicates and invalid entries",
        "info.how.verify": "<strong>Verification:</strong> Our hybrid Go + Python engine tests each proxy for connectivity and performance",
        "info.how.security": "<strong>Security Scanning:</strong> Automated checks filter out honeypots, malware hosts, and unsafe nodes",
        "info.how.optimize": "<strong>Optimization:</strong> Proxies are ranked by latency and reliability",
        "info.how.publish": "<strong>Publishing:</strong> Configs are auto-generated for all major VPN clients",
        "info.how.highlight.title": "🧠 Network Intelligence",
        "info.how.highlight.text": "We optimize routes and revive blocked IPs using advanced washing techniques.",
        "info.security.title": "Security & Privacy",
        "info.community.title": "Open Source",

        "footer.love": "Empowering global access to information. Open Source & Forever Free. ✨",
        "footer.lastupdated": "Last updated:",
        "footer.checking": "checking...",

        "formats.title": "Format Guide",
        "formats.base64": "Universal (Base64): The standard subscription format. Compatible with V2RayNG, v2rayN, Streisand, and most clients. Best for general use.",
        "formats.singbox": "Sing-box JSON: Next-gen configuration. 'Sniper' mode auto-routes traffic based on latency. 'Tank' mode tunnels everything.",
        "formats.clash": "Clash YAML: Ready-to-import profile for Clash for Windows, Clash Verge, and Stash. Includes rule-based routing.",

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
        "table.process": "Process",
        "table.history": "History",
        "table.copy": "Copy Link",

        "verify.local": "Turbo-Verify (Local)",
        "verify.status": "Ready to verify via WASM",

        /* About Page */
        "about.hero.title": "About ConfigStream",
        "about.title": "Our Mission",
        "about.subtitle": "To provide free, uncensored, and secure internet access to everyone, everywhere. We believe information is a human right.",

        /* Core Pillars */
        "about.pillar1.title": "Zero Budget, Maximum Impact",
        "about.pillar1.text": "We operate entirely on free infrastructure (GitHub Actions/Pages). This guarantees sustainability—we can't run out of funds because we don't spend any.",
        "about.pillar2.title": "Automated Intelligence",
        "about.pillar2.text": "Our hybrid Python/Go engine (\"Resilient Core\") automatically scrapes, deduplicates, tests, and \"washes\" thousands of proxies every 6 hours.",
        "about.pillar3.title": "Radical Transparency",
        "about.pillar3.text": "Open source from day one. Every line of code, every metric, and every configuration is public and auditable by the community.",

        /* Technology & Protocols */
        "about.tech.title": "Under the Hood",
        "about.protocols.title": "Supported Protocols & Clients",

        /* Join Us */
        "about.join.title": "Join the Movement",
        "about.join.text": "ConfigStream is built by the community, for the community.",
        "about.join.btn": "Contribute on GitHub",
        "about.mission.title": "Our Mission",
        "about.mission.text": "ConfigStream is an automated, open-source intelligence platform designed to aggregate, test, and distribute high-performance proxy configurations. In an era of increasing internet censorship and fragmentation, we provide the tools to maintain connectivity and bypass restrictions securely.",
        "about.architecture.title": "Core Architecture",
        "about.architecture.text": "The platform operates on a \"Zero Budget\" philosophy, leveraging GitHub Actions for compute and GitHub Pages for distribution. Our hybrid engine combines the flexibility of Python with the raw performance of Go.",
        "about.tech.hybrid_engine": "Hybrid Engine",
        "about.tech.hybrid_engine_desc": "Python orchestrates the logic, while a custom Go binary handles high-concurrency network scanning and testing.",
        "about.tech.washer": "The Washer (Proxy Reviver)",
        "about.tech.washer_desc": "Our intelligent \"Washer\" module wraps flagged or dirty proxies in Cloudflare WARP tunnels, reviving them for safe use.",
        "about.tech.smart_routing": "Smart Routing",
        "about.tech.smart_routing_desc": "Topology-aware chaining connects domestic relays to foreign exit nodes, bypassing deep packet inspection (DPI).",
        "about.tech.scanner": "Active Scanner",
        "about.tech.scanner_desc": "A built-in Go scanner actively discovers fresh, low-latency Cloudflare endpoints to ensure maximum performance.",
        "about.security.title": "Security & Intelligence",
        "about.security.text": "ConfigStream incorporates multi-layered security validation to ensure proxy safety and reliability. Our intelligence pipeline filters out malicious nodes through comprehensive threat detection.",
        "about.security.firehol": "FireHol Blocklist Integration",
        "about.security.firehol_desc": "Real-time validation against known malicious IP addresses from FireHol's community-maintained blocklists.",
        "about.security.honeypot": "Honeypot Detection",
        "about.security.honeypot_desc": "Advanced heuristics identify and filter out honeypot traps designed to monitor user activity.",
        "about.security.validation": "Configuration Validation",
        "about.security.validation_desc": "Strict parsing and validation ensures all configs are well-formed, non-malicious, and standards-compliant.",
        "about.security.resharding": "Dynamic Resharding",
        "about.security.resharding_desc": "Intelligent load balancing based on actual fetch and test times ensures optimal pipeline performance.",
        "about.credits.title": "Credits & Acknowledgements",
        "about.credits.text": "ConfigStream is built on the shoulders of giants. We extend our gratitude to the following projects and communities:",
        "about.credits.core": "Core Technologies",
        "about.credits.core_desc": "• <strong>Sing-box:</strong> Advanced routing engine<br>• <strong>Python & Go:</strong> Hybrid pipeline architecture<br>• <strong>WebAssembly:</strong> Client-side verification",
        "about.credits.data": "Data & Intelligence",
        "about.credits.data_desc": "• <strong>IRCF & MortezaBashsiz:</strong> Community WARP tools<br>• <strong>FireHol:</strong> IP blocklist database<br>• <strong>MaxMind GeoIP2:</strong> Geolocation services",
        "about.credits.frontend": "Frontend & Visualization",
        "about.credits.frontend_desc": "• <strong>Globe.gl:</strong> 3D globe visualization<br>• <strong>Chart.js:</strong> Analytics charts<br>• <strong>Feather Icons:</strong> Modern icon system",
        "about.credits.fonts": "Fonts & Typography",
        "about.credits.fonts_desc": "• <strong>Be Vietnam Pro:</strong> Primary UI font<br>• <strong>Vazirmatn:</strong> Farsi/Arabic UI font<br>• <strong>Mikhak:</strong> Farsi/Arabic display font",
        "about.credits.thanks": "<strong>Special Thanks:</strong> To all the open-source proxy list maintainers and the community contributors who make this platform possible.",
        "about.opensource.title": "Open Source & License",
        "about.opensource.text": "ConfigStream is released under the <strong>AGPLv3 License</strong>, ensuring it remains free and open source forever. We believe in transparency, community-driven development, and unrestricted access to information.",
        "about.opensource.btn": "View on GitHub",
        "about.footer": "&copy; 2025 ConfigStream. Open Source (AGPLv3).",
        "about.arch.title": "Architecture: The \"Resilient Core\"",
        "about.arch.text": "Built on a \"Zero Budget\" philosophy, ConfigStream leverages the immense power of distributed CI/CD infrastructure (GitHub Actions) to create a self-sustaining, unstoppable pipeline. We don't rely on expensive servers that can be blocked or taken down.",
        "about.arch.hybrid": "<strong>Hybrid Engine:</strong> A fusion of Python's analytical intelligence and a high-performance <strong>Go Sidecar</strong> for massively concurrent, raw-socket network verification.",
        "about.arch.intel": "<strong>Intelligence Layer:</strong> Features \"Proxy Washing\" technology that automatically rehabilitates blocked IPs by tunneling traffic through Cloudflare WARP, creating robust \"Smart Chains\".",
        "about.arch.agg": "<strong>Global Aggregator:</strong> Scrapes, parses, and normalizes data from over 600 public sources every 6 hours.",
        "about.arch.pub": "<strong>Universal Publisher:</strong> Delivers optimized configurations for every major client: V2Ray, Clash, Sing-box ('Sniper' routing & 'Tank' tunneling), and more.",
        "about.btn.source": "View Source on GitHub",

        /* Analytics Page */
        "analytics.hero.title": "Network Intelligence",
        "analytics.hero.subtitle": "Real-time insights into global proxy distribution and performance.",
        "analytics.charts.protocol": "Protocol Distribution",
        "analytics.charts.latency": "Latency Distribution",
        "analytics.charts.countries": "Top Countries",
        "analytics.charts.rejection": "Rejection Logic",
        "analytics.charts.threats": "Threat Distribution",
        "analytics.charts.asns": "Top ISPs / ASNs",
        "analytics.charts.latency_by_country": "Latency by Country",
        "analytics.charts.latency_by_protocol": "Latency by Protocol",

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
        "hero.subtitle.prefix": "使用我们免费、自动更新的 VPN 配置访问全球网络。系统每",
        "hero.subtitle.middle": "小时从",
        "hero.subtitle.suffix": "个精选源获取新鲜代理，确保您时刻拥有稳定可靠的连接。",
        "hero.subtitle.powered": "由 <strong>Resilient Core</strong> 混合引擎提供动力，实现最大可靠性。",
        "hero.browse": "浏览节点",
        "hero.get": "获取订阅",
        "pipeline.title": "实时系统状态",
        "stats.sourced": "采集源总数",
        "stats.unique": "去重后可用",
        "stats.online": "当前在线",
        "stats.clean": "干净（原生）",
        "stats.revived": "复活（清洗）",
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
        "downloads.chosen.title": "精选 Top 1000",
        "downloads.chosen.desc": "优选合集：按低延迟排序，每种协议精选前 50 个节点。绝大多数用户的最佳选择！",
        "downloads.chosen.btn": "复制精选订阅",
        "info.start.title": "快速上手",
        "info.start.text": "使用很简单：① 选择上方的订阅格式 ② 复制订阅链接 ③ 在您的代理客户端（V2Ray、Clash、Sing-box 等）中导入即可。",
        "info.start.step1": "<strong>选择格式</strong>：根据您的客户端（V2Ray、Clash、Sing-box 等）选择适合的格式",
        "info.start.step2": "<strong>复制链接</strong>：点击复制按钮复制订阅链接",
        "info.start.step3": "<strong>导入</strong>：将订阅链接导入到您的客户端的订阅管理器中",
        "info.start.step4": "<strong>更新</strong>：更新订阅以获取最新节点",
        "info.start.step5": "<strong>连接</strong>：从列表中选择任何节点，开始使用！",
        "info.start.tip": "💡 <em>提示：订阅会自动更新，您会拥有持续新鲜的、工作中的节点！</em>",
        "info.how.title": "工作原理",
        "info.how.text": "ConfigStream 使用 GitHub Actions 运行全自动、零成本管道：",
        "info.how.collection": "采集：",
        "info.how.collection.text": "每",
        "info.how.collection.hours": "小时，我们从全球",
        "info.how.collection.sources": "个公开来源聚合代理",
        "info.how.dedup": "<strong>去重：</strong> 高级过滤去除重复和无效项",
        "info.how.verify": "<strong>验证：</strong> 我们的混合 Go + Python 引擎测试每个代理的连接性和性能",
        "info.how.security": "<strong>安全扫描：</strong> 自动检查过滤掉蜜罐、恶意主机和不安全节点",
        "info.how.optimize": "<strong>优化：</strong> 代理按延迟和可靠性排序",
        "info.how.publish": "<strong>发布：</strong> 为所有主要 VPN 客户端自动生成配置",
        "info.how.highlight.title": "🧠 网络智能",
        "info.how.highlight.text": "我们采用先进的清洗技术优化路由，复活被封禁的 IP 地址。",
        "info.security.title": "安全与隐私",
        "info.community.title": "开源项目",
        "footer.love": "为自由互联网而生的开源项目。✨",
        "footer.lastupdated": "最后更新：",
        "footer.checking": "检查中...",
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
        "table.process": "处理",
        "table.history": "历史",
        "table.copy": "复制链接",
        "verify.local": "本地极速验证",
        "verify.status": "WASM 组件就绪",

        /* About Page */
        "about.hero.title": "关于 ConfigStream",
        "about.subtitle": "自动化、高可用、免费访问开放互联网。",
        "about.mission.title": "使命",
        "about.mission.text": "我们相信获取信息是一项基本权利。ConfigStream 自动化地发现、测试和优化抗审查的代理节点，为受限网络环境中的用户提供可靠的通道—完全免费。",
        "about.arch.title": "架构：“弹性核心”",
        "about.arch.text": "我们采用“零预算”架构，完全运行在 GitHub 的基础设施上，确保可持续性和抗审查性。",
        "about.arch.hybrid": "<strong>混合引擎：</strong> 结合 Python 的灵活性（用于情报分析）与高性能 <strong>Go Sidecar</strong>（用于大规模并发网络测试）。",
        "about.arch.intel": "<strong>情报层：</strong> 我们的“代理清洗”技术通过 Cloudflare WARP 隧道自动修复被屏蔽的 IP。",
        "about.arch.agg": "<strong>聚合器：</strong> 每 6 小时从 668+ 个来源获取数据。",
        "about.arch.pub": "<strong>发布器：</strong> 为 V2Ray、Clash、Sing-box（坦克/狙击手模式）等生成优化配置。",
        "about.security.title": "安全性",
        "about.security.text": "虽然我们执行自动安全检查（拦截广告、恶意软件网站、蜜罐和 TLS 验证），但这些是公共代理。我们建议仅用于浏览，避免进行敏感交易（如银行、密码）。",
        "about.btn.source": "在 GitHub 上查看源码",

        /* Analytics Page */
        "analytics.hero.title": "网络情报",
        "analytics.hero.subtitle": "实时洞察全球代理节点的分布与性能表现。",
        "analytics.charts.protocol": "协议分布",
        "analytics.charts.latency": "延迟分布",
        "analytics.charts.countries": "热门国家",
        "analytics.charts.rejection": "拒绝逻辑",
        "analytics.charts.threats": "威胁分布",
        "analytics.charts.asns": "顶级互联网提供商",
        "analytics.charts.latency_by_country": "按国家延迟",
        "analytics.charts.latency_by_protocol": "按协议延迟",

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

        "wiki.nav.home": "صفحه اصلی دانشنامه",
        "wiki.nav.intro": "مقدمه",
        "wiki.nav.arch": "معماری سیستم",
        "wiki.nav.proto": "پروتکل‌ها",
        "wiki.nav.eng": "جزئیات فنی",
        "wiki.nav.devops": "دواپس و استقرار",
        "wiki.nav.frontend": "فرانت‌اند",
        "wiki.nav.security": "امنیت",
        "wiki.nav.api": "مرجع API",
        "wiki.nav.contributing": "مشارکت در پروژه",
        "wiki.nav.troubleshooting": "عیب‌یابی",
        "wiki.nav.page_home": "صفحه: خانه",
        "wiki.nav.page_analytics": "صفحه: آمار",
        "wiki.nav.page_proxies": "صفحه: پروکسی‌ها",
        "wiki.nav.page_about": "صفحه: درباره ما",

        "hero.title": "دروازه‌ای به اینترنت آزاد",
        "hero.subtitle.prefix": "با کانفیگ‌های رایگان و خودکار ما، بدون محدودیت به اینترنت دسترسی داشته باشید. سیستم ما هر",
        "hero.subtitle.middle": "ساعت پروکسی‌های تازه را از",
        "hero.subtitle.suffix": "منبع دریافت می‌کند تا اتصالی پایدار را تضمین کند.",
        "hero.subtitle.powered": "قدرت‌گرفته از موتور ترکیبی <strong>Resilient Core</strong> برای حداکثر قابلیت اطمینان.",
        "hero.browse": "مشاهده پروکسی‌ها",
        "hero.get": "دریافت کانفیگ",
        "pipeline.title": "وضعیت لحظه‌ای سیستم",
        "stats.sourced": "کل منابع",
        "stats.unique": "تست شده و سالم",
        "stats.online": "آنلاین",
        "stats.clean": "پاک (بومی)",
        "stats.revived": "احیا شده (شسته)",
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
        "downloads.chosen.title": "گلچین ۱۰۰۰ تایی",
        "downloads.chosen.desc": "انتخاب ویژه ما: ۵۰ پروکسی برتر از هر پروتکل با کمترین پینگ. بهترین گزینه برای اکثر کاربران!",
        "downloads.chosen.btn": "کپی اشتراک ویژه",
        "info.start.title": "راهنمای شروع",
        "info.start.text": "استفاده خیلی راحت است: ۱. فرمت مورد نظر را انتخاب کنید ۲. لینک اشتراک را کپی کنید ۳. در برنامه فیلترشکن خود (V2Ray، Clash، Sing-box و غیره) وارد کنید.",
        "info.start.step1": "<strong>انتخاب فرمت</strong>: بر اساس برنامه خود (V2Ray، Clash، Sing-box و غیره) فرمت مناسب را از لینک‌های بالا انتخاب کنید",
        "info.start.step2": "<strong>کپی لینک</strong>: روی دکمه کپی کلیک کنید",
        "info.start.step3": "<strong>ایمپورت</strong>: لینک اشتراک را در بخش مدیریت اشتراک‌های برنامه خود وارد کنید",
        "info.start.step4": "<strong>بروزرسانی</strong>: اشتراک را آپدیت کنید تا جدیدترین پروکسی‌ها را دریافت کنید",
        "info.start.step5": "<strong>اتصال</strong>: به یکی از پروکسی‌ها متصل شوید و لذت ببرید!",
        "info.start.tip": "💡 <em>نکته: اشتراک‌ها به صورت خودکار آپدیت می‌شوند، پس همیشه پروکسی‌های تازه خواهید داشت!</em>",
        "info.how.title": "نحوه کارکرد",
        "info.how.text": "ConfigStream از یک خط لوله کاملاً خودکار و رایگان روی GitHub Actions استفاده می‌کند:",
        "info.how.collection": "جمع‌آوری:",
        "info.how.collection.text": "هر",
        "info.how.collection.hours": "ساعت، پروکسی‌ها را از بیش از",
        "info.how.collection.sources": "منبع عمومی در سراسر جهان جمع‌آوری می‌کنیم",
        "info.how.dedup": "<strong>حذف تکراری‌ها:</strong> فیلترینگ پیشرفته موارد تکراری و نامعتبر را حذف می‌کند",
        "info.how.verify": "<strong>تست و بررسی:</strong> موتور ترکیبی Go + Python ما اتصال و عملکرد هر پروکسی را تست می‌کند",
        "info.how.security": "<strong>اسکن امنیتی:</strong> بررسی‌های خودکار هانی‌پات‌ها، بدافزارها و نودهای ناامن را فیلتر می‌کنند",
        "info.how.optimize": "<strong>بهینه‌سازی:</strong> پروکسی‌ها بر اساس پینگ و پایداری رتبه‌بندی می‌شوند",
        "info.how.publish": "<strong>انتشار:</strong> کانفیگ‌ها به صورت خودکار برای تمام کلاینت‌های اصلی VPN تولید می‌شوند",
        "info.how.highlight.title": "🧠 هوش شبکه",
        "info.how.highlight.text": "ما با تکنیک‌های پیشرفته مسیریابی را بهینه می‌کنیم و IPهای مسدود شده را احیا می‌کنیم.",
        "info.security.title": "امنیت و حریم خصوصی",
        "info.community.title": "متن‌باز",
        "footer.love": "پروژه‌ای دلی برای آزادی اینترنت. ✨",
        "footer.lastupdated": "آخرین بروزرسانی:",
        "footer.checking": "در حال بررسی...",
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
        "table.process": "پردازش",
        "table.history": "تاریخچه",
        "table.copy": "کپی",
        "verify.local": "تست سرعت (محلی)",
        "verify.status": "آماده تست با WASM",

        /* About Page */
        "about.hero.title": "درباره ConfigStream",
        "about.subtitle": "دسترسی خودکار، پایدار و رایگان به اینترنت آزاد.",
        "about.mission.title": "ماموریت",
        "about.mission.text": "ما معتقدیم دسترسی به اطلاعات یک حق بنیادین است. ConfigStream به صورت خودکار پروکسی‌های مقاوم در برابر سانسور را کشف، تست و بهینه می‌کند و یک راه نجات قابل اعتماد برای کاربران در محیط‌های تحت محدودیت فراهم می‌آورد—کاملاً رایگان.",
        "about.arch.title": "معماری: \"هسته مقاوم\"",
        "about.arch.text": "ما از معماری \"بودجه صفر\" استفاده می‌کنیم که کاملاً بر روی زیرساخت گیت‌هاب اجرا می‌شود و پایداری و مقاومت در برابر سانسور را تضمین می‌کند.",
        "about.arch.hybrid": "<strong>موتور ترکیبی:</strong> ترکیب انعطاف‌پذیری پایتون برای هوش مصنوعی با <strong>Go Sidecar</strong> قدرتمند برای تست همزمان شبکه.",
        "about.arch.intel": "<strong>لایه هوشمند:</strong> فناوری «پاکسازی پروکسی» ما به‌طور خودکار IPهای مسدود شده را از طریق تونل Cloudflare WARP بازیابی می‌کند.",
        "about.arch.agg": "<strong>جمع‌آوری‌کننده:</strong> هر ۶ ساعت از بیش از ۶۶۸ منبع اطلاعات دریافت می‌کند.",
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
        "analytics.charts.rejection": "منطق رد",
        "analytics.charts.threats": "توزیع تهدیدات",
        "analytics.charts.asns": "ارائه‌دهندگان اینترنت برتر",
        "analytics.charts.latency_by_country": "تاخیر بر اساس کشور",
        "analytics.charts.latency_by_protocol": "تاخیر بر اساس پروتکل",

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

        "wiki.nav.home": "Главная вики",
        "wiki.nav.intro": "Введение",
        "wiki.nav.arch": "Архитектура",
        "wiki.nav.proto": "Протоколы",
        "wiki.nav.eng": "Инженерия",
        "wiki.nav.devops": "DevOps",
        "wiki.nav.frontend": "Фронтенд",
        "wiki.nav.security": "Безопасность",
        "wiki.nav.api": "Справка API",
        "wiki.nav.contributing": "Участие в проекте",
        "wiki.nav.troubleshooting": "Устранение неполадок",
        "wiki.nav.page_home": "Страница: Главная",
        "wiki.nav.page_analytics": "Страница: Аналитика",
        "wiki.nav.page_proxies": "Страница: Прокси",
        "wiki.nav.page_about": "Страница: О проекте",

        "hero.title": "Интернет без границ",
        "hero.subtitle.prefix": "Получите свободный доступ к сети с нашими бесплатными, автообновляемыми VPN-конфигурациями. Мы собираем свежие прокси из",
        "hero.subtitle.middle": "источников каждые",
        "hero.subtitle.suffix": "часов.",
        "hero.subtitle.powered": "Работает на <strong>Resilient Core</strong> — гибридном движке для максимальной надежности.",
        "hero.browse": "Найти прокси",
        "hero.get": "Скачать конфиги",
        "pipeline.title": "Статус системы",
        "stats.sourced": "Всего источников",
        "stats.unique": "Рабочих прокси",
        "stats.online": "Онлайн сейчас",
        "stats.clean": "Чистые (нативные)",
        "stats.revived": "Восстановленные (промытые)",
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
        "downloads.chosen.title": "Топ 1000 Лучших",
        "downloads.chosen.desc": "Наш выбор: 50 лучших прокси каждого протокола с минимальной задержкой. Идеально для большинства задач!",
        "downloads.chosen.btn": "Копировать Топ-подписку",
        "info.start.title": "Как начать",
        "info.start.text": "Это просто: 1. Выберите нужный формат выше 2. Скопируйте ссылку на подписку 3. Импортируйте её в ваш VPN-клиент (V2Ray, Clash, Sing-box и т.д.).",
        "info.start.step1": "<strong>Выберите формат</strong> в зависимости от вашего клиента (V2Ray, Clash, Sing-box и т.д.)",
        "info.start.step2": "<strong>Скопируйте ссылку</strong> нажав кнопку копирования",
        "info.start.step3": "<strong>Импортируйте</strong> подписку в менеджер подписок вашего VPN-клиента",
        "info.start.step4": "<strong>Обновите</strong> подписку, чтобы получить последние прокси",
        "info.start.step5": "<strong>Подключитесь</strong> к любому прокси из списка и наслаждайтесь!",
        "info.start.tip": "💡 <em>Совет: Подписки обновляются автоматически, поэтому у вас всегда будут свежие рабочие прокси!</em>",
        "info.how.title": "Как это работает",
        "info.how.text": "ConfigStream использует полностью автоматизированный, бесплатный конвейер на GitHub Actions:",
        "info.how.collection": "Сбор:",
        "info.how.collection.text": "Каждые",
        "info.how.collection.hours": "часов мы собираем прокси из более чем",
        "info.how.collection.sources": "публичных источников по всему миру",
        "info.how.dedup": "<strong>Дедупликация:</strong> Продвинутая фильтрация удаляет дубликаты и невалидные записи",
        "info.how.verify": "<strong>Проверка:</strong> Наш гибридный Go + Python движок тестирует каждый прокси на связность и производительность",
        "info.how.security": "<strong>Сканирование безопасности:</strong> Автоматические проверки фильтруют медоносы, вредоносные хосты и небезопасные узлы",
        "info.how.optimize": "<strong>Оптимизация:</strong> Прокси ранжируются по задержке и надежности",
        "info.how.publish": "<strong>Публикация:</strong> Конфиги автоматически генерируются для всех основных VPN-клиентов",
        "info.how.highlight.title": "🧠 Сетевой интеллект",
        "info.how.highlight.text": "Мы оптимизируем маршруты и восстанавливаем заблокированные IP с помощью продвинутых техник очистки.",
        "info.security.title": "Безопасность и приватность",
        "info.community.title": "Открытый исходный код",
        "footer.love": "Сделано с любовью к свободному интернету. ✨",
        "footer.lastupdated": "Последнее обновление:",
        "footer.checking": "проверка...",
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
        "table.process": "Тип",
        "table.history": "История",
        "table.copy": "Копировать",
        "verify.local": "Быстрая проверка (Local)",
        "verify.status": "WASM готов к работе",

        /* About Page */
        "about.hero.title": "О ConfigStream",
        "about.subtitle": "Автоматизированный, надежный и бесплатный доступ к открытому интернету.",
        "about.mission.title": "Миссия",
        "about.mission.text": "Мы верим, что доступ к информации — это фундаментальное право. ConfigStream автоматизирует поиск, тестирование и оптимизацию прокси, устойчивых к цензуре, предоставляя надёжный канал связи для пользователей в условиях ограниченного доступа к сети—совершенно бесплатно.",
        "about.arch.title": "Архитектура: \"Устойчивое ядро\"",
        "about.arch.text": "Мы используем архитектуру \"Нулевой бюджет\", которая полностью работает на инфраструктуре GitHub, обеспечивая устойчивость и сопротивление цензуре.",
        "about.arch.hybrid": "<strong>Гибридный движок:</strong> Сочетает гибкость Python для анализа с высокопроизводительным <strong>Go Sidecar</strong> для массового параллельного тестирования сети.",
        "about.arch.intel": "<strong>Интеллектуальный слой:</strong> Наша технология «очистки прокси» автоматически восстанавливает заблокированные IP через туннели Cloudflare WARP.",
        "about.arch.agg": "<strong>Агрегатор:</strong> Собирает данные из более чем 668 источников каждые 6 часов.",
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
        "analytics.charts.rejection": "Логика отклонения",
        "analytics.charts.threats": "Распределение угроз",
        "analytics.charts.asns": "Топ провайдеры",
        "analytics.charts.latency_by_country": "Задержка по странам",
        "analytics.charts.latency_by_protocol": "Задержка по протоколам",

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

        "wiki.nav.home": "الصفحة الرئيسية للموسوعة",
        "wiki.nav.intro": "مقدمة",
        "wiki.nav.arch": "البنية المعمارية",
        "wiki.nav.proto": "البروتوكولات",
        "wiki.nav.eng": "الهندسة",
        "wiki.nav.devops": "العمليات والتطوير",
        "wiki.nav.frontend": "الواجهة الأمامية",
        "wiki.nav.security": "الأمان",
        "wiki.nav.api": "مرجع API",
        "wiki.nav.contributing": "المساهمة",
        "wiki.nav.troubleshooting": "استكشاف الأخطاء",
        "wiki.nav.page_home": "صفحة: الرئيسية",
        "wiki.nav.page_analytics": "صفحة: الإحصائيات",
        "wiki.nav.page_proxies": "صفحة: الخوادم",
        "wiki.nav.page_about": "صفحة: عن المشروع",

        "hero.title": "إنترنت بلا قيود",
        "hero.subtitle.prefix": "تصفح بحرية مع تكوينات VPN المجانية والمحدثة تلقائيًا. نجمع الخوادم من",
        "hero.subtitle.middle": "مصدرًا كل",
        "hero.subtitle.suffix": "ساعات لضمان أفضل أداء.",
        "hero.subtitle.powered": "مدعوم بمحرك <strong>Resilient Core</strong> الهجين لتحقيق أقصى موثوقية.",
        "hero.browse": "تصفح القائمة",
        "hero.get": "احصل على الاشتراك",
        "pipeline.title": "حالة النظام",
        "stats.sourced": "إجمالي المصادر",
        "stats.unique": "خوادم فعالة",
        "stats.online": "متصل الآن",
        "stats.clean": "نظيف (أصلي)",
        "stats.revived": "تم إحياؤه (مغسول)",
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
        "downloads.chosen.title": "قائمة الـ 1000 المميزة",
        "downloads.chosen.desc": "اختيارنا الأفضل: أسرع 50 خادم لكل بروتوكول. الخيار الأمثل لمعظم المستخدمين!",
        "downloads.chosen.btn": "نسخ الاشتراك المميز",
        "info.start.title": "كيف تبدأ",
        "info.start.text": "الأمر بسيط: ١. اختر التنسيق المناسب أعلاه ٢. انسخ رابط الاشتراك ٣. قم باستيراده في تطبيق VPN الخاص بك (V2Ray أو Clash أو Sing-box وغيرها).",
        "info.start.step1": "<strong>اختر التنسيق</strong> من روابط الاشتراك أعلاه بناءً على تطبيق VPN الخاص بك (V2Ray أو Clash أو Sing-box وغيرها)",
        "info.start.step2": "<strong>انسخ الرابط</strong> بالنقر على زر النسخ",
        "info.start.step3": "<strong>استيراد</strong> الاشتراك إلى مدير الاشتراكات في تطبيق VPN الخاص بك",
        "info.start.step4": "<strong>تحديث</strong> الاشتراك لجلب أحدث الخوادم",
        "info.start.step5": "<strong>اتصال</strong> بأي خادم من القائمة واستمتع!",
        "info.start.tip": "💡 <em>تلميح: الاشتراكات تتحدث تلقائيًا، لذلك ستحصل دائمًا على خوادم جديدة وتعمل!</em>",
        "info.how.title": "كيف نعمل",
        "info.how.text": "ConfigStream يستخدم خط أنابيب آلي بالكامل ومجاني على GitHub Actions:",
        "info.how.collection": "الجمع:",
        "info.how.collection.text": "كل",
        "info.how.collection.hours": "ساعات، نجمع الخوادم الوكيلة من أكثر من",
        "info.how.collection.sources": "مصدر عام حول العالم",
        "info.how.dedup": "<strong>إزالة التكرار:</strong> تصفية متقدمة تزيل التكرارات والإدخالات غير الصالحة",
        "info.how.verify": "<strong>التحقق:</strong> محركنا الهجين Go + Python يختبر اتصال وأداء كل خادم",
        "info.how.security": "<strong>فحص الأمان:</strong> الفحوصات الآلية تصفي مصائد الجذب والمضيفين الضارين والعقد غير الآمنة",
        "info.how.optimize": "<strong>التحسين:</strong> يتم تصنيف الخوادم حسب سرعة الاستجابة والموثوقية",
        "info.how.publish": "<strong>النشر:</strong> يتم إنشاء التكوينات تلقائيًا لجميع عملاء VPN الرئيسيين",
        "info.how.highlight.title": "🧠 الذكاء الشبكي",
        "info.how.highlight.text": "نقوم بتحسين المسارات وإحياء عناوين IP المحجوبة باستخدام تقنيات متقدمة.",
        "info.security.title": "الأمان والخصوصية",
        "info.community.title": "مفتوح المصدر",
        "footer.love": "مشروع شغوف لإنترنت حر ومفتوح. ✨",
        "footer.lastupdated": "آخر تحديث:",
        "footer.checking": "جاري الفحص...",
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
        "table.process": "المعالجة",
        "table.history": "التاريخ",
        "table.copy": "نسخ",
        "verify.local": "فحص محلي (WASM)",
        "verify.status": "جاهز للفحص",

        /* About Page */
        "about.hero.title": "عن ConfigStream",
        "about.subtitle": "وصول آلي، مرن، ومجاني للإنترنت المفتوح.",
        "about.mission.title": "المهمة",
        "about.mission.text": "نؤمن بأن الوصول إلى المعلومات حق أساسي. يقوم ConfigStream بأتمتة اكتشاف واختبار وتحسين الخوادم المقاومة للرقابة، مما يوفر قناة اتصال موثوقة للمستخدمين في بيئات الشبكات المقيدة—مجانًا تمامًا.",
        "about.arch.title": "الهندسة: \"النواة المرنة\"",
        "about.arch.text": "نستخدم هندسة \"الميزانية الصفرية\" التي تعمل بالكامل على البنية التحتية لـ GitHub، مما يضمن الاستدامة ومقاومة الرقابة.",
        "about.arch.hybrid": "<strong>المحرك الهجين:</strong> يجمع بين مرونة Python للذكاء مع <strong>Go Sidecar</strong> عالي الأداء لاختبار الشبكة بشكل متزامن هائل.",
        "about.arch.intel": "<strong>طبقة الذكاء:</strong> تقنية \"تنظيف البروكسي\" الخاصة بنا تقوم بإصلاح عناوين IP المحظورة تلقائيًا عن طريق تمريرها عبر نفق Cloudflare WARP.",
        "about.arch.agg": "<strong>المجمع:</strong> يجلب من أكثر من 668 مصدر كل 6 ساعات.",
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
        "analytics.charts.rejection": "منطق الرفض",
        "analytics.charts.threats": "توزيع التهديدات",
        "analytics.charts.asns": "أفضل مزودي الإنترنت",
        "analytics.charts.latency_by_country": "سرعة الاستجابة حسب البلد",
        "analytics.charts.latency_by_protocol": "سرعة الاستجابة حسب البروتوكول",

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

        // Set lang attribute for font selection
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
        const langButtons = document.querySelectorAll('.lang-menu button');
        langButtons.forEach(btn => {
            const btnLang = btn.getAttribute('onclick')?.match(/'([a-z]{2})'/)?.[1];
            if (btnLang === lang) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

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
        // Strict sanitizer: Whitelist-based approach
        const tmp = document.createElement('div');
        tmp.innerHTML = input;

        const walker = document.createTreeWalker(tmp, NodeFilter.SHOW_ELEMENT, null);
        const allowedTags = new Set(['STRONG', 'EM', 'B', 'I', 'U', 'BR', 'P', 'SPAN', 'DIV', 'A', 'UL', 'LI']);
        const allowedAttrs = new Set(['href', 'title', 'alt', 'class', 'id', 'target', 'role', 'aria-label', 'aria-hidden']);

        const toRemove = [];
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (!allowedTags.has(node.tagName)) {
                toRemove.push(node);
                continue;
            }
            // Remove disallowed attributes
            [...node.attributes].forEach(attr => {
                const name = attr.name.toLowerCase();
                const value = attr.value || '';
                if (!allowedAttrs.has(name) && !name.startsWith('data-')) {
                    node.removeAttribute(attr.name);
                    return;
                }
                // Check for javascript: protocol
                if ((name === 'href' || name === 'src') && value.trim().toLowerCase().startsWith('javascript:')) {
                    node.removeAttribute(attr.name);
                }
            });
        }
        toRemove.forEach(n => n.remove());
        return tmp.innerHTML;
    }

    formatNumber(num) {
        if (!num && num !== 0) return '';
        const lang = this.currentLang;

        // Convert to number if string
        const number = typeof num === 'string' ? parseFloat(num.replace(/,/g, '')) : num;

        if (lang === 'fa') {
            // Persian numerals
            const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
            return number.toLocaleString('fa-IR').split('').map(c => {
                if (c >= '0' && c <= '9') return persianDigits[c];
                return c === ',' ? '٬' : c;
            }).join('');
        } else if (lang === 'ar') {
            // Arabic-Indic numerals
            return number.toLocaleString('ar-EG');
        } else if (lang === 'ru') {
            // Russian uses space as thousands separator
            return number.toLocaleString('ru-RU');
        } else if (lang === 'zh') {
            // Chinese
            return number.toLocaleString('zh-CN');
        } else {
            // English and default
            return number.toLocaleString('en-US');
        }
    }
}

window.i18n = new I18n();
document.addEventListener('DOMContentLoaded', () => {
    window.i18n.setLanguage(window.i18n.currentLang);
});
