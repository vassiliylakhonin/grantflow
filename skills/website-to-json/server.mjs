import http from "node:http";
import handler from "./handler.ts";

const port = Number(process.env.PORT || 8787);

const server = http.createServer(async (req, res) => {
  if (req.method !== "POST") {
    res.writeHead(405, { "content-type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "Method not allowed" }));
    return;
  }

  const url = `http://${req.headers.host || `localhost:${port}`}${req.url || "/"}`;
  const body = await readBody(req);

  try {
    const request = new Request(url, {
      method: "POST",
      headers: { "content-type": req.headers["content-type"] || "application/json" },
      body,
    });

    const response = await handler(request);
    await writeResponse(res, response);
  } catch (error) {
    res.writeHead(500, { "content-type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Unknown error",
      })
    );
  }
});

server.listen(port, () => {
  console.log(`website-to-json listening on http://127.0.0.1:${port}`);
});

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function writeResponse(res, response) {
  res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
  const text = await response.text();
  res.end(text);
}
