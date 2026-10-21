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

const $ = (id) => document.getElementById(id);

function idle() {
  const blank = [
    ["LLM only", "executes the parse"],
    ["Manual check · 2023", "the manual, and only the manual"],
    ["Context gate · 2026", "manual + 3D hierarchy + state"],
  ];
  $("verdicts").innerHTML = blank
    .map(
      ([name, tag]) => `
      <article class="bay" data-status="idle">
        <p class="name">${name}</p>
        <p class="tag">${tag}</p>
        <p class="verdict">—</p>
        <p class="code">waiting</p>
        <p class="msg">Send a command to see what each arm does with it.</p>
        <p class="foot"></p>
      </article>`,
    )
    .join("");
}

function renderArms(arms) {
  $("verdicts").innerHTML = arms
    .map(
      (arm) => `
      <article class="bay" data-status="${arm.status}">
        <p class="name">${arm.name}</p>
        <p class="tag">${arm.tagline}</p>
        <p class="verdict">${arm.status}</p>
        <p class="code">${arm.code}</p>
        <p class="msg">${arm.message}</p>
        <p class="foot">${
          arm.moves
            ? "moves the twin"
            : arm.status !== "ADMIT"
              ? "nothing moves"
              : arm.code === "READ_ONLY_OK"
                ? "read-only"
                : "no matching action"
        }</p>
      </article>`,
    )
    .join("");
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

async function send(text) {
  $("heard").textContent = "reading…";
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
    renderTwin(result.twin);
  } catch (error) {
    $("heard").textContent = `failed: ${error.message}`;
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
  idle();
  $("heard").textContent = "nothing yet";
  $("cmd").value = "";
});

buildGroups();
idle();
fetch("/api/state")
  .then((response) => response.json())
  .then(renderTwin);
