# 🚀 ConfigStream Quick Start

Fast track guide to get ConfigStream running in 10 minutes.

---

## ⚡ 3-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/ConfigStream.git
cd ConfigStream

# 2. Install dependencies
pip install -e .

# 3. Test locally
configstream merge --sources sources.mini.txt --output output/

# 4. Commit and push
git add .
git commit -m "Initial setup"
git push origin main
```

---

## 🌐 Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / **/ (root)**
4. Click **Save**

Your site: `https://YOUR_USERNAME.github.io/ConfigStream/`

---

## ⚙️ Enable Automation

1. Go to **Settings** → **Actions** → **General**
2. Enable: **Read and write permissions**
3. Enable: **Allow GitHub Actions to create PRs**
4. Go to **Actions** → **Merge VPN Subscriptions**
5. Click **Run workflow**

Workflow runs every 6 hours automatically.

---

## ✅ Verification

```bash
# Run verification script
./verify.sh YOUR_USERNAME

# Or manually check
curl https://YOUR_USERNAME.github.io/ConfigStream/output/metadata.json
```

---

## 🎯 Common Commands

```bash
# Update configs manually
configstream merge --sources sources.txt --output output/

# With filters
configstream merge \
  --sources sources.txt \
  --output output/ \
  --country US \
  --max-latency 500

# Update GeoIP databases
configstream update-databases

# Get help
configstream --help
```

---

## 📂 Directory Structure

```
ConfigStream/
├── index.html              # Home page
├── proxies.html            # Proxy browser
├── statistics.html         # Analytics
├── assets/
│   ├── css/framework.css   # Design system
│   └── js/utils.js         # Utilities
├── output/                 # Generated configs
├── sources.txt             # Proxy sources
└── src/configstream/       # Python package
```

---

## 🐛 Quick Troubleshooting

**Workflow fails?**
→ Check Settings → Actions → Permissions

**Pages not updating?**
→ Clear cache (Ctrl+Shift+R)

**No proxies?**
→ Check sources.txt has valid URLs

**Import errors?**
→ Run `pip install -e .` again

---

## 📚 Full Documentation

- **DEPLOYMENT.md** - Complete deployment guide
- **ARCHITECTURE.md** - System architecture
- **CONTRIBUTING.md** - Contribution guidelines
- **README.md** - Full project documentation

---

**You're ready to go! 🎉**

Your ConfigStream will now automatically update every 6 hours with fresh VPN configurations!
