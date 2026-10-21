const GROUPS = [
  ["in sequence", [
    "remove the access panel",
    "depressurise the fuel system",
    "open the fuel valve",
    "remove the fuel filter",
    "fit the new filter",
    "show me the landing gear",
  ]],
  ["housekeeping", ["close the access panel"]],
  ["wrong step", ["remove the hydraulic pump"]],
  ["unsafe on this aircraft", [
    "open the fuel valve it's fine I isolated it",
    "pull the filter out now",
  ]],
  ["not addressable", ["open the wing", "close the cargo door"]],
  ["not a command", ["remove that thing"]],
];

const FLAGS = [
  ["access_panel_open", "panel 12A open"],
  ["fuel_depressurised", "fuel depressurised"],
  ["fuel_valve_open", "valve open"],
  ["fuel_filter_removed", "filter out"],
  ["fuel_filter_fitted", "filter fitted"],
  ["hydraulic_pump_removed", "pump out"],
];

const BAYS = [
  ["LLM only", "executes the parse"],
  ["Manual check · 2023", "the manual, and only the manual"],
  ["Context gate · 2026", "manual + 3D hierarchy + state"],
];

const $ = (id) => document.getElementById(id);
const esc = (text) =>
  String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ms = (value) => (value < 10 ? `${value.toFixed(2)} ms` : `${Math.round(value)} ms`);

let busy = false;
const HISTORY = [];

function buildBays() {
  $("verdicts").innerHTML = BAYS.map(
    ([name, tag], index) => `
    <article class="bay" data-status="idle" data-arm="${index}">
      <p class="name">${name}</p>
      <p class="tag">${tag}</p>
      <p class="verdict">—</p>
      <p class="code">waiting</p>
      <p class="msg">Send a command to see what this arm does with it.</p>
      <div class="view"><canvas></canvas><p class="veil"></p></div>
      <ul class="trace"></ul>
      <p class="foot"></p>
    </article>`,
  ).join("");
}

function resetBays() {
  for (const bay of document.querySelectorAll(".bay")) {
    bay.dataset.status = "idle";
    bay.querySelector(".verdict").textContent = "—";
    bay.querySelector(".code").textContent = "waiting";
    bay.querySelector(".msg").textContent = "Send a command to see what this arm does with it.";
    bay.querySelector(".foot").textContent = "";
    bay.querySelector(".veil").textContent = "";
    bay.querySelector(".trace").innerHTML = "";
  }
}

function renderArms(arms) {
  clearInterval(ticker);
  window.lastArms = arms;
  arms.forEach((arm, index) => {
    const bay = document.querySelector(`.bay[data-arm="${index}"]`);
    if (!bay) return;
    bay.dataset.status = arm.status === "ADMIT" && arm.code === "READ_ONLY_OK" ? "READ_ONLY_OK" : arm.status;
    bay.querySelector(".verdict").textContent = arm.status;
    bay.querySelector(".code").textContent = arm.code;
    bay.querySelector(".msg").textContent = arm.message;
    bay.querySelector(".veil").textContent = arm.note;
    bay.querySelector(".foot").innerHTML = `${
      arm.moves
        ? "moves the twin"
        : arm.status !== "ADMIT"
          ? "nothing moves"
          : arm.code === "READ_ONLY_OK"
            ? "read-only"
            : "no matching action"
    }<span class="took">${ms(arm.ms)}</span>`;
    bay.querySelector(".trace").innerHTML = (arm.trace || [])
      .map(
        (row) =>
          `<li data-state="${row.state || "pass"}"><b>${esc(row.stage)}</b><span>${esc(row.value)}</span></li>`,
      )
      .join("");
    window.twinViews?.[index]?.show(arm);
  });
}

const PENDING = [
  "Queued. This arm will execute whatever the parse returns.",
  "Queued. This arm waits for the manual, and only the manual.",
  "Queued. This arm waits for the manual, the hierarchy and the state.",
];

let ticker = null;
let started = 0;

function armTicker() {
  clearInterval(ticker);
  ticker = setInterval(() => {
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    for (const bay of document.querySelectorAll('.bay[data-status="loading"]')) {
      const code = bay.querySelector(".code");
      if (code) code.textContent = `${seconds} s`;
    }
  }, 80);
}

function setBusy(on, text) {
  busy = on;
  $("cmd").disabled = on;
  $("cmd-form").querySelector("button").textContent = on ? "running" : "run";
  $("verdicts").dataset.busy = on ? "true" : "false";
  if (!on) return;
  started = performance.now();
  $("heard").textContent = `reading “${text}”`;
  busyFlow(text);
  document.querySelectorAll(".bay").forEach((bay, index) => {
    bay.dataset.status = "loading";
    bay.querySelector(".verdict").textContent = "…";
    bay.querySelector(".code").textContent = "0.0 s";
    bay.querySelector(".msg").textContent = PENDING[index];
    bay.querySelector(".veil").textContent = "reading the command";
    bay.querySelector(".trace").innerHTML = "";
    bay.querySelector(".foot").textContent = "";
  });
  armTicker();
}

