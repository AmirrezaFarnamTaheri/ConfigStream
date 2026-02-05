# DDS-Xray-Routing-Editor

![Version](https://img.shields.io/badge/version-1.0-blue.svg)

A sleek, web-based tool to **create, sort, and export Xray routing rules** in JSON—right from your browser. Built with **Vue 3** and **Tailwind CSS** , there’s no build step or backend.

---

## Features

- **Rule management UI**: Add, edit, duplicate, delete, and drag-drop re-order rules in a data-grid with grouped headers.
- **Import & Export**:
  - Export current rules as a JSON file (`⬇️ Export JSON`).
  - Import from a JSON file (`⬆️ Import JSON (File)`) or directly from your clipboard (`📋 Import from Clipboard`).
  - Copy current output to clipboard (`✅ Copy Output`).
- **Helpful presets**: Load an example ruleset with one click (`🧪 Example`) or clear everything (`🗑️ Clear All`).
- **Live output**: The right panel shows **Final Output (`routing.rules`)**—always in sync with your edits. You can select and copy it directly.
- **Sponsor box (RTL-friendly)**: A sidebar “Sponsored Content” card where you can place Persian content, links, and even an image.
- **Donation widget**: Copy-friendly wallet inputs with a one-click copy button.

---

## Quick Start

1. **Download** this repository (or clone it).
2. **Open** `index.html` in a modern browser — that’s it. No server is required because the app is fully client-side.

> The app loads Vue and Tailwind from CDNs referenced in `index.html`.

---

## Using the Editor

### Toolbar

- **➕ Add Rule** – Opens the modal to define a new rule.
- **⬇️ Export JSON** – Downloads the rules as a JSON file.
- **⬆️ Import JSON (File)** – Import rules from a local JSON file.
- **📋 Import from Clipboard** – Paste JSON from your clipboard.
- **✅ Copy Output** – Copies the formatted output.
- **🧪 Example** – Loads sample rules.
- **🗑️ Clear All** – Removes all rules.

### Table & Reordering

- Drag the **⋮⋮** handle to rearrange rules.
- The table groups fields by **Source**, **Network**, **Destination**, **Inbound**, and shows **Outbound**/**Balancer** plus **Actions** (Edit / Duplicate / Delete).

### Modal Form (Rule Fields)

The “Add/Edit Rule” dialog contains all supported fields:

- **domainMatcher**: `"" | "hybrid" | "linear"`
- **source** (IPs), **sourcePort**
- **network** (L4), **protocol**
- **attrs** (custom attributes—add/remove rows)
- **ip** (destination IPs), **domain** (destinations), **port**
- **inboundTag**, **user** (client email)
- **outboundTag** _(required)_, **balancerTag**  
  These correspond to the grid columns and are reflected in the final output.

### Output Panel

- The **Final Output (routing.rules)** area mirrors your rules.
- Click **Copy Output** to copy the text or **Export JSON** to download.

---

## JSON Import/Export Format

You can import **either** of the following:

- An **array** of rules: `[{ ... }, { ... }]`
- An **object** containing `routing.rules`: `{ routing: { rules: [...] } }`

> Tip: Use commas to separate multiple values in list-type inputs (e.g., `tcp,udp` or multiple IPs/domains).

---

## Donations

If you find this tool helpful, consider supporting us with a small donation! Your contribution helps us keep improving and fuels our coffee supply ☕❤️. Below are our wallet addresses:

| Cryptocurrency    | Wallet Address                                   |
| ----------------- | ------------------------------------------------ |
| TONcoin (TON)     | UQCtWbj6w5pXICYfRmgg2NssMvral-khYWCKWV83vK-ShJcw |
| DogeCoin (DOGE)   | DRXjceAoxBRzNsNgVR3GduPSau4xiv179y               |
| TRON (TRX-TRC20 ) | TJWnK1fCcxwsemyYgYjebKnsBfofCFy3Pc               |

## To copy an address,

## Tech Stack

- **Vue 3** for reactive UI.
- **Tailwind CSS** for styling.
- Vanilla HTML/CSS/JS—no build tooling required.

---

## Contributing

Issues and PRs are welcome—especially for UX polish, keyboard accessibility, shortcuts, and schema validations.

---

## License

GPL-3.0

---

## Credits

Developed by **Daily Digital Skills**. Sidebar links to the Telegram channel and YouTube are included in the header. {index=22}
