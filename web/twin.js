// The twin, drawn from primitives: the NASA hull is one solid mesh, so the parts the
// procedure touches are schematic service points pinned to it. Same camera in all three
// bays on purpose — the eye is meant to compare, not to explore.

import * as THREE from "./vendor/three.module.js";

const AIR = 0x46505e;
const TRIM = 0x8f9aa8;
const AMBER = 0xd3a34a;
const REFUSE = 0xcf6350;
const VIEW = 0x7d97b8;

const flat = (color, extra = {}) =>
  new THREE.MeshStandardMaterial({ color, roughness: 0.66, metalness: 0.18, flatShading: true, ...extra });

function build() {
  const group = new THREE.Group();
  const air = flat(AIR);
  const trim = flat(TRIM);

  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 6.3, 4, 16), air);
  body.rotation.x = Math.PI / 2;
  body.position.z = 0.1;
  group.add(body);

  for (const side of [-1, 1]) {
    const half = new THREE.Mesh(new THREE.BoxGeometry(4.7, 0.1, 1.6), air);
    half.position.set(side * 2.3, -0.02, 0.45);
    half.rotation.z = side * 0.06;
    group.add(half);
  }

  const tailplane = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.08, 0.85), air);
  tailplane.position.set(0, 0.16, 3.2);
  group.add(tailplane);

  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.3, 0.85), air);
  fin.position.set(0, 0.78, 3.1);
  group.add(fin);

  const nacelle = (x) => {
    const mesh = new THREE.Mesh(new THREE.CapsuleGeometry(0.27, 1.3, 4, 10), air);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.set(x, -0.36, -0.55);
    return mesh;
  };
  group.add(nacelle(-2.35), nacelle(2.35));

  const nodes = new Map();
  const add = (id, object) => {
    nodes.set(id, object);
    group.add(object);
    return object;
  };

  // --- left engine: the cowl is the nacelle, the pump hangs under it ---
  const cowl = add("engine_cowl", nacelle(-2.35));

  const pump = new THREE.Group();
  pump.position.set(-2.35, -0.74, 0.15);
  const pumpBody = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.3, 0.44), trim);
  const port = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.2, 8), trim);
  port.rotation.z = Math.PI / 2;
  port.position.set(0.18, 0.05, 0);
  pump.add(pumpBody, port);
  add("hydraulic_pump", pump);

  // --- wing root: hatch, valve, filter, and the fuel volume around them ---
  const hinge = new THREE.Group();
  hinge.position.set(-0.55, 0.02, 0.35);
  const plate = new THREE.Mesh(
    new THREE.BoxGeometry(1.5, 0.03, 1.15),
    flat(AMBER, { transparent: true, opacity: 0.12, metalness: 0 }),
  );
  plate.position.x = -0.75;
  const frame = new THREE.LineSegments(
    new THREE.EdgesGeometry(plate.geometry),
    new THREE.LineBasicMaterial({ color: AMBER, transparent: true, opacity: 0.8 }),
  );
  frame.position.copy(plate.position);
  hinge.add(plate, frame);
  add("access_panel", hinge);

  const valve = new THREE.Group();
  valve.position.set(-1.15, -0.14, 0.56);
  const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.038, 6, 16), trim);
  wheel.rotation.x = Math.PI / 2;
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.18, 8), trim);
  stem.position.y = -0.1;
  const spinner = new THREE.Group();
  for (const angle of [0, Math.PI / 2]) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.015, 0.03), trim);
    spoke.rotation.y = angle;
    spinner.add(spoke);
  }
  spinner.position.y = 0.02;
  valve.add(wheel, stem, spinner);
  add("fuel_valve", valve);

  const filter = new THREE.Group();
  filter.position.set(-1.62, -0.22, 0.2);
  const can = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.44, 12), trim);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.05, 12), trim);
  cap.position.y = 0.24;
  filter.add(can, cap);
  add("fuel_filter", filter);

  const volume = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(1.75, 0.8, 1.5)),
    new THREE.LineBasicMaterial({ color: VIEW, transparent: true, opacity: 0.28 }),
  );
  volume.position.set(-1.35, -0.28, 0.35);
  add("fuel_system", volume);

  // --- nose gear ---
  const gear = new THREE.Group();
  gear.position.set(0, -0.18, -2.45);
  const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.78, 8), trim);
  leg.position.y = -0.31;
  const tyre = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.055, 6, 14), air);
  tyre.rotation.y = Math.PI / 2;
  tyre.position.y = -0.72;
  gear.add(leg, tyre);
  add("landing_gear", gear);

  // --- glass, pylons, and a contact patch, so the aircraft sits on something ---
  const glass = flat(0x11151b, { metalness: 0.1, roughness: 0.35 });
  const cockpit = new THREE.Mesh(new THREE.BoxGeometry(0.66, 0.2, 0.5), glass);
  cockpit.position.set(0, 0.42, -2.62);
  group.add(cockpit);

  for (let row = 0; row < 6; row++) {
    for (const side of [-1, 1]) {
      const pane = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.11, 0.17), glass);
      pane.position.set(side * 0.52, 0.2, -1.55 + row * 0.52);
      group.add(pane);
    }
  }

  for (const side of [-1, 1]) {
    const pylon = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.26, 0.7), air);
    pylon.position.set(side * 2.1, -0.2, -0.5);
    group.add(pylon);
  }

  const patch = new THREE.Mesh(
    new THREE.CircleGeometry(4.6, 40),
    new THREE.MeshBasicMaterial({ color: 0x0b0d10, transparent: true, opacity: 0.5, depthWrite: false }),
  );
  patch.rotation.x = -Math.PI / 2;
  patch.position.y = -1.35;
  group.add(patch);

  // Each service point owns its materials, so highlighting one cannot tint its neighbours.
  for (const object of nodes.values()) {
    object.traverse((child) => {
      if (!child.material) return;
      child.material = child.material.clone();
      child.material.userData.base = child.material.color.getHex();
    });
  }

  return { group, nodes, hinge, spinner, filter, pump, volume };
}

