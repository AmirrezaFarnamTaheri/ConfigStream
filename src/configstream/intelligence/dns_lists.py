# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Curated lists of DNS servers, including regional infrastructure servers for evasion.
"""

# Iranian Infrastructure DNS (Intranet/National Network)
# These servers often respond from inside Iran even when international DNS is blocked.
IRAN_INFRASTRUCTURE_DNS = {
    # DCI Infrastructure - Tehran (LCT EMAM)
    "217.218.127.104": "DCI Tehran",
    "217.218.127.105": "DCI Tehran",
    "217.218.127.106": "DCI Tehran",
    "217.218.155.105": "DCI Tehran",
    "217.218.155.106": "DCI Tehran",
    "217.218.127.127": "Tehran - Telecommunication Infra",
    "217.218.155.155": "Tehran - Telecommunication Infra",

    # DCI Infrastructure - Other cities
    "217.219.0.104": "DCI Esfahan",
    "217.219.96.104": "DCI Shiraz",
    "217.219.192.104": "DCI Hamedan",
    "217.219.128.104": "DCI Tabriz",
    "217.219.224.104": "DCI Ahvaz",
    "217.219.64.104": "DCI Mashhad",
    "217.219.160.104": "DCI Babol",

    # Key ISP DNS
    "80.191.233.17": "Tehran - Iran Telecom",
    "217.219.72.194": "West Azerbaijan - Iran Telecom",
    "2.185.239.133": "West Azerbaijan - Iran Telecom",
    "217.219.132.88": "East Azerbaijan - Iran Telecom",
    "185.109.74.85": "Bushehr - Pishgaman",
    "217.219.250.200": "Fars - Iran Telecom",
    "89.144.144.144": "Gilan - Andishe Sabz",
    "5.200.200.200": "Golestan - Iran Telecom",
    "185.186.242.161": "Isfahan - Gostaresh",
    "78.39.101.186": "Kerman - Iran Telecom",
    "185.23.131.73": "Khorasan-e Razavi - Razavi ICT",
    "37.156.29.27": "Khorasan-e Razavi - Mobin Net",
    "31.47.37.35": "Mazandaran - Afranet",
    "80.75.5.100": "Mazandaran - Afranet",
    "217.218.234.221": "Qazvin - Iran Telecom",
    "78.38.122.12": "South Khorasan - Iran Telecom",
    "94.183.42.232": "Aria Shatel",
    "178.22.122.100": "Asiatech",
    "185.98.113.113": "Asiatech",
    "213.176.123.5": "Iranian Research Org",
    "194.225.62.80": "Tehran University",
    "92.42.49.43": "Iran Cell",
    "2.188.21.50": "Respina/Infra (Internal)",
    "2.188.21.46": "Respina/Infra (Internal)",
    "2.188.21.130": "Respina/Infra (Internal)",
    "217.218.52.5": "Infra (Internal)",
}

# Special Cloudflare IPs reported to work better
CLOUDFLARE_OPTIMIZED_IPS = [
    "108.162.192.0",
    "162.159.38.0",
    "162.159.44.0",
    "172.64.32.0",
    "34.153.65.94",
    "34.153.64.86",
    "34.153.65.92",
    "208.103.161.11",
    "208.103.161.3",
    "208.103.161.9",
    "208.103.161.45",
    "208.103.161.62",
    "208.103.161.172",
    "208.103.161.103",
    "208.103.161.138",
    "208.103.161.121",
    "208.103.161.6",
]

# Zeus DNS (Anti-Censorship)
ZEUS_DNS = ["37.32.5.60", "37.32.5.61"]
