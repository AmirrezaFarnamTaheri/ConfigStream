#!/usr/bin/env bash
# =============================================
#   DNS Latency Test Script
#   Author: Musixal / Telegram @gozar_xray
# =============================================

# --------------------------
# ASCII Logo
# --------------------------
cat << "EOF"
  ____  _   _ ____    _____ _           _           
 |  _ \| \ | / ___|  |  ___(_)_ __   __| | ___ _ __ 
 | | | |  \| \___ \  | |_  | | '_ \ / _` |/ _ \ '__|
 | |_| | |\  |___) | |  _| | | | | | (_| |  __/ |   
 |____/|_| \_|____/  |_|   |_|_| |_|\__,_|\___|_|   
                                                    
      DNS Latency Checker
       Author: Musixal
     Telegram: @gozar_xray
EOF

echo

TEST_DOMAIN="google.com"
TIMEOUT=2
TRIES=1

# --------------------------
# Iranian DNS Servers with annotations
# --------------------------
declare -A DNS_SERVERS=(
# DCI Infrastructure - Tehran (LCT EMAM)
["217.218.127.104"]="DCI Tehran"
["217.218.127.105"]="DCI Tehran"
["217.218.127.106"]="DCI Tehran"
["217.218.155.105"]="DCI Tehran"
["217.218.155.106"]="DCI Tehran"

# DCI Infrastructure - Other cities
["217.219.0.104"]="DCI Esfahan"
["217.219.96.104"]="DCI Shiraz"
["217.219.192.104"]="DCI Hamedan"
["217.219.128.104"]="DCI Tabriz"
["217.219.224.104"]="DCI Ahvaz"
["217.219.64.104"]="DCI Mashhad"
["217.219.160.104"]="DCI Babol"

# Regional ISP DNS Servers
["217.219.157.2"]="Ardabil - Iran Telecom"
["217.219.72.194"]="West Azerbaijan - Iran Telecom"
["2.185.239.133"]="West Azerbaijan - Iran Telecom"
["2.185.239.134"]="West Azerbaijan - Iran Telecom"
["2.185.239.136"]="West Azerbaijan - Iran Telecom"
["2.185.239.137"]="West Azerbaijan - Iran Telecom"
["2.185.239.138"]="West Azerbaijan - Iran Telecom"
["2.185.239.139"]="West Azerbaijan - Iran Telecom"
["217.219.103.5"]="West Azerbaijan - Iran Telecom"
["78.38.23.216"]="West Azerbaijan - Iran Telecom"
["85.185.6.3"]="West Azerbaijan - Iran Telecom"

["217.219.132.88"]="East Azerbaijan - Iran Telecom"
["217.219.133.21"]="East Azerbaijan - Iran Telecom"
["80.191.209.105"]="East Azerbaijan - Iran Telecom"
["80.191.40.41"]="East Azerbaijan - Iran Telecom"
["93.115.231.100"]="East Azerbaijan - Iran Telecom"
["95.80.184.184"]="East Azerbaijan - Bozorg Net-e Aria"

["185.109.74.85"]="Bushehr - Pishgaman Toseeh Jonoub"
["185.164.73.148"]="Bushehr - Kavoshgar Novin"
["185.164.73.180"]="Bushehr - Kavoshgar Novin"

["217.219.250.200"]="Fars - Iran Telecom"
["217.219.250.201"]="Fars - Iran Telecom"
["217.219.250.202"]="Fars - Iran Telecom"
["185.64.179.89"]="Fars - Shiraz University"
["194.60.210.66"]="Fars - Farzanegan Pars"
["5.145.112.38"]="Fars - E-Money Net"
["5.145.112.39"]="Fars - E-Money Net"

["89.144.144.144"]="Gilan - ANDISHE SABZ"
["217.219.187.3"]="Gilan - ITC"

["5.200.200.200"]="Golestan - Iran Telecom"

["185.186.242.161"]="Isfahan - Gostaresh Ertebat Azin Kia"

["78.39.101.186"]="Kerman - Iran Telecom"
["185.229.29.214"]="Kerman - Atrin ICT"
["185.229.29.215"]="Kerman - Atrin ICT"

["185.23.131.73"]="Khorasan-e Razavi - Razavi ICT"
["37.156.29.27"]="Khorasan-e Razavi - Mobin Net"

["31.130.180.120"]="Lorestan - Roshangaran Ertebatat Rayaneh"

["185.113.59.253"]="Markazi - Rayankadeh Apadana"

["31.47.37.35"]="Mazandaran - Afranet"
["31.47.37.92"]="Mazandaran - Afranet"
["79.175.176.42"]="Mazandaran - Afranet"
["80.75.5.100"]="Mazandaran - Afranet"

["217.218.234.221"]="Qazvin - Iran Telecom"
["194.36.174.161"]="Semnan - Kardox"

["78.38.122.12"]="South Khorasan - Iran Telecom"
["85.185.85.6"]="South Khorasan - Iran Telecom"

["80.191.233.17"]="Tehran - Iran Telecom"
["80.191.233.33"]="Tehran - Iran Telecom"
["217.218.127.127"]="Tehran - Telecommunication Infra"
["217.218.155.155"]="Tehran - Telecommunication Infra"
["213.176.123.5"]="Iranian Research Org of Sci & Tech"
["185.187.84.15"]="Abramad Tech Infra"
["194.225.62.80"]="Tehran University of Medical Science"
["92.42.49.43"]="Iran Cell Service"

# Multiple ISP / Companies in Tehran
["185.128.139.128"]="Sefroyek Pardaz"
["185.128.139.139"]="Sefroyek Pardaz"
["185.51.200.10"]="Sefroyek Pardaz"
["185.51.200.2"]="Sefroyek Pardaz"
["185.51.200.50"]="Sefroyek Pardaz"
["185.51.200.6"]="Sefroyek Pardaz"

["185.161.112.33"]="Parvaz System IT"
["185.161.112.34"]="Parvaz System IT"
["185.161.112.38"]="Parvaz System IT"

["31.24.234.34"]="Tehran Municipality ICT"
["31.24.234.35"]="Tehran Municipality ICT"
["31.24.234.37"]="Tehran Municipality ICT"

["94.139.190.190"]="DATAK Internet Engineering"
["81.163.3.1"]="Rasana Pishtaz Co."
["81.163.3.2"]="Rasana Pishtaz Co."
["45.159.151.220"]="Kavoshgar Novin Karamad"

["82.99.202.164"]="Pars Online"
["91.98.124.109"]="Pars Online"
["91.98.64.222"]="Pars Online"
["82.99.242.155"]="Pars Online"
["91.99.101.12"]="Pars Online"
["91.99.96.158"]="Pars Online"

["185.55.225.25"]="Fanavari Serverpars"
["185.55.226.26"]="Fanavari Serverpars"

["185.53.143.3"]="Dade Pardazi Mobinhost"

["81.91.144.190"]="Farabord Dadeh Haye Iranian Co."
["37.19.90.62"]="Farabord Dadeh Haye Iranian Co."
["37.19.90.65"]="Farabord Dadeh Haye Iranian Co."

["91.245.229.1"]="Kish Cell Pars"
["91.245.229.2"]="Kish Cell Pars"

["94.183.42.232"]="Aria Shatel"
["188.158.158.158"]="Parvaresh Dadeha Co."
["188.159.159.159"]="Parvaresh Dadeha Co."

["185.20.163.2"]="Fanava Group"
["95.38.61.50"]="Fanava Group"

["2.188.166.22"]="Respina Networks"
["5.160.211.66"]="Respina Networks"

["178.22.122.100"]="Asiatech"
["185.98.113.113"]="Asiatech"
["185.98.114.114"]="Asiatech"
["185.98.115.135"]="Asiatech"
["37.156.145.18"]="Asiatech"
["37.156.145.21"]="Asiatech"
["37.156.145.229"]="Asiatech"
["77.238.109.196"]="Asiatech"

["185.81.41.81"]="Rooyekhat Media"
["5.202.100.100"]="Pishgaman Toseeh"
["5.202.100.101"]="Pishgaman Toseeh"
["5.202.100.102"]="Pishgaman Toseeh"
["5.202.100.99"]="Pishgaman Toseeh"
["5.202.122.222"]="Pishgaman Toseeh"

["46.224.1.42"]="Dadeh Gostar Asr Novin"
["46.224.1.43"]="Dadeh Gostar Asr Novin"

["31.24.200.1"]="Pars Fonoun Ofogh"
)

# --------------------------
# Optional: add global public DNS for comparison
# --------------------------
declare -A GLOBAL_DNS=(
["8.8.8.8"]="Google Public DNS"
["8.8.4.4"]="Google Public DNS"
["1.1.1.1"]="Cloudflare DNS"
["1.0.0.1"]="Cloudflare DNS"
["9.9.9.9"]="Quad9 DNS"
["149.112.112.112"]="Quad9 DNS"
["208.67.222.222"]="OpenDNS Cisco"
["208.67.220.220"]="OpenDNS Cisco"
["94.140.14.14"]="AdGuard DNS"
["94.140.15.15"]="AdGuard DNS"
["185.228.168.9"]="CleanBrowsing DNS"
["185.228.169.9"]="CleanBrowsing DNS"
["76.76.2.0"]="Control D"
["76.76.10.0"]="Control D"
)

# Merge global DNS into main DNS_SERVERS
for k in "${!GLOBAL_DNS[@]}"; do
    DNS_SERVERS[$k]="${GLOBAL_DNS[$k]}"
done

# Temporary file for healthy DNS
HEALTHY_FILE=$(mktemp)

printf "%-16s %-35s %-10s %-10s\n" "DNS_SERVER" "PROVIDER" "STATUS" "LATENCY(ms)"
printf "%-16s %-35s %-10s %-10s\n" "----------" "--------" "------" "-----------"

for DNS in "${!DNS_SERVERS[@]}"; do
    PROVIDER=${DNS_SERVERS[$DNS]}
    RESULT=$(dig @"$DNS" "$TEST_DOMAIN" +time=$TIMEOUT +tries=$TRIES +stats +nocmd +noquestion 2>/dev/null)

    if echo "$RESULT" | grep -q "Query time"; then
        LATENCY=$(echo "$RESULT" | awk '/Query time/ {print $4}')
        printf "%-16s %-35s %-10s %-10s\n" "$DNS" "$PROVIDER" "OK" "$LATENCY"
        echo -e "$LATENCY\t$DNS\t$PROVIDER" >> "$HEALTHY_FILE"
    else
        printf "%-16s %-35s %-10s %-10s\n" "$DNS" "$PROVIDER" "FAIL" "-"
    fi
done

# Print healthy DNS sorted by latency
if [ -s "$HEALTHY_FILE" ]; then
    echo
    echo "===== Healthy DNS servers sorted by latency (ms) ====="
    sort -n "$HEALTHY_FILE" | awk -F'\t' '{printf "%-16s %-35s %-10s\n",$2,$3,$1}'
else
    echo
    echo "No healthy DNS servers found."
fi

# Cleanup
rm -f "$HEALTHY_FILE"
