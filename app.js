(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const state = { plan: null, ready: new Set(), stepTimer: null };
  const LEVELS = ["Exploring", "Piloting", "Scaling", "AI-native"];
  const RANK = { high: 0, medium: 1, low: 2 };

  const slugify = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(String(u || "")) ? String(u) : null);
  const srcLink = (u) => {
    const url = safeUrl(u);
    return url ? `<a class="src" href="${esc(url)}" target="_blank" rel="noopener">↗ source</a>` : "";
  };
  const FACT = `<span class="tag fact">Sourced fact</span>`;
  const HYPO = `<span class="tag hypo">Hypothesis</span>`;

  /* ---------- examples ---------- */
  let examples = [];
  async function loadExamples() {
    try { examples = await (await fetch("data/examples.json")).json(); } catch { examples = []; }
    await Promise.all(examples.map(async (acc) => {
      try {
        const r = await fetch(`data/plans/${slugify(acc.name)}.json`, { method: "HEAD" });
        if (r.ok) state.ready.add(slugify(acc.name));
      } catch { /* not generated yet */ }
    }));
    $("#examples-grid").innerHTML = examples.map((acc) => {
      const ready = state.ready.has(slugify(acc.name));
      return `<button type="button" class="account" data-company="${esc(acc.name)}">
        <strong>${esc(acc.name)}</strong>
        <span class="sector">${esc(acc.sector)}</span>
        <span class="status ${ready ? "" : "todo"}">${ready ? "● Strategy ready" : "○ Build live"}</span>
      </button>`;
    }).join("");
  }

  /* ---------- loading / errors ---------- */
  function startLoading() {
    $("#error").hidden = true;
    $("#plan").hidden = true;
    $("#loading").hidden = false;
    const steps = [...document.querySelectorAll(".steps li")];
    let i = 0;
    const tick = () => {
      steps.forEach((li, idx) => { li.classList.toggle("done", idx < i); li.classList.toggle("active", idx === i); });
      if (i < steps.length - 1) i += 1;
    };
    tick();
    state.stepTimer = setInterval(tick, 7000);
    $("#plan-form button").disabled = true;
    $("#loading").scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function stopLoading() {
    clearInterval(state.stepTimer);
    $("#loading").hidden = true;
    $("#plan-form button").disabled = false;
  }

  /* ---------- data ---------- */
  async function getPlan(company) {
    const slug = slugify(company);
    if (state.ready.has(slug) || slug.startsWith("demo-")) {
      const r = await fetch(`data/plans/${slug}.json`);
      if (r.ok) return r.json();
    }
    const code = ($("#access-code") && $("#access-code").value.trim()) || "";
    const r = await fetch("api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Access-Code": code },
      body: JSON.stringify({ company }),
    });
    const data = await r.json().catch(() => ({}));
    if (r.status === 503 || r.status === 404 || r.status === 405) {
      throw new Error("Live generation is not enabled on this deployment. Open the demo strategy or a ready example.");
    }
    if (r.status === 401) throw new Error("Live generation needs an access code. Ask the author for one, or open a ready example.");
    if (!r.ok) throw new Error(`Could not build the strategy: ${data.error || r.status}`);
    return data.plan;
  }

  async function run(company) {
    startLoading();
    try {
      state.plan = await getPlan(company);
      renderPlan(state.plan);
    } catch (err) {
      $("#error").textContent = err.message;
      $("#error").hidden = false;
    } finally {
      stopLoading();
    }
  }

  /* ---------- rendering ---------- */
  function matrix(useCases) {
    const levels = ["high", "medium", "low"];
    const cell = (v, f) => useCases
      .filter((u) => u.value === v && u.feasibility === f)
      .map((u) => `<span class="chip" title="${esc(u.business_value)}">${esc(u.name)}</span>`).join("");
    const rows = levels.map((v) => `
      <div class="m-label">${v}</div>
      ${["low", "medium", "high"].map((f) => `<div class="m-cell ${v === "high" && f === "high" ? "sweet" : ""}">${cell(v, f)}</div>`).join("")}`).join("");
    return `<div class="matrix">
      <div class="m-axis-y">Business value</div>
      <div class="m-grid">${rows}
        <div></div><div class="m-label x">low</div><div class="m-label x">medium</div><div class="m-label x">high</div>
      </div>
      <div class="m-axis-x">Feasibility</div>
    </div>`;
  }

  function renderPlan(p) {
    const m = p.ai_maturity || { level: "", summary: "", evidence: [] };
    const levelIdx = Math.max(0, LEVELS.indexOf(m.level));
    const useCases = [...(p.use_cases || [])].sort((a, b) => (RANK[a.value] + RANK[a.feasibility]) - (RANK[b.value] + RANK[b.feasibility]));
    const byWindow = (w) => (p.action_plan || []).filter((a) => a.window === w).map((a) => `<li>${esc(a.action)}</li>`).join("");

    $("#plan").innerHTML = `
      <div class="plan-head">
        <div>
          <p class="eyebrow">Account strategy</p>
          <h2>${esc(p.company)}</h2>
          <p class="one-liner">${esc(p.one_liner)}</p>
        </div>
        <div class="plan-actions">
          <button type="button" class="btn-ghost" id="copy-md">Copy as Markdown</button>
          <button type="button" class="btn-ghost" id="print-pdf">Export to PDF</button>
          <button type="button" class="btn-ghost" id="close-plan">Close</button>
        </div>
      </div>
      <div class="legend">${FACT}${HYPO}</div>
      <div class="plan-grid">
        <section class="card span-7">
          <h3>Snapshot ${FACT}</h3>
          <dl class="kv">${(p.snapshot || []).map((s) => `<dt>${esc(s.label)}</dt><dd>${esc(s.value)}${srcLink(s.source)}</dd>`).join("")}</dl>
        </section>
        <section class="card span-5">
          <h3>AI maturity ${FACT}</h3>
          <div class="meter">${LEVELS.map((l, i) => `<span class="${i <= levelIdx ? "on" : ""}">${esc(l)}</span>`).join("")}</div>
          <p class="summary">${esc(m.summary)}</p>
          <ul class="list">${(m.evidence || []).map((e) => `<li>${esc(e.fact)}${srcLink(e.source)}</li>`).join("")}</ul>
        </section>
        <section class="card span-12">
          <h3>Strategic priorities ${FACT}</h3>
          <div class="priorities">${(p.strategic_priorities || []).map((s, i) => `
            <article class="prio"><span class="prio-n">P${i + 1}</span><h4>${esc(s.priority)}</h4><p>${esc(s.evidence)}${srcLink(s.source)}</p></article>`).join("")}</div>
        </section>
        <section class="card span-12">
          <h3>Use-case portfolio ${HYPO}</h3>
          <div class="uc-layout">
            ${matrix(useCases)}
            <div class="opps">${useCases.map((u) => `
              <article class="opp">
                <div class="opp-top"><span class="tag product">${esc(u.product)}</span><span class="tag team">${esc(u.team)}</span></div>
                <h4>${esc(u.name)}</h4>
                <p>${esc(u.business_value)}</p>
                <p class="signal">Value ${esc(u.value)} · Feasibility ${esc(u.feasibility)} · Serves: ${esc(u.linked_priority)}${srcLink(u.source)}</p>
              </article>`).join("")}</div>
          </div>
        </section>
        <section class="card span-6">
          <h3>Stakeholder map</h3>
          <div class="people">${(p.stakeholders || []).map((s) => `
            <div class="person"><div class="person-top"><strong>${esc(s.role)}</strong><span class="tag infl">${esc(s.influence)}</span></div><span>${esc(s.cares_about)}</span><em>→ ${esc(s.angle)}</em></div>`).join("")}</div>
        </section>
        <section class="card span-6">
          <h3>Adoption and impact ${HYPO}</h3>
          <p class="sub">Governance</p>
          <ul class="list">${((p.adoption_and_impact || {}).governance || []).map((g) => `<li>${esc(g)}</li>`).join("")}</ul>
          <p class="sub">Metrics leadership will track</p>
          <div class="metrics">${((p.adoption_and_impact || {}).metrics || []).map((x) => `<div class="metric"><strong>${esc(x.metric)}</strong><span>${esc(x.why)}</span></div>`).join("")}</div>
        </section>
        <section class="card span-12">
          <h3>12-month expansion plan ${HYPO}</h3>
          <div class="timeline">${(p.expansion_plan || []).map((g) => `
            <div class="phase"><span class="when">${esc(g.horizon)}</span><p>${esc(g.motion)}</p><p class="trigger">Next phase when: ${esc(g.trigger)}</p></div>`).join("")}</div>
        </section>
        <section class="card span-6">
          <h3>Risks ${HYPO}</h3>
          <div class="risks">${(p.risks || []).map((r) => `
            <div class="risk"><div><span class="label">Risk</span>${esc(r.risk)}</div><div><span class="label">Mitigation</span>${esc(r.mitigation)}</div></div>`).join("")}</div>
        </section>
        <section class="card span-6">
          <h3>Questions to validate</h3>
          <ol class="list numbered">${(p.open_questions || []).map((q) => `<li>${esc(q)}</li>`).join("")}</ol>
        </section>
        <section class="card span-12">
          <h3>30 / 60 / 90-day plan</h3>
          <div class="timeline">${["30 days", "60 days", "90 days"].map((w) => `
            <div class="phase"><span class="when">${w}</span><ul class="list">${byWindow(w)}</ul></div>`).join("")}</div>
        </section>
        <section class="card span-12">
          <h3>First message ${HYPO}</h3>
          <p class="sub">Opens on: ${esc((p.outreach || {}).opening_signal)}</p>
          <div class="outreach">
            <div class="msg"><div class="msg-top"><span class="tag product">Français</span><button type="button" class="btn-ghost small" id="copy-fr">Copy</button></div><p>${esc((p.outreach || {}).message_fr)}</p></div>
            <div class="msg"><div class="msg-top"><span class="tag team">English translation</span></div><p>${esc((p.outreach || {}).message_en)}</p></div>
          </div>
        </section>
        <section class="card span-12">
          <h3>Sources</h3>
          <ol class="sources">${(p.sources || []).map((s) => {
            const url = safeUrl(s.url);
            return `<li>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(s.title || url)}</a>` : esc(s.title)}</li>`;
          }).join("")}</ol>
        </section>
      </div>`;

    $("#plan").hidden = false;
    $("#copy-md").addEventListener("click", copyMarkdown);
    $("#copy-fr").addEventListener("click", async (e) => {
      try { await navigator.clipboard.writeText((state.plan.outreach || {}).message_fr || ""); e.target.textContent = "Copied"; setTimeout(() => { e.target.textContent = "Copy"; }, 1600); } catch { /* clipboard blocked */ }
    });
    $("#print-pdf").addEventListener("click", () => { try { window.print(); } catch { /* blocked */ } });
    $("#close-plan").addEventListener("click", () => { state.plan = null; $("#plan").hidden = true; });
    $("#plan").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function toMarkdown(p) {
    const L = [`# Account strategy: ${p.company}`, "", p.one_liner, "", "## Snapshot"];
    (p.snapshot || []).forEach((s) => L.push(`- **${s.label}**: ${s.value} ([source](${s.source}))`));
    const m = p.ai_maturity || {};
    L.push("", `## AI maturity: ${m.level}`, m.summary || "");
    (m.evidence || []).forEach((e) => L.push(`- ${e.fact} ([source](${e.source}))`));
    L.push("", "## Strategic priorities");
    (p.strategic_priorities || []).forEach((s, i) => L.push(`${i + 1}. **${s.priority}**: ${s.evidence} ([source](${s.source}))`));
    L.push("", "## Use-case portfolio (hypotheses)", "| Use case | Product | Team | Value | Feasibility | Serves |", "|---|---|---|---|---|---|");
    (p.use_cases || []).forEach((u) => L.push(`| ${u.name} | ${u.product} | ${u.team} | ${u.value} | ${u.feasibility} | ${u.linked_priority} |`));
    L.push("", "## Stakeholder map");
    (p.stakeholders || []).forEach((s) => L.push(`- **${s.role}** (${s.influence}): ${s.cares_about} → ${s.angle}`));
    const a = p.adoption_and_impact || {};
    L.push("", "## Adoption and impact", "**Governance**");
    (a.governance || []).forEach((g) => L.push(`- ${g}`));
    L.push("", "**Metrics**");
    (a.metrics || []).forEach((x) => L.push(`- ${x.metric}: ${x.why}`));
    L.push("", "## 12-month expansion plan");
    (p.expansion_plan || []).forEach((g) => L.push(`- **${g.horizon}**: ${g.motion} (next phase when: ${g.trigger})`));
    L.push("", "## Risks");
    (p.risks || []).forEach((r) => L.push(`- ${r.risk} → ${r.mitigation}`));
    L.push("", "## Questions to validate");
    (p.open_questions || []).forEach((q, i) => L.push(`${i + 1}. ${q}`));
    L.push("", "## 30 / 60 / 90-day plan");
    (p.action_plan || []).forEach((x) => L.push(`- **${x.window}**: ${x.action}`));
    const o = p.outreach || {};
    L.push("", "## First message", `Opens on: ${o.opening_signal || ""}`, "", "**Français**", "", o.message_fr || "", "", "**English**", "", o.message_en || "");
    L.push("", "## Sources");
    (p.sources || []).forEach((s) => L.push(`- [${s.title}](${s.url})`));
    return L.join("\n");
  }

  async function copyMarkdown() {
    const btn = $("#copy-md");
    try {
      await navigator.clipboard.writeText(toMarkdown(state.plan));
      btn.textContent = "Copied";
      setTimeout(() => { btn.textContent = "Copy as Markdown"; }, 1600);
    } catch { /* clipboard blocked */ }
  }

  /* ---------- events ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    loadExamples();
    $("#plan-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const company = $("#company").value.trim();
      if (company.length >= 2) run(company);
    });
    $("#demo-btn").addEventListener("click", () => run("demo-nova-rail"));
    $("#examples-grid").addEventListener("click", (e) => {
      const card = e.target.closest(".account");
      if (card) run(card.dataset.company);
    });
  });
})();
