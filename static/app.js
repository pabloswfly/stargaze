(() => {
  "use strict";

  const canvas = document.getElementById("sky");
  const ctx2d = canvas.getContext("2d");
  const tooltip = document.getElementById("tooltip");
  const statusEl = document.getElementById("status");
  const compassEl = document.getElementById("compass");

  const latInput = document.getElementById("lat");
  const lonInput = document.getElementById("lon");
  const useLocationBtn = document.getElementById("use-location");
  const applyLocationBtn = document.getElementById("apply-location");
  const timeSlider = document.getElementById("time-slider");
  const timeLabel = document.getElementById("time-label");
  const nowButton = document.getElementById("now-button");
  const magLimitInput = document.getElementById("mag-limit");
  const magLimitLabel = document.getElementById("mag-limit-label");
  const toggleConstellations = document.getElementById("toggle-constellations");
  const toggleLabels = document.getElementById("toggle-labels");
  const panelToggle = document.getElementById("panel-toggle");
  const panel = document.getElementById("panel");

  const DEG2RAD = Math.PI / 180;
  const RAD2DEG = 180 / Math.PI;

  const state = {
    lat: 51.4769,
    lon: 0.0,
    centerAlt: 45,
    centerAz: 180,
    fovDeg: 90,
    skyData: null,
    magLimit: 6.0,
    showConstellations: true,
    showLabels: true,
    timeOffsetMinutes: 0,
    dragging: false,
    lastPointer: null,
    pinchStartDist: null,
    pinchStartFov: null,
    pixelsPerUnit: 1,
    hoverTarget: null,
    pinnedTarget: null,
  };

  // ---- Projection: stereographic, centered on (state.centerAlt, state.centerAz) ----

  function altAzToVector(altDeg, azDeg) {
    const alt = altDeg * DEG2RAD;
    const az = azDeg * DEG2RAD;
    const cosAlt = Math.cos(alt);
    return [cosAlt * Math.sin(az), cosAlt * Math.cos(az), Math.sin(alt)];
  }

  function project(altDeg, azDeg) {
    const [x, y, z] = altAzToVector(altDeg, azDeg);

    // Rotate so the view center points along +Y' (forward).
    const azC = state.centerAz * DEG2RAD;
    const altC = state.centerAlt * DEG2RAD;

    // Rotate around vertical (z) axis by -azC.
    const x1 = x * Math.cos(azC) - y * Math.sin(azC);
    const y1 = x * Math.sin(azC) + y * Math.cos(azC);
    const z1 = z;

    // Tilt so altC maps to the forward (+Y) axis: rotate around the x-axis by -altC.
    const y2 = y1 * Math.cos(altC) + z1 * Math.sin(altC);
    const z2 = -y1 * Math.sin(altC) + z1 * Math.cos(altC);
    const x2 = x1;

    // (x2, z2) span the tangent plane; y2 = cos(angular distance from center).
    const behind = y2 < -0.05;
    const k = 2 / (1 + y2);
    return {
      x: k * x2,
      y: -k * z2,
      behind,
      cosDist: y2,
    };
  }

  function updateScale() {
    const minDim = Math.min(canvas.width, canvas.height);
    const halfFovRad = (state.fovDeg / 2) * DEG2RAD;
    const edgeRadius = 2 * Math.tan(halfFovRad / 2);
    state.pixelsPerUnit = (minDim / 2) / edgeRadius;
  }

  function toScreen(unitX, unitY) {
    return {
      sx: canvas.width / 2 + unitX * state.pixelsPerUnit,
      sy: canvas.height / 2 + unitY * state.pixelsPerUnit,
    };
  }

  // ---- Rendering ----

  function magnitudeToRadius(mag) {
    const clamped = Math.max(-1.5, Math.min(mag, state.magLimit));
    return Math.max(0.4, 3.0 - clamped * 0.5);
  }

  function skyTintColor() {
    if (!state.skyData) return "#05060a";
    const sunAlt = state.skyData.sun.alt;
    if (sunAlt > 0) return "#3a6ea8";
    if (sunAlt > -6) return "#1c3352"; // civil twilight
    if (sunAlt > -12) return "#101c33"; // nautical twilight
    if (sunAlt > -18) return "#0a1120"; // astronomical twilight
    return "#05060a"; // full night
  }

  // ---- Horizon line + cardinal directions ----

  const CARDINAL_POINTS = [
    ["N", 0],
    ["E", 90],
    ["S", 180],
    ["W", 270],
  ];

  function drawHorizon() {
    const steps = 180;
    ctx2d.strokeStyle = "rgba(120, 210, 150, 0.55)";
    ctx2d.lineWidth = 1.5 * window.devicePixelRatio;
    ctx2d.setLineDash([6 * window.devicePixelRatio, 5 * window.devicePixelRatio]);
    ctx2d.beginPath();
    let started = false;
    for (let i = 0; i <= steps; i++) {
      const az = (360 * i) / steps;
      const p = project(0, az);
      if (p.behind) {
        started = false;
        continue;
      }
      const { sx, sy } = toScreen(p.x, p.y);
      if (!started) {
        ctx2d.moveTo(sx, sy);
        started = true;
      } else {
        ctx2d.lineTo(sx, sy);
      }
    }
    ctx2d.stroke();
    ctx2d.setLineDash([]);

    ctx2d.font = `bold ${13 * window.devicePixelRatio}px sans-serif`;
    ctx2d.fillStyle = "rgba(150, 230, 175, 0.95)";
    ctx2d.textAlign = "center";
    for (const [label, az] of CARDINAL_POINTS) {
      const p = project(0, az);
      if (p.behind) continue;
      const { sx, sy } = toScreen(p.x, p.y);
      if (sx < -20 || sx > canvas.width + 20 || sy < -20 || sy > canvas.height + 20) continue;
      ctx2d.fillText(label, sx, sy + 18 * window.devicePixelRatio);
    }
    ctx2d.textAlign = "left";
  }

  function azToCompass(azDeg) {
    const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    const idx = Math.round((((azDeg % 360) + 360) % 360) / 45) % 8;
    return dirs[idx];
  }

  function updateCompass() {
    const altLabel = state.centerAlt >= 0 ? "above horizon" : "below horizon";
    compassEl.textContent =
      `Facing ${azToCompass(state.centerAz)} (${Math.round(state.centerAz)}°) · ` +
      `${Math.abs(Math.round(state.centerAlt))}° ${altLabel}`;
  }

  function resize() {
    canvas.width = window.innerWidth * window.devicePixelRatio;
    canvas.height = window.innerHeight * window.devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    updateScale();
    draw();
  }

  function draw() {
    updateScale();
    ctx2d.fillStyle = skyTintColor();
    ctx2d.fillRect(0, 0, canvas.width, canvas.height);

    drawHorizon();
    updateCompass();

    if (!state.skyData) return;

    const drawnLabels = [];

    if (state.showConstellations) {
      ctx2d.strokeStyle = "rgba(140, 170, 220, 0.35)";
      ctx2d.lineWidth = 1;
      for (const con of state.skyData.constellations) {
        for (const line of con.lines) {
          ctx2d.beginPath();
          let started = false;
          for (const pt of line) {
            const p = project(pt.alt, pt.az);
            if (p.behind) {
              started = false;
              continue;
            }
            const { sx, sy } = toScreen(p.x, p.y);
            if (!started) {
              ctx2d.moveTo(sx, sy);
              started = true;
            } else {
              ctx2d.lineTo(sx, sy);
            }
          }
          ctx2d.stroke();
        }
      }
    }

    // Stars
    for (const star of state.skyData.stars) {
      const p = project(star.alt, star.az);
      if (p.behind) continue;
      const { sx, sy } = toScreen(p.x, p.y);
      if (sx < -20 || sx > canvas.width + 20 || sy < -20 || sy > canvas.height + 20) continue;
      const r = magnitudeToRadius(star.mag);
      ctx2d.beginPath();
      ctx2d.fillStyle = "#f5f7ff";
      ctx2d.arc(sx, sy, r * window.devicePixelRatio, 0, 2 * Math.PI);
      ctx2d.fill();
      star._screen = { sx, sy, r: Math.max(r * window.devicePixelRatio, 6) };
      if (state.showLabels && star.name && state.fovDeg < 120) {
        drawnLabels.push({ sx, sy, text: star.name, size: 11 });
      }
    }

    // Planets
    for (const planet of state.skyData.planets) {
      const p = project(planet.alt, planet.az);
      if (p.behind) continue;
      const { sx, sy } = toScreen(p.x, p.y);
      const r = Math.max(2.5, 5.5 - planet.mag * 0.4) * window.devicePixelRatio;
      ctx2d.beginPath();
      ctx2d.fillStyle = "#ffd27f";
      ctx2d.arc(sx, sy, r, 0, 2 * Math.PI);
      ctx2d.fill();
      planet._screen = { sx, sy, r: Math.max(r, 8) };
      if (state.showLabels) drawnLabels.push({ sx, sy, text: planet.name, size: 12 });
    }

    // Sun
    {
      const p = project(state.skyData.sun.alt, state.skyData.sun.az);
      if (!p.behind) {
        const { sx, sy } = toScreen(p.x, p.y);
        ctx2d.beginPath();
        ctx2d.fillStyle = "#ffe066";
        ctx2d.arc(sx, sy, 10 * window.devicePixelRatio, 0, 2 * Math.PI);
        ctx2d.fill();
        state.skyData.sun._screen = { sx, sy, r: 14 * window.devicePixelRatio };
        if (state.showLabels) drawnLabels.push({ sx, sy, text: "Sun", size: 12 });
      }
    }

    // Moon (phase-shaded)
    {
      const moon = state.skyData.moon;
      const p = project(moon.alt, moon.az);
      if (!p.behind) {
        const { sx, sy } = toScreen(p.x, p.y);
        const r = 9 * window.devicePixelRatio;
        ctx2d.beginPath();
        ctx2d.fillStyle = "#3a3d4a";
        ctx2d.arc(sx, sy, r, 0, 2 * Math.PI);
        ctx2d.fill();
        ctx2d.save();
        ctx2d.beginPath();
        ctx2d.arc(sx, sy, r, 0, 2 * Math.PI);
        ctx2d.clip();
        const litFrac = moon.illuminated_fraction;
        const waxing = ((moon.phase_angle % 360) + 360) % 360 < 180;
        ctx2d.fillStyle = "#f2f2ea";
        const ellipseWidth = Math.abs(1 - 2 * litFrac) * r;
        ctx2d.beginPath();
        if (litFrac >= 0.5) {
          ctx2d.arc(sx, sy, r, -Math.PI / 2, Math.PI / 2, waxing);
          ctx2d.ellipse(sx, sy, ellipseWidth, r, 0, Math.PI / 2, -Math.PI / 2, !waxing);
        } else {
          ctx2d.arc(sx, sy, r, Math.PI / 2, (3 * Math.PI) / 2, waxing);
          ctx2d.ellipse(sx, sy, ellipseWidth, r, 0, -Math.PI / 2, Math.PI / 2, !waxing);
        }
        ctx2d.fill();
        ctx2d.restore();
        moon._screen = { sx, sy, r: Math.max(r, 12) };
        if (state.showLabels) drawnLabels.push({ sx, sy, text: "Moon", size: 12 });
      }
    }

    // Labels (simple overlap-avoidance: skip if too close to an already-drawn label)
    ctx2d.fillStyle = "rgba(230, 235, 245, 0.85)";
    ctx2d.font = `${11 * window.devicePixelRatio}px sans-serif`;
    const placed = [];
    for (const lbl of drawnLabels) {
      const tooClose = placed.some((p) => Math.hypot(p.sx - lbl.sx, p.sy - lbl.sy) < 14 * window.devicePixelRatio);
      if (tooClose) continue;
      placed.push(lbl);
      ctx2d.fillText(lbl.text, lbl.sx + 8 * window.devicePixelRatio, lbl.sy + 3 * window.devicePixelRatio);
    }
  }

  // ---- Networking ----

  function currentTimeValue() {
    const t = new Date(Date.now() + state.timeOffsetMinutes * 60000);
    return t;
  }

  function updateTimeLabel() {
    const t = currentTimeValue();
    timeLabel.textContent = t.toLocaleString([], { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" });
  }

  let fetchController = null;
  async function fetchSky() {
    const t = currentTimeValue();
    const params = new URLSearchParams({
      lat: String(state.lat),
      lon: String(state.lon),
      time: t.toISOString(),
      mag_limit: String(state.magLimit),
    });
    statusEl.textContent = "Loading sky...";
    if (fetchController) fetchController.abort();
    fetchController = new AbortController();
    try {
      const resp = await fetch(`/api/sky?${params.toString()}`, { signal: fetchController.signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      state.skyData = await resp.json();
      statusEl.textContent = `${state.lat.toFixed(2)}, ${state.lon.toFixed(2)} · ${t.toLocaleString([], { hour: "2-digit", minute: "2-digit" })}`;
      draw();
    } catch (err) {
      if (err.name !== "AbortError") {
        statusEl.textContent = `Failed to load sky data: ${err.message}`;
      }
    }
  }

  function debounce(fn, ms) {
    let handle = null;
    return (...args) => {
      if (handle) clearTimeout(handle);
      handle = setTimeout(() => fn(...args), ms);
    };
  }
  const debouncedFetch = debounce(fetchSky, 300);

  // ---- Interaction: pan ----

  function pointerPos(evt) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (evt.clientX - rect.left) * window.devicePixelRatio,
      y: (evt.clientY - rect.top) * window.devicePixelRatio,
    };
  }

  canvas.addEventListener("pointerdown", (evt) => {
    state.dragging = true;
    state.lastPointer = pointerPos(evt);
    canvas.setPointerCapture(evt.pointerId);
  });

  canvas.addEventListener("pointermove", (evt) => {
    if (state.dragging && state.lastPointer) {
      const p = pointerPos(evt);
      const dx = p.x - state.lastPointer.x;
      const dy = p.y - state.lastPointer.y;
      const dAzRad = -dx / state.pixelsPerUnit;
      const dAltRad = dy / state.pixelsPerUnit;
      state.centerAz = (state.centerAz + dAzRad * RAD2DEG + 360) % 360;
      state.centerAlt = Math.max(-90, Math.min(90, state.centerAlt + dAltRad * RAD2DEG));
      state.lastPointer = p;
      draw();
    } else {
      handleHover(evt);
    }
  });

  window.addEventListener("pointerup", (evt) => {
    state.dragging = false;
    state.lastPointer = null;
  });

  canvas.addEventListener("wheel", (evt) => {
    evt.preventDefault();
    const factor = Math.exp(evt.deltaY * 0.001);
    state.fovDeg = Math.max(20, Math.min(150, state.fovDeg * factor));
    draw();
  }, { passive: false });

  // Basic pinch-to-zoom for touch.
  const activePointers = new Map();
  canvas.addEventListener("pointerdown", (evt) => activePointers.set(evt.pointerId, pointerPos(evt)));
  canvas.addEventListener("pointermove", (evt) => {
    if (!activePointers.has(evt.pointerId)) return;
    activePointers.set(evt.pointerId, pointerPos(evt));
    if (activePointers.size === 2) {
      const pts = [...activePointers.values()];
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (state.pinchStartDist == null) {
        state.pinchStartDist = dist;
        state.pinchStartFov = state.fovDeg;
      } else {
        state.fovDeg = Math.max(20, Math.min(150, state.pinchStartFov * (state.pinchStartDist / dist)));
        draw();
      }
    }
  });
  function clearPointer(evt) {
    activePointers.delete(evt.pointerId);
    if (activePointers.size < 2) {
      state.pinchStartDist = null;
      state.pinchStartFov = null;
    }
  }
  canvas.addEventListener("pointerup", clearPointer);
  canvas.addEventListener("pointercancel", clearPointer);

  // ---- Hover / tooltip ----

  function allTargets() {
    if (!state.skyData) return [];
    const targets = [];
    for (const s of state.skyData.stars) if (s._screen) targets.push({ ...s, kind: "star" });
    for (const p of state.skyData.planets) if (p._screen) targets.push({ ...p, kind: "planet" });
    if (state.skyData.sun._screen) targets.push({ ...state.skyData.sun, kind: "sun", name: "Sun" });
    if (state.skyData.moon._screen) targets.push({ ...state.skyData.moon, kind: "moon", name: "Moon" });
    return targets;
  }

  function handleHover(evt) {
    const p = pointerPos(evt);
    let best = null;
    let bestDist = Infinity;
    for (const t of allTargets()) {
      const d = Math.hypot(t._screen.sx - p.x, t._screen.sy - p.y);
      if (d < t._screen.r + 10 * window.devicePixelRatio && d < bestDist) {
        best = t;
        bestDist = d;
      }
    }
    if (best) {
      showTooltip(best, evt.clientX, evt.clientY);
    } else {
      hideTooltip();
    }
  }

  function showTooltip(target, clientX, clientY) {
    const label = target.name || `HIP ${target.hip}`;
    let detail = "";
    if (target.kind === "star" || target.kind === "planet") {
      detail = ` · mag ${target.mag.toFixed(1)}`;
    } else if (target.kind === "moon") {
      detail = ` · ${Math.round(target.illuminated_fraction * 100)}% illuminated`;
    }
    tooltip.textContent = `${label}${detail}`;
    tooltip.style.left = `${clientX}px`;
    tooltip.style.top = `${clientY}px`;
    tooltip.classList.remove("hidden");
  }

  function hideTooltip() {
    tooltip.classList.add("hidden");
  }

  canvas.addEventListener("pointerleave", hideTooltip);

  // Tap-to-show on touch (pointermove already handles hover for mouse).
  canvas.addEventListener("click", (evt) => {
    if (Math.abs(evt.movementX) + Math.abs(evt.movementY) > 4) return; // was a drag
    handleHover(evt);
  });

  // ---- Controls wiring ----

  function applyLocation(lat, lon) {
    state.lat = lat;
    state.lon = lon;
    latInput.value = lat.toFixed(4);
    lonInput.value = lon.toFixed(4);
    fetchSky();
  }

  useLocationBtn.addEventListener("click", () => {
    if (!navigator.geolocation) {
      statusEl.textContent = "Geolocation not supported; enter coordinates manually.";
      return;
    }
    statusEl.textContent = "Requesting location...";
    navigator.geolocation.getCurrentPosition(
      (pos) => applyLocation(pos.coords.latitude, pos.coords.longitude),
      (err) => {
        statusEl.textContent = `Location unavailable (${err.message}); enter coordinates manually.`;
      },
      { timeout: 10000 }
    );
  });

  applyLocationBtn.addEventListener("click", () => {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      applyLocation(lat, lon);
    }
  });

  timeSlider.addEventListener("input", () => {
    state.timeOffsetMinutes = parseInt(timeSlider.value, 10);
    updateTimeLabel();
    debouncedFetch();
  });

  nowButton.addEventListener("click", () => {
    state.timeOffsetMinutes = 0;
    timeSlider.value = "0";
    updateTimeLabel();
    fetchSky();
  });

  magLimitInput.addEventListener("input", () => {
    state.magLimit = parseFloat(magLimitInput.value);
    magLimitLabel.textContent = state.magLimit.toFixed(1);
    debouncedFetch();
  });

  toggleConstellations.addEventListener("change", () => {
    state.showConstellations = toggleConstellations.checked;
    draw();
  });

  toggleLabels.addEventListener("change", () => {
    state.showLabels = toggleLabels.checked;
    draw();
  });

  panelToggle.addEventListener("click", () => panel.classList.toggle("hidden"));

  window.addEventListener("resize", resize);

  // ---- Init ----

  function init() {
    latInput.value = state.lat.toFixed(4);
    lonInput.value = state.lon.toFixed(4);
    magLimitInput.value = String(state.magLimit);
    magLimitLabel.textContent = state.magLimit.toFixed(1);
    updateTimeLabel();
    resize();
    fetchSky();

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => applyLocation(pos.coords.latitude, pos.coords.longitude),
        () => {
          /* keep default location silently */
        },
        { timeout: 8000 }
      );
    }
  }

  init();
})();