const tint = (object, hex, strength = 0.9) => {
  object.traverse((child) => {
    const material = child.material;
    if (!material) return;
    if (material.isLineBasicMaterial) {
      material.color.setHex(hex === null ? material.userData.base : hex);
    } else if ("emissive" in material) {
      material.emissive.setHex(hex === null ? 0x000000 : hex);
      material.emissiveIntensity = hex === null ? 0 : strength;
    }
  });
};

const clear = (object) => tint(object, null);

class View {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
    this.home = { at: new THREE.Vector3(-9.9, 3.6, -9.5), look: new THREE.Vector3(-0.2, 0.0, 0.4) };
    this.camera.position.copy(this.home.at);
    this.look = this.home.look.clone();
    this.camera.lookAt(this.look);
    this.at = this.home.at.clone();
    this.lookAt3 = this.home.look.clone();
    this.boxes = new Map();

    this.scene.add(new THREE.HemisphereLight(0xa6b6cc, 0x101318, 1.7));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(-6, 9, -5);
    const rim = new THREE.DirectionalLight(0x6f8098, 0.9);
    rim.position.set(6, -2, 7);
    this.scene.add(key, rim);

    const built = build();
    this.twin = built;
    this.scene.add(built.group);
    this.flags = new Set();

    this.resize();
    new ResizeObserver(() => this.resize()).observe(canvas);
  }

  resize() {
    const { clientWidth: w, clientHeight: h } = this.canvas;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  show({ after = [], focus = null, blocker = null, status = "idle" } = {}) {
    this.flags = new Set(after);
    for (const node_ of this.twin.nodes.values()) clear(node_);
    if (blocker && this.twin.nodes.has(blocker)) tint(this.twin.nodes.get(blocker), REFUSE, 1);
    if (focus && this.twin.nodes.has(focus)) {
      const tone = blocker ? REFUSE : status === "ADMIT" ? AMBER : REFUSE;
      if (blocker === focus) tint(this.twin.nodes.get(focus), tone, 0.7);
      else tint(this.twin.nodes.get(focus), tone, status === "ADMIT" ? 0.55 : 0.35);
    }
    this.target = {
      panel: this.flags.has("access_panel_open") ? -0.95 : 0,
      valve: this.flags.has("fuel_valve_open") ? 2.4 : 0,
      filter: this.flags.has("fuel_filter_removed") ? -0.5 : 0,
      pump: this.flags.has("hydraulic_pump_removed") ? -0.62 : 0,
    };
    this.frame(blocker || focus);
  }

  /** Aim the camera at a node, or back at the whole aircraft when nothing is addressed. */
  frame(id) {
    if (!id || !this.twin.nodes.has(id)) {
      this.at = this.home.at.clone();
      this.lookAt3 = this.home.look.clone();
      return;
    }
    if (!this.boxes.has(id)) {
      const box = new THREE.Box3().setFromObject(this.twin.nodes.get(id));
      const centre = box.getCenter(new THREE.Vector3());
      const radius = box.getSize(new THREE.Vector3()).length() / 2;
      this.boxes.set(id, { centre, radius });
    }
    const { centre, radius } = this.boxes.get(id);
    const aspect = this.camera.aspect;
    const distance =
      Math.min(Math.max(radius * 5.2, 8.8), 15) *
      (aspect < 1.2 ? 1.25 : aspect > 1.55 ? 0.86 : 1);
    const bearing = new THREE.Vector3(-0.8, 0.46, -0.62).normalize();
    // Keep the aircraft in frame around the part: the eye goes to the part, not to a slab.
    const anchor = new THREE.Vector3(0, 0, 0.2).lerp(centre, 0.6);
    this.at = anchor.clone().addScaledVector(bearing, distance);
    this.lookAt3 = anchor.clone();
  }

  step(dt) {
    if (!this.target) return;
    const ease = 1 - Math.exp(-9 * dt);
    const { hinge, spinner, filter, pump } = this.twin;
    hinge.rotation.z += (this.target.panel - hinge.rotation.z) * ease;
    spinner.rotation.y += (this.target.valve - spinner.rotation.y) * ease;
    filter.position.y += (-0.22 + this.target.filter - filter.position.y) * ease;
    pump.position.x += (-2.35 + this.target.pump - pump.position.x) * ease;

    const glide = 1 - Math.exp(-4.2 * dt);
    this.camera.position.lerp(this.at, glide);
    this.look.lerp(this.lookAt3, glide);
    this.camera.lookAt(this.look);
    this.renderer.render(this.scene, this.camera);
  }
}

const views = [...document.querySelectorAll(".view canvas")].map((canvas) => new View(canvas));
window.twinViews = views;

for (const view of views) view.show({});
if (window.lastArms) views.forEach((view, i) => window.lastArms[i] && view.show(window.lastArms[i]));

let previous = performance.now();
const frame = (now) => {
  const dt = Math.min((now - previous) / 1000, 0.05);
  previous = now;
  for (const view of views) view.step(dt);
  requestAnimationFrame(frame);
};
requestAnimationFrame(frame);
