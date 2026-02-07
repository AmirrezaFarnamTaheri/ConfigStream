export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/^\/+/, "");
    const parts = path.split("/");
    if (parts.length < 4) {
      return new Response("Usage: /owner/repo/branch/path/to/file.ext", { status: 400 });
    }
    const [owner, repo, branch, ...filePathParts] = parts;
    const filePath = filePathParts.join("/");
    const rawUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${filePath}`;
    const resp = await fetch(rawUrl);
    return new Response(resp.body, {
      status: resp.status,
      headers: resp.headers,
    });
  }
};