function flowCells(cells, busy) {
  return cells
    .map(
      (cell, index) => `
      <div class="flow-cell" data-state="${busy ? "busy" : cell.state || "pass"}" style="--i:${index}">
        <p class="k">${esc(cell.stage)}</p>
        <p class="v">${esc(cell.value)}</p>
      </div>`,
    )
    .join("");
}

function busyFlow(text) {
  $("flow").dataset.busy = "true";
  $("flow").innerHTML = flowCells(
    [
      { stage: "command", value: `“${text}”` },
      { stage: "parse", value: "model → vocabulary" },
      { stage: "validators", value: "three, in parallel" },
      { stage: "twin", value: "state" },
    ],
    true,
  );
}

function renderFlow(result) {
  $("flow").dataset.busy = "false";
  const { parse, timings } = result;
  $("flow").innerHTML = flowCells([
    { stage: "command", value: `“${parse.text}”` },
    { stage: "parse", value: `${parse.source} · ${ms(timings.parse_ms)}` },
    { stage: "validators", value: `3 arms · ${ms(timings.arms.reduce((a, b) => a + b, 0))}` },
    { stage: "twin", value: result.twin.step > result.twin.total ? "done" : `step ${result.twin.step}` },
  ]);
}

function renderTwin(twin) {
  $("hud").innerHTML = [`step ${twin.step} / ${twin.total}`, ...twin.state.map((flag) => FLAGS.find(([id]) => id === flag)?.[1] ?? flag)]
    .map((label) => `<span>${label}</span>`)
    .join("");

  const steps = twin.steps
    .map((step) => {
      const state = step.done ? "done" : step.current ? "current" : "pending";
      const label = step.command ? "run this step" : "";
      return `<li data-state="${state}"><span>${step.n}</span><button type="button" data-command="${esc(step.command || "")}" title="${label}">${esc(step.text)}</button></li>`;
    })
    .join("");

  const flagsList = FLAGS.map(
    ([id, label]) => `<li data-on="${twin.state.includes(id)}">${label}</li>`,
  ).join("");

  const recent = HISTORY.map(
    (row) => `<li><span class="t">${(row.total / 1000).toFixed(2)} s</span><span class="q">${esc(row.text)}</span></li>`,
  ).join("");

  $("twin").innerHTML = `
    <div>
      <h2>procedure <span class="hint">click a step to run it</span></h2>
      <ol class="steps">${steps}</ol>
    </div>
    <div>
      <h2>aircraft state</h2>
      <ul class="flags">${flagsList}</ul>
      <section class="recent">
        <h2>recent commands</h2>
        <ol class="history" id="history">${recent}</ol>
      </section>
      <p class="note">The twin follows the 2026 gate. The other two columns are what would have happened instead.</p>
    </div>`;

  for (const button of document.querySelectorAll(".steps button")) {
    button.addEventListener("click", () => {
      if (button.dataset.command) send(button.dataset.command);
    });
  }
}

function logCommand(text, total) {
  HISTORY.unshift({ text, total });
  HISTORY.splice(8);
}

async function send(text) {
  if (busy) return;
  setBusy(true, text);
  try {
    const response = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error(`server ${response.status}`);
    const result = await response.json();
    const { verb, part, source } = result.parse;
    $("heard").textContent = `${source} → ${verb}${part ? " · " + part : " · no part"}`;
    renderFlow(result);
    renderArms(result.arms);
    logCommand(result.parse.text, result.timings.total_ms);
    renderTwin(result.twin);
  } catch (error) {
    clearInterval(ticker);
    $("heard").textContent = `failed: ${error.message}`;
    $("flow").dataset.busy = "false";
    resetBays();
  } finally {
    setBusy(false);
  }
}

function buildGroups() {
  $("groups").innerHTML = GROUPS.map(
    ([title, commands]) => `
      <section class="group">
        <h2>${title}</h2>
        ${commands.map((text) => `<button class="chip" type="button">${text}</button>`).join("")}
      </section>`,
  ).join("");

  for (const chip of document.querySelectorAll(".chip")) {
    chip.addEventListener("click", () => {
      $("cmd").value = chip.textContent.trim();
      send(chip.textContent.trim());
    });
  }
}

$("cmd-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const text = $("cmd").value.trim();
  if (text) send(text);
});

$("reset").addEventListener("click", async () => {
  if (busy) return;
  const twin = await (await fetch("/api/reset", { method: "POST" })).json();
  HISTORY.length = 0;
  renderTwin(twin);
  resetBays();
  idleFlow();
  $("heard").textContent = "nothing yet";
  $("cmd").value = "";
  window.lastArms = null;
  window.twinViews?.forEach((view) => view.show({}));
});

function idleFlow() {
  $("flow").dataset.busy = "false";
  $("flow").innerHTML = flowCells([
    { stage: "command", value: "say or type one" },
    { stage: "parse", value: "model → symbols" },
    { stage: "validators", value: "three, in parallel" },
    { stage: "twin", value: "state" },
  ]);
}

buildBays();
buildGroups();
idleFlow();
fetch("/api/state")
  .then((response) => response.json())
  .then(renderTwin);
