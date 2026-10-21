const GROUPS = [
  ["in sequence", [
    "remove the access panel",
    "depressurise the fuel system",
    "open the fuel valve",
    "remove the fuel filter",
    "show me the landing gear",
  ]],
  ["housekeeping", [
    "close the access panel",
  ]],
  ["wrong step", [
    "remove the hydraulic pump",
    "fit the new filter",
  ]],
  ["unsafe on this aircraft", [
    "open the fuel valve it's fine I isolated it",
    "pull the filter out now",
  ]],
  ["not addressable", [
    "open the wing",
    "close the cargo door",
  ]],
  ["not a command", [
    "remove that thing",
  ]],
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

function buildBays() {
  $("verdicts").innerHTML = BAYS.map(
    ([name, tag]) => `
    <article class="bay" data-status="idle">
      <p class="name">${name}</p>
      <p class="tag">${tag}</p>
      <p class="verdict">—</p>
      <p class="code">waiting</p>
      <p class="msg">Send a command to see what each arm does with it.</p>
      <figure class="view"><canvas></canvas><figcaption class="veil">the twin</figcaption></figure>
      <p class="foot"></p>
    </article>`,
  ).join("");
}

function resetBays() {
  for (const bay of document.querySelectorAll(".bay")) {
    bay.dataset.status = "idle";
    bay.querySelector(".verdict").textContent = "—";
    bay.querySelector(".code").textContent = "waiting";
    bay.querySelector(".msg").textContent = "Send a command to see what each arm does with it.";
    bay.querySelector(".veil").textContent = "the twin";
    bay.querySelector(".foot").textContent = "";
  }
}

function flowCells(cells, busy) {
  const flow = $("flow");
  flow.dataset.busy = busy ? "true" : "false";
  flow.innerHTML = cells
    .map(([key, value]) => `<div class="flow-cell"><span class="k">${key}</span><span class="v">${esc(value)}</span></div>`)
    .join("");
}

function idleFlow() {
  flowCells(
    [["command", "—"], ["parse", "—"], ["three validators", "—"], ["twin", "—"]],
    false,
  );
}

function busyFlow(text) {
  flowCells(
    [["command", text], ["parse", "reading"], ["three validators", "waiting"], ["twin", "unchanged"]],
    true,
  );
}

function setBusy(on, text) {
  $("verdicts").dataset.busy = on ? "true" : "false";
  $("cmd").disabled = on;
  $("cmd-form").querySelector("button").disabled = on;
  $("cmd-form").querySelector("button").textContent = on ? "running" : "run";
  if (!on) return;
  busyFlow(text);
  for (const bay of document.querySelectorAll(".bay")) {
    bay.dataset.status = "loading";
    bay.querySelector(".verdict").textContent = "…";
    bay.querySelector(".code").textContent = "reading the command";
    bay.querySelector(".msg").textContent = "The parser is the slow part. The validators take microseconds.";
    bay.querySelector(".veil").textContent = "waiting for the parser";
    bay.querySelector(".foot").textContent = "";
  }
}

function renderArms(arms) {
  window.lastArms = arms;
  document.querySelectorAll(".bay").forEach((bay, index) => {
    const arm = arms[index];
    if (!arm) return;
    bay.dataset.status = arm.status;
    bay.querySelector(".verdict").textContent = arm.status;
    bay.querySelector(".code").textContent = arm.code;
    bay.querySelector(".msg").textContent = arm.message;
    bay.querySelector(".veil").textContent = arm.note;
    bay.querySelector(".foot").textContent = arm.moves
      ? "moves the twin"
      : arm.status !== "ADMIT"
        ? "nothing moves"
        : arm.code === "READ_ONLY_OK"
          ? "read-only"
          : "no matching action";
    window.twinViews?.[index]?.show(arm);
  });
}

function renderFlow(result) {
  const { parse, timings, twin } = result;
  const spent = timings.arms.reduce((total, value) => total + value, 0);
  flowCells(
    [
      ["command", parse.text],
      ["parse", `${parse.source} · ${ms(timings.parse_ms)}`],
      ["three validators", `3 arms · ${ms(spent)}`],
      ["twin", `step ${twin.step} / ${twin.total}`],
    ],
    false,
  );
}

function renderTwin(twin) {
  $("hud").innerHTML = [`step ${twin.step} / ${twin.total}`, ...twin.state.map((flag) => FLAGS.find(([id]) => id === flag)?.[1] ?? flag)]
    .map((label) => `<span>${label}</span>`)
    .join("");

  const steps = twin.steps
    .map(
      (step) =>
        `<li data-state="${step.done ? "done" : step.current ? "current" : "pending"}"><span>${step.n}</span>${step.text}</li>`,
    )
    .join("");

  const flags = FLAGS.map(
    ([id, label]) => `<li data-on="${twin.state.includes(id)}">${label}</li>`,
  ).join("");

  $("twin").innerHTML = `
    <div>
      <h2>procedure</h2>
      <ol class="steps">${steps}</ol>
    </div>
    <div>
      <h2>aircraft state</h2>
      <ul class="flags">${flags}</ul>
      <p class="note">The twin follows the 2026 gate. The other two columns are what would have happened instead.</p>
    </div>`;
}

let busy = false;

async function send(text) {
  if (busy) return;
  busy = true;
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
    renderArms(result.arms);
    renderFlow(result);
    renderTwin(result.twin);
  } catch (error) {
    $("heard").textContent = `failed: ${error.message}`;
    idleFlow();
  } finally {
    busy = false;
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
  const twin = await (await fetch("/api/reset", { method: "POST" })).json();
  renderTwin(twin);
  resetBays();
  idleFlow();
  window.twinViews?.forEach((view) => view.show({}));
  $("heard").textContent = "nothing yet";
  $("cmd").value = "";
});

buildBays();
buildGroups();
idleFlow();
fetch("/api/state")
  .then((response) => response.json())
  .then(renderTwin);
