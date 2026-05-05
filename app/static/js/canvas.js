/* Landscape Planner — canvas.js
   Desktop: drag-and-drop from sidebar, scroll-to-zoom, Alt+drag pan
   Mobile:  touch drag from bottom panel, pinch-to-zoom, two-finger pan,
            Pan Mode button for single-finger pan                          */

(function () {
  "use strict";

  /* ── Fabric.js canvas ────────────────────────────────────────────── */
  const fc = new fabric.Canvas("c", {
    selection: true,
    preserveObjectStacking: true,
  });

  const CANVAS_BG = "/data/canvas.png";
  let bgImgRef = null;
  let isDirty = false;
  let panMode = false;

  /* ── Init background + saved state ──────────────────────────────── */
  function initCanvas() {
    fabric.Image.fromURL(
      CANVAS_BG,
      function (img) {
        bgImgRef = img;
        const scale = 3;
        const w = Math.round(img.width  * scale);
        const h = Math.round(img.height * scale);

        fc.setWidth(w);
        fc.setHeight(h);
        document.getElementById("dropTarget").style.width  = w + "px";
        document.getElementById("dropTarget").style.height = h + "px";

        fc.setBackgroundImage(img, fc.renderAll.bind(fc), {
          scaleX: scale, scaleY: scale,
        });
        loadSavedState();
      },
      { crossOrigin: "anonymous" }
    );
  }

  /* ── Save / load ─────────────────────────────────────────────────── */
  async function loadSavedState() {
    try {
      const r = await fetch("/api/canvas/state");
      if (!r.ok) return;
      const state = await r.json();
      if (!state.objects || !state.objects.length) return;
      fc.loadFromJSON(state, function () {
        if (bgImgRef) {
          const scale = fc.width / bgImgRef.width;
          fc.setBackgroundImage(bgImgRef, fc.renderAll.bind(fc), {
            scaleX: scale, scaleY: scale,
          });
        }
      });
    } catch (e) { console.warn("Load state:", e); }
  }

  async function saveState() {
    const status = document.getElementById("saveStatus");
    try {
      status.textContent = "Saving…";
      const json = fc.toJSON(["data"]);
      delete json.backgroundImage;
      const r = await fetch("/api/canvas/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json),
      });
      if (r.ok) {
        status.textContent = "Saved ✓";
        isDirty = false;
        setTimeout(() => { status.textContent = ""; }, 2000);
      } else {
        status.textContent = "Save failed";
      }
    } catch (e) { status.textContent = "Error"; }
  }

  /* ── Drop plant onto canvas at given canvas coordinates ──────────── */
  function dropPlantAt(imgUrl, plantId, x, y) {
    fabric.Image.fromURL(
      imgUrl,
      function (img) {
        const targetW = 120;
        const scale = targetW / img.width;
        img.set({
          left: x, top: y,
          originX: "center", originY: "center",
          scaleX: scale, scaleY: scale,
          data: { plantId },
        });
        fc.add(img);
        fc.setActiveObject(img);
        fc.renderAll();
      },
      { crossOrigin: "anonymous" }
    );
  }

  /* ── Toolbar buttons ─────────────────────────────────────────────── */
  document.getElementById("btnSave").addEventListener("click", saveState);

  document.getElementById("btnDelete").addEventListener("click", () => {
    const obj = fc.getActiveObject();
    if (!obj) return;
    if (obj.type === "activeSelection") {
      obj.forEachObject(o => fc.remove(o));
      fc.discardActiveObject();
    } else {
      fc.remove(obj);
    }
    fc.renderAll();
    isDirty = true;
  });

  document.getElementById("btnBringFwd").addEventListener("click", () => {
    const obj = fc.getActiveObject();
    if (obj) { fc.bringForward(obj); isDirty = true; }
  });
  document.getElementById("btnSendBack").addEventListener("click", () => {
    const obj = fc.getActiveObject();
    if (obj) { fc.sendBackwards(obj); isDirty = true; }
  });

  /* ── Zoom ────────────────────────────────────────────────────────── */
  function zoomTo(factor, cx, cy) {
    let z = fc.getZoom() * factor;
    z = Math.max(0.1, Math.min(z, 10));
    if (cx !== undefined) {
      fc.zoomToPoint(new fabric.Point(cx, cy), z);
    } else {
      const c = fc.getCenter();
      fc.zoomToPoint(new fabric.Point(c.left, c.top), z);
    }
  }

  document.getElementById("btnZoomIn").addEventListener("click",    () => zoomTo(1.25));
  document.getElementById("btnZoomOut").addEventListener("click",   () => zoomTo(0.8));
  document.getElementById("btnZoomReset").addEventListener("click", () => {
    fc.setViewportTransform([1, 0, 0, 1, 0, 0]);
    fc.renderAll();
  });

  // Mouse-wheel zoom (desktop)
  fc.on("mouse:wheel", function (opt) {
    zoomTo(0.999 ** opt.e.deltaY, opt.e.offsetX, opt.e.offsetY);
    opt.e.preventDefault();
    opt.e.stopPropagation();
  });

  /* ── Pan mode toggle ─────────────────────────────────────────────── */
  const btnPan = document.getElementById("btnPan");
  btnPan.addEventListener("click", () => {
    panMode = !panMode;
    btnPan.classList.toggle("active", panMode);
    btnPan.title = panMode ? "Pan mode ON — tap to switch back to select" : "Pan mode (drag to move view)";
    fc.selection = !panMode;
    fc.forEachObject(o => { o.selectable = !panMode; });
    fc.setCursor(panMode ? "grab" : "default");
    if (!panMode) fc.renderAll();
  });

  /* ── Alt+drag pan (desktop) ──────────────────────────────────────── */
  let altPanning = false, altLastX = 0, altLastY = 0;

  fc.on("mouse:down", opt => {
    if (opt.e.altKey) {
      altPanning = true;
      altLastX = opt.e.clientX;
      altLastY = opt.e.clientY;
      fc.selection = false;
    }
  });
  fc.on("mouse:move", opt => {
    if (!altPanning) return;
    const vpt = fc.viewportTransform;
    vpt[4] += opt.e.clientX - altLastX;
    vpt[5] += opt.e.clientY - altLastY;
    altLastX = opt.e.clientX;
    altLastY = opt.e.clientY;
    fc.requestRenderAll();
  });
  fc.on("mouse:up", () => {
    altPanning = false;
    if (!panMode) fc.selection = true;
  });

  fc.on("object:modified", () => { isDirty = true; });
  fc.on("object:added",    () => { isDirty = true; });
  fc.on("object:removed",  () => { isDirty = true; });

  /* ── Touch: pinch-zoom + two-finger pan + single-finger pan mode ─── */
  /* Listeners on canvasWrapper in capture phase so we intercept before
     Fabric.js sees the events on its own canvas element.               */
  const canvasWrapper = document.getElementById("canvasWrapper");
  let pinchDist = 0;
  let pinchMid  = null;
  let panTouch  = null;

  function touchDist(touches) {
    return Math.hypot(
      touches[0].clientX - touches[1].clientX,
      touches[0].clientY - touches[1].clientY
    );
  }
  function touchMid(touches, rect) {
    return {
      x: (touches[0].clientX + touches[1].clientX) / 2 - rect.left,
      y: (touches[0].clientY + touches[1].clientY) / 2 - rect.top,
      cx: (touches[0].clientX + touches[1].clientX) / 2,
      cy: (touches[0].clientY + touches[1].clientY) / 2,
    };
  }

  canvasWrapper.addEventListener("touchstart", e => {
    if (e.touches.length === 2) {
      e.preventDefault();
      e.stopPropagation();
      pinchDist = touchDist(e.touches);
      pinchMid  = touchMid(e.touches, fc.upperCanvasEl.getBoundingClientRect());
      panTouch  = null;
    } else if (panMode && e.touches.length === 1) {
      e.preventDefault();
      e.stopPropagation();
      panTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }, { capture: true, passive: false });

  canvasWrapper.addEventListener("touchmove", e => {
    if (e.touches.length === 2) {
      e.preventDefault();
      e.stopPropagation();
      const rect = fc.upperCanvasEl.getBoundingClientRect();
      const dist = touchDist(e.touches);
      const mid  = touchMid(e.touches, rect);

      if (pinchDist > 0) zoomTo(dist / pinchDist, mid.x, mid.y);
      if (pinchMid) {
        const vpt = fc.viewportTransform;
        vpt[4] += mid.cx - pinchMid.cx;
        vpt[5] += mid.cy - pinchMid.cy;
        fc.requestRenderAll();
      }
      pinchDist = dist;
      pinchMid  = mid;
    } else if (panMode && e.touches.length === 1 && panTouch) {
      e.preventDefault();
      e.stopPropagation();
      const vpt = fc.viewportTransform;
      vpt[4] += e.touches[0].clientX - panTouch.x;
      vpt[5] += e.touches[0].clientY - panTouch.y;
      panTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      fc.requestRenderAll();
    }
  }, { capture: true, passive: false });

  canvasWrapper.addEventListener("touchend", e => {
    if (e.touches.length < 2) { pinchDist = 0; pinchMid = null; }
    if (e.touches.length === 0) panTouch = null;
  }, { capture: true, passive: true });

  /* ── Plant gallery loader ─────────────────────────────────────────── */
  let _plantsCache = null;

  async function fetchPlants() {
    if (_plantsCache) return _plantsCache;
    const r = await fetch("/api/plants");
    if (!r.ok) throw new Error(r.status);
    _plantsCache = await r.json();
    return _plantsCache;
  }

  function buildGallery(gallery, plants) {
    if (!plants.length) {
      gallery.innerHTML = '<div class="text-muted small text-center py-3">No plants yet.<br><a href="/plants/upload">Add plants first</a></div>';
      return;
    }
    gallery.innerHTML = "";
    plants.forEach(p => gallery.appendChild(makeTile(p)));
  }

  async function loadDesktopGallery() {
    const gallery = document.getElementById("plantGallery");
    if (!gallery) return;
    try { buildGallery(gallery, await fetchPlants()); }
    catch (e) { gallery.innerHTML = '<div class="text-danger small py-2">Error loading plants</div>'; }
  }

  async function loadMobileGallery() {
    const gallery = document.getElementById("mobileGallery");
    if (!gallery) return;
    gallery.innerHTML = '<div class="text-muted small py-3 px-2">Loading…</div>';
    try { buildGallery(gallery, await fetchPlants()); }
    catch (e) { gallery.innerHTML = '<div class="text-danger small py-2 px-2">Error loading plants</div>'; }
  }

  // Populate mobile gallery each time the panel opens
  document.getElementById("mobilePlants")
    .addEventListener("show.bs.offcanvas", loadMobileGallery);

  function makeTile(p) {
    const div = document.createElement("div");
    div.className = "plant-tile";
    div.dataset.imgUrl  = p.image_path || p.thumbnail_path || "";
    div.dataset.plantId = p.id;
    div.dataset.name    = ((p.common_name || "") + " " + (p.scientific_name || "")).toLowerCase();

    const imgSrc = p.thumbnail_path || p.image_path || "";
    div.innerHTML = imgSrc
      ? `<img src="${imgSrc}" alt="${p.common_name || ""}" draggable="false">`
      : `<div style="height:80px;display:flex;align-items:center;justify-content:center;background:#e8f3e8"><i class="bi bi-flower1" style="font-size:2rem;color:#2d7a2d"></i></div>`;
    div.innerHTML += `<div class="name">${p.common_name || p.scientific_name || "Plant"}</div>`;

    // Desktop: HTML drag-and-drop
    div.draggable = true;
    div.addEventListener("dragstart", e => {
      e.dataTransfer.setData("plantId", div.dataset.plantId);
      e.dataTransfer.setData("imgUrl",  div.dataset.imgUrl);
      e.dataTransfer.effectAllowed = "copy";
    });

    // Mobile: touch drag
    addTouchDrag(div);

    return div;
  }

  /* ── Sidebar search (desktop) ────────────────────────────────────── */
  document.getElementById("sidebarSearch").addEventListener("input", function () {
    const q = this.value.toLowerCase();
    document.querySelectorAll("#plantGallery .plant-tile").forEach(t => {
      t.style.display = (t.dataset.name || "").includes(q) ? "" : "none";
    });
  });

  /* Mobile search */
  document.getElementById("mobileSearch").addEventListener("input", function () {
    const q = this.value.toLowerCase();
    document.querySelectorAll("#mobileGallery .plant-tile").forEach(t => {
      t.style.display = (t.dataset.name || "").includes(q) ? "" : "none";
    });
  });

  /* ── Desktop drag-and-drop onto canvas ───────────────────────────── */
  const dropTarget  = document.getElementById("dropTarget");
  const dropOverlay = document.getElementById("dropOverlay");

  dropTarget.addEventListener("dragenter", e => { e.preventDefault(); dropOverlay.style.display = "flex"; });
  dropTarget.addEventListener("dragleave", e => {
    if (!dropTarget.contains(e.relatedTarget)) dropOverlay.style.display = "none";
  });
  dropTarget.addEventListener("dragover", e => e.preventDefault());
  dropTarget.addEventListener("drop", e => {
    e.preventDefault();
    dropOverlay.style.display = "none";
    const imgUrl  = e.dataTransfer.getData("imgUrl");
    const plantId = e.dataTransfer.getData("plantId");
    if (!imgUrl) return;
    const rect = fc.getElement().getBoundingClientRect();
    const zoom = fc.getZoom();
    const vpt  = fc.viewportTransform;
    dropPlantAt(imgUrl, plantId,
      (e.clientX - rect.left - vpt[4]) / zoom,
      (e.clientY - rect.top  - vpt[5]) / zoom
    );
  });

  /* ── Touch drag-and-drop ─────────────────────────────────────────── */
  const ghost       = document.getElementById("touchGhost");
  const ghostImg    = document.getElementById("touchGhostImg");
  let   touchDragData = null;

  function addTouchDrag(tile) {
    tile.addEventListener("touchstart", e => {
      if (e.touches.length !== 1) return;
      touchDragData = { imgUrl: tile.dataset.imgUrl, plantId: tile.dataset.plantId };
      ghostImg.src = tile.querySelector("img")?.src || "";
      ghost.style.display = "block";
      ghost.style.left = e.touches[0].clientX + "px";
      ghost.style.top  = e.touches[0].clientY + "px";
      tile.classList.add("touch-active");
      e.preventDefault();
    }, { passive: false });

    tile.addEventListener("touchmove", e => {
      if (!touchDragData) return;
      ghost.style.left = e.touches[0].clientX + "px";
      ghost.style.top  = e.touches[0].clientY + "px";
      e.preventDefault();
    }, { passive: false });

    tile.addEventListener("touchend", e => {
      tile.classList.remove("touch-active");
      ghost.style.display = "none";
      if (!touchDragData) return;

      const touch = e.changedTouches[0];
      const canvasEl = fc.getElement();
      const rect = canvasEl.getBoundingClientRect();

      if (
        touch.clientX >= rect.left && touch.clientX <= rect.right &&
        touch.clientY >= rect.top  && touch.clientY <= rect.bottom
      ) {
        const zoom = fc.getZoom();
        const vpt  = fc.viewportTransform;
        dropPlantAt(
          touchDragData.imgUrl, touchDragData.plantId,
          (touch.clientX - rect.left - vpt[4]) / zoom,
          (touch.clientY - rect.top  - vpt[5]) / zoom
        );
        // Close mobile panel after placing
        const offcanvas = bootstrap.Offcanvas.getInstance(
          document.getElementById("mobilePlants")
        );
        if (offcanvas) offcanvas.hide();
      }
      touchDragData = null;
    }, { passive: false });
  }

  /* ── Keyboard shortcuts ──────────────────────────────────────────── */
  document.addEventListener("keydown", e => {
    if (["Delete", "Backspace"].includes(e.key) && document.activeElement === document.body) {
      const obj = fc.getActiveObject();
      if (!obj) return;
      if (obj.type === "activeSelection") {
        obj.forEachObject(o => fc.remove(o));
        fc.discardActiveObject();
      } else {
        fc.remove(obj);
      }
      fc.renderAll();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      saveState();
    }
  });

  window.addEventListener("beforeunload", e => {
    if (isDirty) { e.preventDefault(); e.returnValue = ""; }
  });

  /* ── Start ───────────────────────────────────────────────────────── */
  initCanvas();
  loadDesktopGallery();
})();
