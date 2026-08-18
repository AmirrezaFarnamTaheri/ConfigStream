# ConfigStream (配置流) — 高可用抗封锁代理聚合与验证平台

[![Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml)
[![CI](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml)
[![Pages Deploy](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml)

**[English](README.md) • [فارسی](README_FA.md) • [简体中文](README_ZH.md) • [Русский](README_RU.md)**

ConfigStream 是一个主权级、零运维预算的抗审查开源代理聚合系统。在恶劣的网络扰动和深度包检测（DPI）环境下，全自动进行多协议配置抓取、四层真实连通性测试、智能洗白加固与订阅分发。

---

## 🚀 自动订阅地址（每 15 分钟自动更新）

所有订阅内置 Hiddify/Streisand 元数据标头（`#profile-title`, `#subscription-userinfo`），支持标准 Base64 格式：

| 节点分类 / 配置文件 | 纯文本订阅 (URI 列表) | Base64 订阅链接 | 推荐客户端 |
| :--- | :--- | :--- | :--- |
| **全量节点 (All)** | [`configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs.txt) | [`configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs_base64.txt) | 通用全量 |
| **高可用已验证 (Verified)** | [`verified/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs.txt) | [`verified/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs_base64.txt) | Hiddify, v2rayN, Streisand |
| **高速低延迟 (Fast)** | [`fast/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs.txt) | [`fast/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs_base64.txt) | 游戏加速、语音通话 (< 800ms) |
| **强安全与前向保密 (Secure)** | [`secure/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs.txt) | [`secure/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs_base64.txt) | VLESS-Reality, Hysteria2, TUIC |
| **延迟前 100 强 (Top 100)** | [`top100.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/top100.txt) | — | 极速精选 |

### 核心客户端专属配置 (Clash / Sing-box)
- **Clash / Mihomo 配置文件:** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/clash.yaml`
- **Sing-box 1.13+ 核心配置:** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/singbox.json`

---

## ⚙️ 核心架构与多层验证体系

1. **L0/L1 结构去重与廉价过滤:**
   - 基于 `(Host, Port, Protocol, UUID)` 进行无网络静态去重。
   - 兼容 Xray 规范（支持 36 位标准 UUID、32 位紧凑十六进制以及小于 30 字节的自定义 ID 映射）。
   - 过滤私有局域网 IP 与危险端口，防御 SSRF。
2. **L2 异步 TCP 握手与并发 DNS 解构:**
   - 64 独立线程池异步解析 A/AAAA 记录，规避 round-robin IP 抖动。
   - 严格的 800 并发套接字上限，防止系统文件描述符耗尽 (`EMFILE`)。
3. **L3 本地内核真实数据包嗅探:**
   - 采用嵌入式 Go 原生内核进行真实的 HTTP 204 通道探活。
   - 多轮测试中位数算法（Median Filter），剔除偶发性抖动节点（Flaky Nodes）。
4. **智能洗白与链式拓扑 (Washer & Chaining):**
   - 针对受污染节点通过 Cloudflare WARP / Masque 进行链式前置封装，提高生存率。

---

## 📱 常用客户端导入指南

### 1. Clash Verge Rev / Mihomo Party / Clash Nyanpasu
1. 打开客户端，进入 **Profiles (配置)** 页面。
2. 将 `clash.yaml` 订阅链接粘贴到 URL 输入框中，点击 **Import (导入)**。

### 2. Sing-box / Hiddify
1. 复制 Base64 或 `singbox.json` 订阅链接。
2. 点击 **+ (添加配置)** $\rightarrow$ **从剪贴板添加**。

### 3. v2rayN / Shadowrocket / Streisand
1. 复制 Base64 订阅链接。
2. 在 **订阅设置** 中添加并点击 **更新订阅** 即可。

---

## 🛠️ 本地开发与测试

```bash
# 克隆仓库
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream

# 安装 Python 依赖
pip install -r requirements-dev.txt
pip install -e . --no-deps

# 运行验证管道
python -m configstream.cli merge --sources sources/batch_1.txt --output output/

# 执行单元测试
pytest tests/unit/
```

---

## 📜 开源协议
本项目采用 **AGPL-3.0-or-later** 开源许可证。
