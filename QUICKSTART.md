# 🚀 ConfigStream Quick Start

Fast track guide to get ConfigStream running in 10 minutes.

---

## ⚡ 3-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/ConfigStream.git
cd ConfigStream

# 2. Install dependencies
pip install -e ".[dev]"

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
3. Branch: **gh-pages** / **(root)**
4. Click **Save**

Your site: `https://YOUR_USERNAME.github.io/ConfigStream/`

---

## ⚙️ Enable Automation

1. Go to **Settings** → **Actions** → **General**
2. Enable: **Read and write permissions** for workflows.
3. Go to the **Actions** tab in your repository.
4. Find the **ConfigStream Pipeline** workflow and enable it if it's disabled.
5. Manually run the workflow by clicking **Run workflow**.

The workflow will now run automatically every 6 hours.

---

## ✅ Verification

After the workflow has completed, you can verify that the site is live:

```bash
# Manually check the metadata URL
curl https://YOUR_USERNAME.github.io/ConfigStream/metadata.json
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
  --max-latency 500 \
  --leniency \
  --strict-security

# Update GeoIP databases
configstream update-databases

# Get help
configstream --help
```

---

## 📂 Directory Structure

```
ConfigStream/
├── frontend/               # All frontend assets
│   ├── index.html          # Home page
│   ├── proxies.html        # Proxy browser
│   └── assets/             # CSS, JS, images
├── output/                 # Generated configs
├── sources/                # Proxy sources
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
