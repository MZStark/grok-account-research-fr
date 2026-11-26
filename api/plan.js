// Vercel serverless function: POST /api/plan  { company }
// Calls the xAI (Grok) Responses API (web search + structured output) with plain fetch,
// so the project has zero npm dependencies.

const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const SCHEMA = JSON.parse(fs.readFileSync(path.join(ROOT, "schema.json"), "utf8"));
const SYSTEM_PROMPT = fs.readFileSync(path.join(ROOT, "prompts", "system.md"), "utf8");
const MODEL = process.env.GROK_MODEL || "grok-4.7";
const BASE_URL = (process.env.XAI_BASE_URL || "https://api.x.ai/v1").replace(/\/$/, "");

// Light abuse protection for a public demo: per-IP limit and a small cache.
const WINDOW_MS = 60 * 60 * 1000;
const MAX_PER_WINDOW = Number(process.env.RATE_LIMIT_PER_HOUR || 5);
const hits = new Map();
const cache = new Map();

function rateLimited(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  return recent.length > MAX_PER_WINDOW;
}

function extractText(data) {
  if (typeof data.output_text === "string" && data.output_text) return data.output_text;
  for (const item of data.output || []) {
    for (const part of item.content || []) {
      if (part.type === "output_text" && part.text) return part.text;
    }
  }
  throw new Error("No text in model response");
}

// Accepts raw JSON or JSON wrapped in a Markdown fence.
function parsePlan(text) {
  const trimmed = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "");
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start === -1 || end === -1) throw new Error("The model did not return a JSON strategy");
  const plan = JSON.parse(trimmed.slice(start, end + 1));
  for (const key of SCHEMA.required) {
    if (!(key in plan)) throw new Error(`The strategy is missing "${key}"`);
  }
  return plan;
}

async function callGrok(company, { structured }) {
  const user = `Company: ${company}\nSearch the web first, then build the account strategy.` +
    (structured ? "" : `\nReturn ONLY a JSON object that matches this JSON schema, with no text around it:\n${JSON.stringify(SCHEMA)}`);
  const body = {
    model: MODEL,
    tools: [{ type: "web_search" }],
    input: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: user },
    ],
  };
  if (structured) {
    body.text = { format: { type: "json_schema", name: "account_plan", schema: SCHEMA, strict: true } };
  }
  const response = await fetch(`${BASE_URL}/responses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.XAI_API_KEY}`,
    },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  return { response, data };
}

function apiError(response, data) {
  const raw = data && data.error;
  const message = (raw && (raw.message || raw)) || data.message || `Grok API error ${response.status}`;
  return typeof message === "string" ? message : JSON.stringify(message);
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Use POST" });
  }
  if (!process.env.XAI_API_KEY) {
    return res.status(503).json({ error: "Live generation is not configured on this deployment." });
  }

  // Fail closed: live generation always requires ACCESS_CODE to be set and matched.
  if (!process.env.ACCESS_CODE || req.headers["x-access-code"] !== process.env.ACCESS_CODE) {
    return res.status(401).json({ error: "Live generation needs an access code." });
  }

  const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
  const company = String(body.company || "").trim().slice(0, 80);
  if (company.length < 2) return res.status(400).json({ error: "Company name is required." });

  const key = company.toLowerCase();
  if (cache.has(key)) return res.status(200).json({ plan: cache.get(key), cached: true });

  const ip = (req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
  if (rateLimited(ip)) {
    return res.status(429).json({ error: "Demo limit reached. Try again in an hour." });
  }

  try {
    // Structured output first; if the model or endpoint rejects the schema format,
    // ask for the same JSON in plain text and validate it here.
    let { response, data } = await callGrok(company, { structured: true });
    if (response.status === 400 || response.status === 422) {
      ({ response, data } = await callGrok(company, { structured: false }));
    }
    if (!response.ok) return res.status(502).json({ error: apiError(response, data) });

    const plan = parsePlan(extractText(data));
    cache.set(key, plan);
    return res.status(200).json({ plan });
  } catch (err) {
    return res.status(500).json({ error: err.message || "Unexpected error" });
  }
};
