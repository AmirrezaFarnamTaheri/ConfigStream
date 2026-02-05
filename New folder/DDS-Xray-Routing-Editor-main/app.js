const { createApp, ref, computed, watch, onMounted, onBeforeUnmount } = Vue;

createApp({
  setup() {
    // ---------- State ----------
    const rules = ref(loadRules());
    const dragIndex = ref(null);

    // Modal + Form
    const modalOpen = ref(false);
    const editIndex = ref(null);
    const form = ref(blankForm());

    // Sidebar wallets (Persian section allowed)
const wallets = ref([
  { name: "Toncoin (TON)", address: "UQCtWbj6w5pXICYfRmgg2NssMvral-khYWCKWV83vK-ShJcw" },
  { name: "TRON (TRX)", address: "TJWnK1fCcxwsemyYgYjebKnsBfofCFy3Pc" },
  { name: "Dogecoin (DOGE)", address: "DRXjceAoxBRzNsNgVR3GduPSau4xiv179y" },
  { name: "Litecoin (LTC)", address: "ltc1qz6f9aqmm9w86l7jva0ljvh35gxw80u8yplx6px" },
  { name: "Ethereum (ETH)", address: "0xFA231ce9128AC097F70F5efcfFb3d918645e1Ca9" },
]);


    const copyWalletAddress = (addr) => {
      navigator.clipboard?.writeText(addr)
        .then(() => alert("Address copied!"))
        .catch(() => {
          const ta = document.createElement("textarea");
          ta.value = addr;
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand("copy"); alert("Address copied!"); } catch {}
          document.body.removeChild(ta);
        });
    };

    // ---------- Persist ----------
    watch(rules, (val) => {
      localStorage.setItem("xrayRules", JSON.stringify(val));
    }, { deep: true });

    // ---------- Clean before export (REMOVE _id) ----------
    function cleanRules(arr) {
      return arr.map(({ _id, ...rest }) => ({ ...rest }));
    }

    // ---------- Computed Export Text ----------
    const exportText = computed(() => {
      const payload = { routing: { rules: cleanRules(rules.value) } };
      return JSON.stringify(payload, null, 2);
    });

    // ---------- Drag & Drop ----------
    const onDragStart = (i) => (dragIndex.value = i);
    const onDrop = (i) => {
      const from = dragIndex.value;
      const to = i;
      if (from === null || to === null || from === to) return;
      const arr = [...rules.value];
      const [moved] = arr.splice(from, 1);
      arr.splice(to, 0, moved);
      rules.value = arr;
      dragIndex.value = null;
    };

    // ---------- CRUD ----------
    function openCreate() {
      editIndex.value = null;
      form.value = blankForm();
      modalOpen.value = true;
    }
    function openEdit(i) {
      editIndex.value = i;
      form.value = toForm(rules.value[i]);
      modalOpen.value = true;
    }
    function closeModal() { modalOpen.value = false; }

    function saveRule() {
      const rule = fromForm(form.value);

      // Required outboundTag
      if (!rule.outboundTag) {
        alert("Field 'outboundTag' is required.");
        return;
      }

      // Validate domainMatcher: "", "hybrid", "linear"
      if (typeof rule.domainMatcher === "string") {
        const dm = rule.domainMatcher.trim();
        if (dm && !["hybrid", "linear"].includes(dm)) {
          alert("Domain Matcher must be empty, hybrid, or linear.");
          return;
        }
        if (!dm) delete rule.domainMatcher;
      }

      // Validate network: "", "tcp", "udp", "tcp,udp"
      if (typeof rule.network === "string") {
        const n = rule.network.trim();
        if (!["", "tcp", "udp", "tcp,udp"].includes(n)) {
          alert("Network must be empty, tcp, udp, or tcp,udp.");
          return;
        }
        if (n === "") delete rule.network;
      }

      if (editIndex.value === null) {
        rules.value = [...rules.value, withId(rule)];
      } else {
        const arr = [...rules.value];
        arr[editIndex.value] = { ...withKeepId(arr[editIndex.value], rule) };
        rules.value = arr;
      }
      modalOpen.value = false;
    }

    function duplicate(i) {
      rules.value = [
        ...rules.value.slice(0, i + 1),
        withId(JSON.parse(JSON.stringify(rules.value[i]))),
        ...rules.value.slice(i + 1),
      ];
    }

    function remove(i) {
      if (!confirm("Delete this rule?")) return;
      const arr = [...rules.value];
      arr.splice(i, 1);
      rules.value = arr;
    }

    // ---------- Import / Export / Copy ----------
    function downloadJSON() {
      const payload = { routing: { rules: cleanRules(rules.value) } };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "routing_rules.json";
      a.click();
      URL.revokeObjectURL(url);
    }

    function importJSON(ev) {
      const file = ev.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result);
          let imported = [];
          if (Array.isArray(data)) {
            imported = data;
          } else if (data?.routing?.rules && Array.isArray(data.routing.rules)) {
            imported = data.routing.rules;
          } else {
            throw new Error("Invalid JSON structure.");
          }
          rules.value = imported.map(withId); // ignore incoming _id
          alert("Import successful ✅");
        } catch (e) {
          alert("Error reading JSON: " + e.message);
        } finally {
          ev.target.value = "";
        }
      };
      reader.readAsText(file);
    }

    async function importFromClipboard() {
      try {
        if (!navigator.clipboard?.readText) {
          alert("Clipboard API not available in this browser.");
          return;
        }
        const text = await navigator.clipboard.readText();
        if (!text || !text.trim()) {
          alert("Clipboard is empty.");
          return;
        }
        const data = JSON.parse(text);
        let imported = [];
        if (Array.isArray(data)) {
          imported = data;
        } else if (data?.routing?.rules && Array.isArray(data.routing.rules)) {
          imported = data.routing.rules;
        } else {
          throw new Error("Invalid JSON structure.");
        }
        rules.value = imported.map(withId);
        alert("Import from clipboard successful ✅");
      } catch (err) {
        console.error(err);
        alert("Clipboard import failed: " + (err?.message || "Unknown error"));
      }
    }

    function copyJSON() {
      const text = JSON.stringify({ routing: { rules: cleanRules(rules.value) } }, null, 2);
      navigator.clipboard.writeText(text)
        .then(() => alert("JSON copied to clipboard ✅"))
        .catch(() => alert("Copy failed."));
    }

    function clearAll() {
      if (!confirm("Clear all rules?")) return;
      rules.value = [];
    }

    function loadExample() {
      const sample = [
        {
          type: "field",
          domain: ["geosite:category-ads-all", "geosite:meta"],
          outboundTag: "block",
        },
        { type: "field", ip: ["geoip:ir"], outboundTag: "direct" },
        { type: "field", protocol: ["bittorrent"], outboundTag: "block" },
        { type: "field", domain: ["geosite:google", "geosite:youtube"], outboundTag: "proxy" },
      ];
      rules.value = sample.map(withId);
    }

    // ---------- Actions menu (three dots) ----------
    const actionsOpen = ref(null);
    function toggleActions(i) {
      actionsOpen.value = actionsOpen.value === i ? null : i;
    }
    function closeActions() { actionsOpen.value = null; }
    function onDocClick() { actionsOpen.value = null; }
    function onKeydown(e) { if (e.key === "Escape") actionsOpen.value = null; }

    onMounted(() => {
      document.addEventListener("click", onDocClick);
      document.addEventListener("keydown", onKeydown);
    });
    onBeforeUnmount(() => {
      document.removeEventListener("click", onDocClick);
      document.removeEventListener("keydown", onKeydown);
    });

    // ---------- Helpers ----------
    function loadRules() {
      try {
        const raw = localStorage.getItem("xrayRules");
        const arr = raw ? JSON.parse(raw) : [];
        return Array.isArray(arr) ? arr.map(withId) : [];
      } catch {
        return [];
      }
    }
    function uid() { return Math.random().toString(36).slice(2) + Date.now().toString(36); }
    function withId(rule) { const { _id, ...rest } = rule || {}; return { _id: uid(), ...rest }; }
    function withKeepId(oldItem, nextRule) { return { _id: oldItem?._id || uid(), ...nextRule }; }

    // ------- FORM converters -------
    function blankForm() {
      return {
        // top fields
        domainMatcher: "",      // "", "hybrid", "linear"
        sourceText: "",
        sourcePort: "",
        networkText: "",        // "", "tcp", "udp", "tcp,udp"
        protocolText: "",

        // attributes block
        ipText: "",
        domainText: "",
        userText: "",
        port: "",
        inboundTagText: "",
        outboundTag: "",

        // dynamic custom attributes
        attributes: [],         // [{_id, key, value}]
      };
    }

    function toForm(rule) {
      const attrsArr = [];
      if (rule?.attrs && typeof rule.attrs === "object") {
        Object.entries(rule.attrs).forEach(([k, v]) => {
          attrsArr.push({ _id: uid(), key: k, value: String(v ?? "") });
        });
      }
      return {
        domainMatcher: rule.domainMatcher || "",
        sourceText: (rule.source || []).join(", "),
        sourcePort: rule.sourcePort || "",
        networkText: Array.isArray(rule.network) ? rule.network.join(",") : (rule.network || ""),
        protocolText: (rule.protocol || []).join(", "),

        ipText: (rule.ip || []).join(", "),
        domainText: (rule.domain || []).join(", "),
        userText: (rule.user || []).join(", "),
        port: rule.port || "",
        inboundTagText: (rule.inboundTag || []).join(", "),
        outboundTag: rule.outboundTag || "",

        attributes: attrsArr,
      };
    }

    function fromForm(f) {
      const toArr = (txt) => (txt || "").split(",").map(s => s.trim()).filter(Boolean);

      const r = {
        type: "field",
        outboundTag: f.outboundTag || "",
      };

      const candidates = {
        domainMatcher: (f.domainMatcher || "").trim(), // "", "hybrid", "linear"
        source: toArr(f.sourceText),
        sourcePort: (f.sourcePort || "").trim(),
        network: (f.networkText || "").trim(), // "", "tcp", "udp", "tcp,udp"
        protocol: toArr(f.protocolText),

        ip: toArr(f.ipText),
        domain: toArr(f.domainText),
        user: toArr(f.userText),
        port: (f.port || "").trim(),
        inboundTag: toArr(f.inboundTagText),
      };

      Object.entries(candidates).forEach(([k, v]) => {
        if (Array.isArray(v) && v.length) r[k] = v;
        else if (typeof v === "string" && v) r[k] = v;
      });

      // dynamic custom attributes -> attrs object
      if (Array.isArray(f.attributes) && f.attributes.length) {
        const obj = {};
        f.attributes.forEach(row => {
          const key = (row.key || "").trim();
          const val = (row.value || "").trim();
          if (key) obj[key] = val;
        });
        if (Object.keys(obj).length) r.attrs = obj;
      }
      return r;
    }

    // ---------- Dynamic attribute rows ----------
    function addAttrRow() { form.value.attributes.push({ _id: uid(), key: "", value: "" }); }
    function removeAttrRow(idx) { form.value.attributes.splice(idx, 1); }

    // ---------- Display helpers (ellipsis + full title) ----------
    const ELLIP_LIMIT = 10; // tune if needed
    function truncateText(s, limit = ELLIP_LIMIT) {
      const t = (s ?? "").toString();
      return t.length > limit ? t.slice(0, limit - 1) + "…" : t;
    }
    function fmtList(v) {
      if (!Array.isArray(v) || !v.length) return " ";
      return truncateText(v.join(", "));
    }
    function fmtStr(v) {
      const s = (v ?? "").toString().trim();
      return s ? truncateText(s) : " ";
    }
    function fmtAttrs(obj) {
      if (!obj || typeof obj !== "object") return " ";
      const s = Object.entries(obj).map(([k, v]) => `${k}:${v}`).join(", ");
      return s ? truncateText(s) : " ";
    }
    function fmtNetwork(n) {
      if (!n) return " ";
      const s = Array.isArray(n) ? n.join(",") : String(n);
      return truncateText(s);
    }

    // FULL text helpers for tooltip title
    function fullList(v) { return Array.isArray(v) && v.length ? v.join(", ") : ""; }
    function fullStr(v) { return (v ?? "").toString().trim(); }
    function fullAttrs(obj) {
      if (!obj || typeof obj !== "object") return "";
      return Object.entries(obj).map(([k, v]) => `${k}:${v}`).join(", ");
    }
    function fullNetwork(n) { return !n ? "" : (Array.isArray(n) ? n.join(",") : String(n)); }

    // ---------- Expose ----------
    return {
      // state
      rules, modalOpen, editIndex, form, wallets,

      // computed
      exportText,

      // actions
      openCreate, openEdit, closeModal, saveRule,
      duplicate, remove,
      onDragStart, onDrop,
      downloadJSON, importJSON, importFromClipboard, copyJSON,
      clearAll, loadExample,
      copyWalletAddress,

      // attrs
      addAttrRow, removeAttrRow,

      // actions menu
      actionsOpen, toggleActions, closeActions,

      // table helpers (ellipsis)
      fmtList, fmtStr, fmtAttrs, fmtNetwork,
      // full text for title
      fullList, fullStr, fullAttrs, fullNetwork,
    };
  }
}).mount("#app");
