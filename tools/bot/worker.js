// Cloudflare Worker for ConfigStream Bot
// Deploy this script to a Cloudflare Worker to serve proxy requests statelessly.

const GITHUB_PAGES_URL = "https://farnam.github.io/ConfigStream"; // Replace with actual repo URL
const METADATA_URL = `${GITHUB_PAGES_URL}/files/metadata.json`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Simple router
    if (path === "/bot" || path === "/webhook") {
      if (request.method === "POST") {
        return handleTelegramWebhook(request, env);
      }
      return new Response("Method not allowed", { status: 405 });
    }

    return new Response("ConfigStream Bot Worker is Running", { status: 200 });
  },
};

async function handleTelegramWebhook(request, env) {
  try {
    const update = await request.json();
    if (!update.message) {
      return new Response("No message", { status: 200 });
    }

    const chatId = update.message.chat.id;
    const text = update.message.text || "";

    let responseText = "Hello! I am the ConfigStream Bot.\n";
    responseText += "Commands:\n";
    responseText += "/stats - Get current proxy stats\n";
    responseText += "/get <country> - Get a proxy for a specific country (e.g., /get US)\n";
    responseText += "/sub - Get subscription links";

    if (text.startsWith("/stats")) {
        const stats = await fetchStats();
        responseText = `📊 *Pipeline Stats*\n`;
        responseText += `Total Fetched: ${stats.total_fetched}\n`;
        responseText += `Active Proxies: ${stats.active_proxies}\n`;
        responseText += `Last Updated: ${stats.last_updated}`;
    } else if (text.startsWith("/get")) {
        const parts = text.split(" ");
        if (parts.length < 2) {
            responseText = "⚠️ Please specify a country code. Example: `/get US`";
        } else {
            const country = parts[1].toUpperCase();
            const proxy = await fetchProxyForCountry(country);
            if (proxy) {
                responseText = `🌍 *Proxy for ${country}*\n\`\`\`\n${proxy}\n\`\`\``;
            } else {
                responseText = `❌ No proxies found for ${country}.`;
            }
        }
    } else if (text.startsWith("/sub")) {
        responseText = "🔗 *Subscription Links*\n";
        responseText += `Clash: ${GITHUB_PAGES_URL}/files/clash.yaml\n`;
        responseText += `SingBox: ${GITHUB_PAGES_URL}/files/singbox.json\n`;
    }

    // Send response back to Telegram
    await sendTelegramMessage(env.TELEGRAM_BOT_TOKEN, chatId, responseText);

    return new Response("OK", { status: 200 });
  } catch (e) {
    return new Response("Error processing update", { status: 500 });
  }
}

async function fetchStats() {
    try {
        const resp = await fetch(METADATA_URL);
        if (!resp.ok) return { total_fetched: "?", active_proxies: "?", last_updated: "?" };
        return await resp.json();
    } catch (e) {
        return { total_fetched: "Err", active_proxies: "Err", last_updated: "Err" };
    }
}

async function fetchProxyForCountry(country) {
    // In a real scenario, we would fetch the huge proxies.json or a specific country file.
    // Assuming /files/by_country/CC.json exists as per server.py logic
    const url = `${GITHUB_PAGES_URL}/files/by_country/${country.toLowerCase()}.json`;
    try {
        const resp = await fetch(url);
        if (!resp.ok) return null;
        const proxies = await resp.json();
        if (proxies.length > 0) {
            // Return a random one
            const p = proxies[Math.floor(Math.random() * proxies.length)];
            return p.link || JSON.stringify(p); // Assuming 'link' field exists or returning JSON
        }
        return null;
    } catch (e) {
        return null;
    }
}

async function sendTelegramMessage(token, chatId, text) {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            chat_id: chatId,
            text: text,
            parse_mode: "Markdown"
        })
    });
}
