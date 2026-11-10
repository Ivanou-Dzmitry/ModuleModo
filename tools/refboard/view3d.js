'use strict';

// 3D preview on plain WebGL2: the house is a box textured with the facade layouts,
// with a gable roof. Front = front layout, both sides = side layout, back = filler wall.
// Simple fake AO: a soft contact shadow on the ground and wall darkening at the base and under the eaves.
const View3D = (() => {
  const PX_PER_M = 64;        // facade texture resolution
  const OVERHANG = 0.3;       // roof overhang, m
  const SNAP_W = 1240, SNAP_H = 680;

  let canvas, gl, prog, loc, meshes = [], textures = [];
  let ready = false, visible = false, dirty = true, frame = 0;
  const cam = { yaw: 0.6, pitch: 0.28, zoom: 1 };
  let dims = { w: 1, d: 1, h: 1, r: 0 };

  // ---------- math (column-major 4×4) ----------
  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }
  function lookAt(e, c, up) {
    const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    const norm = a => { const l = Math.hypot(...a) || 1; return a.map(v => v / l); };
    const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const z = norm(sub(e, c)), x = norm(cross(up, z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1];
  }
  function mul(a, b) {
    const o = new Array(16).fill(0);
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
    return o;
  }

  // ---------- GL setup ----------
  const VS = `#version 300 es
    in vec3 aPos; in vec3 aNor; in vec2 aUv;
    uniform mat4 uMvp; out vec3 vNor; out vec2 vUv; out vec3 vPos;
    void main() { gl_Position = uMvp * vec4(aPos, 1.0); vNor = aNor; vUv = aUv; vPos = aPos; }`;
  const FS = `#version 300 es
    precision mediump float;
    in vec3 vNor; in vec2 vUv; in vec3 vPos;
    uniform sampler2D uTex; uniform vec3 uLight; uniform int uAo; uniform float uTop;
    out vec4 outColor;
    void main() {
      vec4 c = texture(uTex, vUv);
      float l = 0.58 + 0.42 * max(dot(normalize(vNor), uLight), 0.0);
      float ao = 1.0;
      if (uAo > 0) ao *= mix(0.6, 1.0, smoothstep(0.0, 1.4, vPos.y));          // base of the wall
      if (uAo > 1) ao *= mix(0.72, 1.0, smoothstep(0.0, 0.7, uTop - vPos.y));  // under the eaves
      outColor = vec4(c.rgb * l * ao, c.a);
    }`;

  function init() {
    canvas = document.getElementById('view3d');
    // opaque canvas: the blended contact shadow must not leave see-through pixels in exports
    gl = canvas.getContext('webgl2', { antialias: true, preserveDrawingBuffer: true, alpha: false });
    if (!gl) return false;
    const sh = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    loc = {
      pos: gl.getAttribLocation(prog, 'aPos'), nor: gl.getAttribLocation(prog, 'aNor'), uv: gl.getAttribLocation(prog, 'aUv'),
      mvp: gl.getUniformLocation(prog, 'uMvp'), tex: gl.getUniformLocation(prog, 'uTex'), light: gl.getUniformLocation(prog, 'uLight'),
      ao: gl.getUniformLocation(prog, 'uAo'), top: gl.getUniformLocation(prog, 'uTop'),
    };
    gl.enable(gl.DEPTH_TEST);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    bindControls();
    return true;
  }

  function texture(source, repeat) {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    const wrap = repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
    textures.push(t);
    return t;
  }

  const colourCanvas = hex => {
    const c = document.createElement('canvas'); c.width = c.height = 4;
    const x = c.getContext('2d'); x.fillStyle = hex; x.fillRect(0, 0, 4, 4);
    return c;
  };

  // ---------- textures from the facade layouts ----------
  const WALL = '#9a948c';

  function paintCell(c, mod, x, y, w, h) {
    const img = mod && getImage(mod.src);
    if (img) drawCover(c, img, x, y, w, h, mod.crop);
    else { c.fillStyle = WALL; c.fillRect(x, y, w, h); }
  }

  // Same rules as the sheet: a module lower than its floor sits at the top, the filler fills the rest.
  function facadeCanvas(layout, n) {
    const fl = floors(), g = state.grid, filler = byId(state.filler);
    const cv = document.createElement('canvas');
    cv.width = Math.max(4, Math.round(n * g * PX_PER_M));
    cv.height = Math.max(4, Math.round(fl.reduce((a, b) => a + b, 0) * PX_PER_M));
    const c = cv.getContext('2d');
    let top = cv.height, acc = 0;
    fl.forEach((fh, f) => {
      acc += fh;
      const y = Math.round(cv.height - acc * PX_PER_M), cellH = top - y;
      for (let b = 0; b < n; b++) {
        const x = Math.round(b * g * PX_PER_M), w = Math.round((b + 1) * g * PX_PER_M) - x;
        const mod = byId(layout[`${f}_${b}`]);
        if (!mod) { paintCell(c, filler, x, y, w, cellH); continue; }
        const mh = Math.min(cellH, Math.round(mod.h * PX_PER_M));
        if (mh < cellH) paintCell(c, filler, x, y + mh, w, cellH - mh);
        paintCell(c, mod, x, y, w, mh);
      }
      top = y;
    });
    return cv;
  }

  function fillerTile() {
    const cv = document.createElement('canvas'); cv.width = cv.height = 256;
    paintCell(cv.getContext('2d'), byId(state.filler), 0, 0, 256, 256);
    return cv;
  }

  // Soft dark blob under the house: the footprint blurred out by `margin` metres on each side.
  function contactShadow(w, d, margin) {
    const k = 512 / (w + 2 * margin);
    const cv = document.createElement('canvas');
    cv.width = 512; cv.height = Math.max(8, Math.round((d + 2 * margin) * k));
    const c = cv.getContext('2d');
    const far = 10000;                       // draw the shape off-canvas and keep only its blurred shadow
    c.shadowColor = 'rgba(0,0,0,0.5)'; c.shadowBlur = margin * k * 0.9; c.shadowOffsetX = far;
    c.fillRect(margin * k * 0.55 - far, margin * k * 0.55, (w + margin * 0.9) * k, (d + margin * 0.9) * k);
    return cv;
  }

  // ---------- mesh ----------
  function pushQuad(arr, p, n, uv) {
    const [u0, v0, u1, v1] = uv;
    const t = [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
    for (const i of [0, 1, 2, 0, 2, 3]) arr.push(...p[i], ...n, ...t[i]);
  }
  function pushTri(arr, p, n, t) { for (let i = 0; i < 3; i++) arr.push(...p[i], ...n, ...t[i]); }

  // ao: 0 none, 1 darken the base, 2 base and under the eaves; blend: transparent overlay drawn last
  function mesh(tex, data, ao = 0, blend = false) {
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW);
    meshes.push({ tex, buf, count: data.length / 8, ao, blend });
  }

  function rebuild() {
    meshes.forEach(m => gl.deleteBuffer(m.buf)); meshes = [];
    textures.forEach(t => gl.deleteTexture(t)); textures = [];

    const g = state.grid, n = state.bays, sideN = state.depthBays > 0 ? state.depthBays : 2;
    const w = n * g, d = sideN * g, h = floors().reduce((a, b) => a + b, 0), r = state.roof ? 1.6 : 0;
    dims = { w, d, h, r };
    const X = w / 2, Z = d / 2;

    const front = [], back = [], sides = [], gables = [], roof = [], ground = [], blob = [];
    pushQuad(front, [[-X, 0, Z], [X, 0, Z], [X, h, Z], [-X, h, Z]], [0, 0, 1], [0, 0, 1, 1]);
    pushQuad(back, [[X, 0, -Z], [-X, 0, -Z], [-X, h, -Z], [X, h, -Z]], [0, 0, -1], [0, 0, n, h / g]);
    // seen from the right, the front corner is on the left, as on the sheet; the left side is its mirror
    pushQuad(sides, [[X, 0, Z], [X, 0, -Z], [X, h, -Z], [X, h, Z]], [1, 0, 0], [0, 0, 1, 1]);
    pushQuad(sides, [[-X, 0, -Z], [-X, 0, Z], [-X, h, Z], [-X, h, -Z]], [-1, 0, 0], [1, 0, 0, 1]);

    if (r > 0) {
      for (const sx of [1, -1]) {
        pushTri(gables, [[sx * X, h, Z], [sx * X, h, -Z], [sx * X, h + r, 0]], [sx, 0, 0],
          [[0, 0], [d / g, 0], [d / g / 2, r / g]]);
      }
      const ye = h - OVERHANG * r / Z, xe = X + OVERHANG, ze = Z + OVERHANG;
      const nl = Math.hypot(Z, r);
      pushQuad(roof, [[-xe, ye, ze], [xe, ye, ze], [xe, h + r, 0], [-xe, h + r, 0]], [0, Z / nl, r / nl], [0, 0, 1, 1]);
      pushQuad(roof, [[xe, ye, -ze], [-xe, ye, -ze], [-xe, h + r, 0], [xe, h + r, 0]], [0, Z / nl, -r / nl], [0, 0, 1, 1]);
    } else {
      pushQuad(roof, [[-X, h, Z], [X, h, Z], [X, h, -Z], [-X, h, -Z]], [0, 1, 0], [0, 0, 1, 1]);
    }
    const G = Math.max(w, d) * 3;
    pushQuad(ground, [[-G, 0, G], [G, 0, G], [G, 0, -G], [-G, 0, -G]], [0, 1, 0], [0, 0, 1, 1]);
    const MB = 1.6, bx = X + MB, bz = Z + MB;
    pushQuad(blob, [[-bx, 0.01, bz], [bx, 0.01, bz], [bx, 0.01, -bz], [-bx, 0.01, -bz]], [0, 1, 0], [0, 0, 1, 1]);

    // eaves run along the front and the back, so only those walls get the under-eaves term
    const eaves = r > 0 ? 2 : 1;
    mesh(texture(facadeCanvas(state.layout, n)), front, eaves);
    mesh(texture(facadeCanvas(state.depthBays > 0 ? state.layoutSide : {}, sideN)), sides, 1);
    const tile = texture(fillerTile(), true);
    mesh(tile, back, eaves);
    if (gables.length) mesh(tile, gables);
    mesh(texture(colourCanvas(state.roofColor || '#8a4b3b')), roof);
    mesh(texture(colourCanvas(mix(state.bg || '#f1efea', state.ink || '#1e1e1e', 0.12))), ground);
    mesh(texture(contactShadow(w, d, MB)), blob, 0, true);
    dirty = false;
  }

  // ---------- draw ----------
  function draw(width, height) {
    if (dirty) rebuild();
    gl.viewport(0, 0, width, height);
    const bg = rgb(state.bg || '#f1efea').map(v => v / 255);
    gl.clearColor(bg[0], bg[1], bg[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    const { w, d, h, r } = dims;
    const target = [0, (h + r) * 0.45, 0];
    const dist = Math.max(w, d, h + r) * 1.45 * cam.zoom;
    const eye = [
      target[0] + dist * Math.cos(cam.pitch) * Math.sin(cam.yaw),
      target[1] + dist * Math.sin(cam.pitch),
      target[2] + dist * Math.cos(cam.pitch) * Math.cos(cam.yaw),
    ];
    const mvp = mul(perspective(0.6, width / height, 0.1, dist * 10), lookAt(eye, target, [0, 1, 0]));

    gl.useProgram(prog);
    gl.uniformMatrix4fv(loc.mvp, false, mvp);
    const L = [0.5, 0.75, 0.6], ll = Math.hypot(...L);
    gl.uniform3f(loc.light, L[0] / ll, L[1] / ll, L[2] / ll);
    gl.uniform1i(loc.tex, 0);
    gl.uniform1f(loc.top, h);
    gl.activeTexture(gl.TEXTURE0);
    for (const m of meshes) {
      gl.uniform1i(loc.ao, m.ao);
      if (m.blend) { gl.enable(gl.BLEND); gl.depthMask(false); } else { gl.disable(gl.BLEND); gl.depthMask(true); }
      gl.bindBuffer(gl.ARRAY_BUFFER, m.buf);
      gl.enableVertexAttribArray(loc.pos); gl.vertexAttribPointer(loc.pos, 3, gl.FLOAT, false, 32, 0);
      gl.enableVertexAttribArray(loc.nor); gl.vertexAttribPointer(loc.nor, 3, gl.FLOAT, false, 32, 12);
      gl.enableVertexAttribArray(loc.uv); gl.vertexAttribPointer(loc.uv, 2, gl.FLOAT, false, 32, 24);
      gl.bindTexture(gl.TEXTURE_2D, m.tex);
      gl.drawArrays(gl.TRIANGLES, 0, m.count);
    }
    gl.disable(gl.BLEND); gl.depthMask(true);
  }

  function fitCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = Math.round(canvas.clientWidth * dpr), ch = Math.round(canvas.clientHeight * dpr);
    if (cw && ch && (canvas.width !== cw || canvas.height !== ch)) { canvas.width = cw; canvas.height = ch; }
  }

  function requestDraw() {
    if (!ready || !visible || frame) return;
    frame = requestAnimationFrame(() => { frame = 0; fitCanvas(); draw(canvas.width, canvas.height); });
  }

  // ---------- controls ----------
  function bindControls() {
    let drag = null;
    canvas.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY }; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener('pointerup', () => { drag = null; });
    canvas.addEventListener('pointermove', e => {
      if (!drag) return;
      cam.yaw -= (e.clientX - drag.x) * 0.008;
      cam.pitch = clamp(cam.pitch + (e.clientY - drag.y) * 0.006, -0.05, 1.45);
      drag = { x: e.clientX, y: e.clientY };
      requestDraw();
    });
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      cam.zoom = clamp(cam.zoom * (e.deltaY < 0 ? 1 / 1.1 : 1.1), 0.35, 3);
      requestDraw();
    }, { passive: false });
    window.addEventListener('resize', requestDraw);
  }

  // ---------- public ----------
  return {
    available() {
      if (!ready && canvas === undefined) {
        try { ready = init(); } catch (e) { console.error(e); ready = false; }
      }
      return ready;
    },
    show(on) { visible = on; requestDraw(); },
    invalidate() { dirty = true; requestDraw(); },
    resetView() { cam.yaw = 0.6; cam.pitch = 0.28; cam.zoom = 1; requestDraw(); },
    // Renders the current view at w×h (default: the general-view aspect) and returns a PNG data URL.
    snapshot(w = SNAP_W, h = SNAP_H) {
      const ow = canvas.width, oh = canvas.height;
      canvas.width = w; canvas.height = h;
      draw(w, h);
      const url = canvas.toDataURL('image/png');
      canvas.width = ow; canvas.height = oh;
      requestDraw();
      return url;
    },
  };
})();
