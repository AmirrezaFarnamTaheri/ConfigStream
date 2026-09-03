/**
 * ConfigStream - Procedural 3D Polyhedral Hero Node
 *
 * High-craft, lightweight procedural 3D geometric node featuring:
 * - Dual polyhedral core + wireframe orbital cage + pulsing data nodes
 * - Cold Luxury palette (Electric Cobalt #3b82f6, Cyan #06b6d4)
 * - Hardware DPR clamping: Math.min(window.devicePixelRatio || 1, 1.5)
 * - WCAG 2.2 AA Reduced Motion detection & static single-frame rendering
 * - Offscreen lifecycle management via IntersectionObserver & RAF gating
 * - WebGL context loss and restoration handling
 * - Pure 2D Canvas graceful fallback
 * - Clean teardown hook exported at window._disposeHeroNode()
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

(function (global) {
  'use strict';

  // Cold Luxury design tokens
  const PALETTE = {
    cobalt: '#3b82f6',
    cobaltRgb: [59, 130, 246],
    cobaltHex: 0x3b82f6,
    cyan: '#06b6d4',
    cyanRgb: [6, 182, 212],
    cyanHex: 0x06b6d4,
    glow: 'rgba(6, 182, 212, 0.35)',
    coreGlow: 'rgba(59, 130, 246, 0.45)',
    whiteGlow: 'rgba(255, 255, 255, 0.85)'
  };

  // State
  let canvas = null;
  let container = null;
  let gl = null;
  let ctx2d = null;
  let isWebGL = false;
  let isContextLost = false;
  let isVisible = true;
  let isReducedMotion = false;
  let rafId = null;
  let resizeObserver = null;
  let intersectionObserver = null;
  let mediaQueryList = null;
  let glResources = null;
  let animationTime = 0;
  let lastTimestamp = 0;

  // Geometry: Golden ratio and Icosahedron coordinates
  const PHI = (1 + Math.sqrt(5)) / 2;

  // 12 vertices of regular icosahedron (normalized)
  function createIcosahedronVertices(scale) {
    const raw = [
      [-1,  PHI, 0], [ 1,  PHI, 0], [-1, -PHI, 0], [ 1, -PHI, 0],
      [ 0, -1,  PHI], [ 0,  1,  PHI], [ 0, -1, -PHI], [ 0,  1, -PHI],
      [ PHI, 0, -1], [ PHI, 0,  1], [-PHI, 0, -1], [-PHI, 0,  1]
    ];
    return raw.map(v => {
      const len = Math.hypot(v[0], v[1], v[2]);
      return [ (v[0] / len) * scale, (v[1] / len) * scale, (v[2] / len) * scale ];
    });
  }

  // 30 unique edges of an icosahedron
  const ICOSAHEDRON_EDGES = [
    [0, 11], [0, 5], [0, 1], [0, 7], [0, 10],
    [1, 5], [5, 11], [11, 10], [10, 7], [7, 1],
    [3, 9], [3, 4], [3, 2], [3, 6], [3, 8],
    [4, 9], [9, 8], [8, 6], [6, 2], [2, 4],
    [1, 9], [5, 4], [11, 2], [10, 6], [7, 8],
    [6, 7], [1, 8], [5, 9], [11, 4], [10, 2]
  ];

  // 20 vertices of regular dodecahedron (dual cage, normalized)
  function createDodecahedronVertices(scale) {
    const raw = [
      [-1, -1, -1], [-1, -1,  1], [-1,  1, -1], [-1,  1,  1],
      [ 1, -1, -1], [ 1, -1,  1], [ 1,  1, -1], [ 1,  1,  1],
      [ 0, -1/PHI, -PHI], [ 0, -1/PHI,  PHI], [ 0,  1/PHI, -PHI], [ 0,  1/PHI,  PHI],
      [-1/PHI, -PHI, 0], [-1/PHI,  PHI, 0], [ 1/PHI, -PHI, 0], [ 1/PHI,  PHI, 0],
      [-PHI, 0, -1/PHI], [-PHI, 0,  1/PHI], [ PHI, 0, -1/PHI], [ PHI, 0,  1/PHI]
    ];
    return raw.map(v => {
      const len = Math.hypot(v[0], v[1], v[2]);
      return [ (v[0] / len) * scale, (v[1] / len) * scale, (v[2] / len) * scale ];
    });
  }

  // 30 edges of a dodecahedron
  const DODECAHEDRON_EDGES = [
    [0, 8], [0, 12], [0, 16], [1, 9], [1, 12], [1, 17],
    [2, 10], [2, 13], [2, 16], [3, 11], [3, 13], [3, 17],
    [4, 8], [4, 14], [4, 18], [5, 9], [5, 14], [5, 19],
    [6, 10], [6, 15], [6, 18], [7, 11], [7, 15], [7, 19],
    [8, 10], [9, 11], [12, 14], [13, 15], [16, 17], [18, 19]
  ];

  let staticGeometry = null;

  function buildWireGeometry(vertices, edges, firstColor, secondColor) {
    const positions = [];
    const colors = [];
    for (const [first, second] of edges) {
      positions.push(...vertices[first], ...vertices[second]);
      colors.push(...firstColor, ...secondColor);
    }
    return {
      positions: new Float32Array(positions),
      colors: new Float32Array(colors)
    };
  }

  function getStaticGeometry() {
    if (staticGeometry) return staticGeometry;
    staticGeometry = {
      core: buildWireGeometry(
        createIcosahedronVertices(0.85),
        ICOSAHEDRON_EDGES,
        [PALETTE.cobaltRgb[0] / 255, PALETTE.cobaltRgb[1] / 255, PALETTE.cobaltRgb[2] / 255, 0.9],
        [PALETTE.cyanRgb[0] / 255, PALETTE.cyanRgb[1] / 255, PALETTE.cyanRgb[2] / 255, 0.9]
      ),
      cage: buildWireGeometry(
        createDodecahedronVertices(1.35),
        DODECAHEDRON_EDGES,
        [PALETTE.cyanRgb[0] / 255, PALETTE.cyanRgb[1] / 255, PALETTE.cyanRgb[2] / 255, 0.6],
        [PALETTE.cobaltRgb[0] / 255, PALETTE.cobaltRgb[1] / 255, PALETTE.cobaltRgb[2] / 255, 0.6]
      ),
      canvas2d: {
        cage: createDodecahedronVertices(1.35),
        core: createIcosahedronVertices(0.85),
        rings: createOrbitalRings(36, 1.6)
      }
    };
    return staticGeometry;
  }

  // Orbital rings (3 geodesic rings at differing angles)
  function createOrbitalRings(segments, radius) {
    const rings = [];
    const step = (Math.PI * 2) / segments;
    for (let r = 0; r < 3; r++) {
      const ring = [];
      const tiltX = (r * Math.PI) / 3;
      const tiltY = (r * Math.PI) / 6;
      for (let i = 0; i <= segments; i++) {
        const theta = i * step;
        let x = Math.cos(theta) * radius;
        let y = Math.sin(theta) * radius;
        let z = 0;

        // Apply tilts
        const y1 = y * Math.cos(tiltX) - z * Math.sin(tiltX);
        const z1 = y * Math.sin(tiltX) + z * Math.cos(tiltX);
        const x2 = x * Math.cos(tiltY) + z1 * Math.sin(tiltY);
        const z2 = -x * Math.sin(tiltY) + z1 * Math.cos(tiltY);

        ring.push([x2, y1, z2]);
      }
      rings.push(ring);
    }
    return rings;
  }

  // 3D rotation math helpers
  function rotate3D(point, pitch, yaw, roll) {
    let [x, y, z] = point;

    // Pitch (around X)
    const cosX = Math.cos(pitch);
    const sinX = Math.sin(pitch);
    const y1 = y * cosX - z * sinX;
    const z1 = y * sinX + z * cosX;

    // Yaw (around Y)
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);
    const x2 = x * cosY + z1 * sinY;
    const z2 = -x * sinY + z1 * cosY;

    // Roll (around Z)
    const cosZ = Math.cos(roll);
    const sinZ = Math.sin(roll);
    const x3 = x2 * cosZ - y1 * sinZ;
    const y3 = x2 * sinZ + y1 * cosZ;

    return [x3, y3, z2];
  }

  // DPR Clamping helper
  function getClampedDPR() {
    return Math.min(global.devicePixelRatio || 1, 1.5);
  }

  // Resize canvas according to container dimensions and clamped DPR
  function updateDimensions() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : { width: 300, height: 220 };
    const width = Math.max(rect.width || (container ? container.clientWidth : 300), 100);
    const height = Math.max(rect.height || (container ? container.clientHeight : 220), 100);
    const dpr = getClampedDPR();

    const targetWidth = Math.floor(width * dpr);
    const targetHeight = Math.floor(height * dpr);

    if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      if (gl && !isContextLost) {
        gl.viewport(0, 0, targetWidth, targetHeight);
      }
    }
  }

  // WebGL Shaders & Program Setup
  function initWebGL(glCtx) {
    const vsSource = `
      attribute vec3 aPosition;
      attribute vec4 aColor;
      uniform mat4 uMVP;
      varying vec4 vColor;
      varying vec3 vPos;
      void main(void) {
        gl_Position = uMVP * vec4(aPosition, 1.0);
        vColor = aColor;
        vPos = aPosition;
      }
    `;

    const fsSource = `
      precision mediump float;
      varying vec4 vColor;
      varying vec3 vPos;
      uniform float uTime;
      void main(void) {
        float pulse = 0.85 + 0.15 * sin(uTime * 2.0 + length(vPos));
        gl_FragColor = vec4(vColor.rgb * pulse, vColor.a);
      }
    `;

    function compile(type, src) {
      const s = glCtx.createShader(type);
      if (!s) return null;
      glCtx.shaderSource(s, src);
      glCtx.compileShader(s);
      if (!glCtx.getShaderParameter(s, glCtx.COMPILE_STATUS)) {
        glCtx.deleteShader(s);
        return null;
      }
      return s;
    }

    const vs = compile(glCtx.VERTEX_SHADER || 35633, vsSource);
    const fs = compile(glCtx.FRAGMENT_SHADER || 35632, fsSource);
    if (!vs || !fs) return null;

    const program = glCtx.createProgram();
    if (!program) return null;
    glCtx.attachShader(program, vs);
    glCtx.attachShader(program, fs);
    glCtx.linkProgram(program);

    if (!glCtx.getProgramParameter(program, glCtx.LINK_STATUS)) {
      glCtx.deleteProgram(program);
      return null;
    }

    const geometry = getStaticGeometry();
    const resources = {
      program,
      vs,
      fs,
      aPosition: glCtx.getAttribLocation(program, 'aPosition'),
      aColor: glCtx.getAttribLocation(program, 'aColor'),
      uMVP: glCtx.getUniformLocation(program, 'uMVP'),
      uTime: glCtx.getUniformLocation(program, 'uTime'),
      coreVertexBuffer: glCtx.createBuffer(),
      coreColorBuffer: glCtx.createBuffer(),
      cageVertexBuffer: glCtx.createBuffer(),
      cageColorBuffer: glCtx.createBuffer()
    };
    const arrayBuffer = glCtx.ARRAY_BUFFER || 34962;
    const staticDraw = glCtx.STATIC_DRAW || 35044;
    for (const [buffer, data] of [
      [resources.coreVertexBuffer, geometry.core.positions],
      [resources.coreColorBuffer, geometry.core.colors],
      [resources.cageVertexBuffer, geometry.cage.positions],
      [resources.cageColorBuffer, geometry.cage.colors]
    ]) {
      if (!buffer) return null;
      glCtx.bindBuffer(arrayBuffer, buffer);
      glCtx.bufferData(arrayBuffer, data, staticDraw);
    }
    return resources;
  }

  // Perspective matrix helper
  function createPerspective(fov, aspect, near, far) {
    const f = 1.0 / Math.tan(fov / 2);
    const nf = 1 / (near - far);
    return [
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far + near) * nf, -1,
      0, 0, (2 * far * near) * nf, 0
    ];
  }

  // 4x4 matrix multiplication
  function multiplyMatrix(a, b) {
    const out = new Array(16).fill(0);
    for (let i = 0; i < 4; i++) {
      for (let j = 0; j < 4; j++) {
        let sum = 0;
        for (let k = 0; k < 4; k++) {
          sum += a[i * 4 + k] * b[k * 4 + j];
        }
        out[i * 4 + j] = sum;
      }
    }
    return out;
  }

  // Model-view transformation matrix
  function createModelViewMatrix(tx, ty, tz, rx, ry, rz) {
    const cx = Math.cos(rx), sx = Math.sin(rx);
    const cy = Math.cos(ry), sy = Math.sin(ry);
    const cz = Math.cos(rz), sz = Math.sin(rz);

    // Rotation XYZ
    const rot = [
      cy * cz,               cy * sz,               -sy,     0,
      sx * sy * cz - cx * sz, sx * sy * sz + cx * cz, sx * cy, 0,
      cx * sy * cz + sx * sz, cx * sy * sz - sx * cz, cx * cy, 0,
      0,                     0,                     0,       1
    ];

    rot[12] = tx;
    rot[13] = ty;
    rot[14] = tz;
    return rot;
  }

  // Render frame via WebGL
  function renderWebGL(t) {
    if (!gl || isContextLost || !glResources) return;

    updateDimensions();
    const width = canvas.width || 300;
    const height = canvas.height || 220;
    const aspect = width / height;

    gl.viewport(0, 0, width, height);
    gl.clearColor(0.0, 0.0, 0.0, 0.0);
    gl.clear((gl.COLOR_BUFFER_BIT || 16384) | (gl.DEPTH_BUFFER_BIT || 256));
    if (gl.enable) {
      gl.enable(gl.DEPTH_TEST || 2929);
      gl.enable(gl.BLEND || 3042);
      gl.blendFunc(gl.SRC_ALPHA || 770, gl.ONE || 1);
    }

    gl.useProgram(glResources.program);
    if (glResources.uTime) {
      gl.uniform1f(glResources.uTime, t);
    }

    const proj = createPerspective(Math.PI / 4, aspect, 0.1, 100.0);

    const geometry = getStaticGeometry();

    const mvCore = createModelViewMatrix(0, 0, -3.2, t * 0.45, t * 0.75, t * 0.25);
    const mvpCore = multiplyMatrix(mvCore, proj);

    if (glResources.uMVP) {
      gl.uniformMatrix4fv(glResources.uMVP, false, new Float32Array(mvpCore));
    }

    gl.bindBuffer(gl.ARRAY_BUFFER || 34962, glResources.coreVertexBuffer);
    gl.enableVertexAttribArray(glResources.aPosition);
    gl.vertexAttribPointer(glResources.aPosition, 3, gl.FLOAT || 5126, false, 0, 0);

    gl.bindBuffer(gl.ARRAY_BUFFER || 34962, glResources.coreColorBuffer);
    gl.enableVertexAttribArray(glResources.aColor);
    gl.vertexAttribPointer(glResources.aColor, 4, gl.FLOAT || 5126, false, 0, 0);

    gl.drawArrays(gl.LINES || 1, 0, geometry.core.positions.length / 3);

    // Outer orbital cage dodecahedron (Electric Cyan)
    const mvCage = createModelViewMatrix(0, 0, -3.2, -t * 0.35, t * 0.4, -t * 0.15);
    const mvpCage = multiplyMatrix(mvCage, proj);

    if (glResources.uMVP) {
      gl.uniformMatrix4fv(glResources.uMVP, false, new Float32Array(mvpCage));
    }

    gl.bindBuffer(gl.ARRAY_BUFFER || 34962, glResources.cageVertexBuffer);
    gl.vertexAttribPointer(glResources.aPosition, 3, gl.FLOAT || 5126, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER || 34962, glResources.cageColorBuffer);
    gl.vertexAttribPointer(glResources.aColor, 4, gl.FLOAT || 5126, false, 0, 0);
    gl.drawArrays(gl.LINES || 1, 0, geometry.cage.positions.length / 3);
  }

  // Render frame via 2D Canvas Fallback
  function renderCanvas2D(t) {
    if (!ctx2d) return;

    const width = canvas.width || 300;
    const height = canvas.height || 220;
    const cx = width / 2;
    const cy = height / 2;
    const dpr = getClampedDPR();
    const scale = Math.min(width, height) * 0.38;

    ctx2d.clearRect(0, 0, width, height);
    ctx2d.save();

    // Perspective projection helper
    const fov = 3.2;
    function project(p) {
      const z = p[2] + fov;
      const factor = scale / z;
      return [cx + p[0] * factor, cy + p[1] * factor, z];
    }

    // Outer Cage Dodecahedron (Cyan)
    const geometry = getStaticGeometry().canvas2d;
    const rawCage = geometry.cage;
    const rotCage = rawCage.map(p => rotate3D(p, -t * 0.35, t * 0.4, -t * 0.15));
    const projCage = rotCage.map(project);

    ctx2d.beginPath();
    for (const [i, j] of DODECAHEDRON_EDGES) {
      const p1 = projCage[i];
      const p2 = projCage[j];
      ctx2d.moveTo(p1[0], p1[1]);
      ctx2d.lineTo(p2[0], p2[1]);
    }
    ctx2d.strokeStyle = 'rgba(6, 182, 212, 0.45)';
    ctx2d.lineWidth = 1.2 * dpr;
    ctx2d.stroke();

    // Orbital Rings
    const orbitalRings = geometry.rings;
    ctx2d.strokeStyle = 'rgba(59, 130, 246, 0.25)';
    ctx2d.lineWidth = 1.0 * dpr;
    for (const ring of orbitalRings) {
      const rotRing = ring.map(p => rotate3D(p, t * 0.2, -t * 0.3, t * 0.1));
      const projRing = rotRing.map(project);
      ctx2d.beginPath();
      for (let k = 0; k < projRing.length; k++) {
        if (k === 0) ctx2d.moveTo(projRing[k][0], projRing[k][1]);
        else ctx2d.lineTo(projRing[k][0], projRing[k][1]);
      }
      ctx2d.stroke();
    }

    // Inner Core Icosahedron (Electric Cobalt / Cyan)
    const rawCore = geometry.core;
    const rotCore = rawCore.map(p => rotate3D(p, t * 0.45, t * 0.75, t * 0.25));
    const projCore = rotCore.map(project);

    // Draw Core Edges with Gradient
    ctx2d.beginPath();
    for (const [i, j] of ICOSAHEDRON_EDGES) {
      const p1 = projCore[i];
      const p2 = projCore[j];
      ctx2d.moveTo(p1[0], p1[1]);
      ctx2d.lineTo(p2[0], p2[1]);
    }
    ctx2d.strokeStyle = PALETTE.cobalt;
    ctx2d.lineWidth = 1.8 * dpr;
    ctx2d.stroke();

    // Draw Core Nodes (Glowing Cyan/White Vertices)
    for (let k = 0; k < projCore.length; k++) {
      const p = projCore[k];
      const nodeRadius = (2.8 + Math.sin(t * 3.0 + k) * 0.8) * dpr;

      // Node halo
      ctx2d.beginPath();
      ctx2d.arc(p[0], p[1], nodeRadius * 2.2, 0, Math.PI * 2);
      ctx2d.fillStyle = PALETTE.glow;
      ctx2d.fill();

      // Node core
      ctx2d.beginPath();
      ctx2d.arc(p[0], p[1], nodeRadius, 0, Math.PI * 2);
      ctx2d.fillStyle = PALETTE.cyan;
      ctx2d.fill();
    }

    ctx2d.restore();
  }

  // Unified render dispatch
  function renderFrame(timeSec) {
    if (isWebGL) {
      renderWebGL(timeSec);
    } else {
      renderCanvas2D(timeSec);
    }
  }

  // Animation Loop
  function animate(timestamp) {
    if (!isVisible || isReducedMotion || isContextLost) {
      rafId = null;
      return;
    }

    if (!lastTimestamp) lastTimestamp = timestamp;
    const delta = Math.min((timestamp - lastTimestamp) / 1000, 0.1);
    lastTimestamp = timestamp;
    animationTime += delta;

    renderFrame(animationTime);
    rafId = global.requestAnimationFrame ? global.requestAnimationFrame(animate) : null;
  }

  function startLoop() {
    if (rafId) return;
    if (isReducedMotion) {
      renderFrame(0.5); // Static beauty frame
      return;
    }
    if (isVisible && !isContextLost) {
      lastTimestamp = 0;
      rafId = global.requestAnimationFrame ? global.requestAnimationFrame(animate) : null;
    }
  }

  function stopLoop() {
    if (rafId && global.cancelAnimationFrame) {
      global.cancelAnimationFrame(rafId);
    }
    rafId = null;
  }

  // WebGL Context Lost / Restored Handlers
  function onContextLost(event) {
    if (event && event.preventDefault) {
      event.preventDefault();
    }
    isContextLost = true;
    stopLoop();
  }

  function onContextRestored() {
    isContextLost = false;
    if (gl) {
      glResources = initWebGL(gl);
    }
    if (isVisible && !isReducedMotion) {
      startLoop();
    } else {
      renderFrame(animationTime || 0.5);
    }
  }

  // Reduced motion media query change listener
  function onMotionPreferenceChange(e) {
    isReducedMotion = !!e.matches;
    if (isReducedMotion) {
      stopLoop();
      renderFrame(0.5);
    } else if (isVisible) {
      startLoop();
    }
  }

  // Initialize Hero Scene
  function initHeroScene() {
    const doc = global.document;
    if (!doc) return;

    container = doc.getElementById('hero-canvas-container') || doc.querySelector('.hero-canvas-container');
    canvas = doc.getElementById('hero-canvas') || (container ? container.querySelector('canvas') : null);

    if (!canvas) {
      return;
    }

    // Check prefers-reduced-motion
    if (global.matchMedia) {
      mediaQueryList = global.matchMedia('(prefers-reduced-motion: reduce)');
      isReducedMotion = !!mediaQueryList.matches;
      if (mediaQueryList.addEventListener) {
        mediaQueryList.addEventListener('change', onMotionPreferenceChange);
      } else if (mediaQueryList.addListener) {
        mediaQueryList.addListener(onMotionPreferenceChange);
      }
    }

    // Attempt WebGL context creation with graceful fallback to 2D Canvas
    try {
      gl = canvas.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: false }) ||
           canvas.getContext('experimental-webgl', { alpha: true, antialias: true, premultipliedAlpha: false });
    } catch (_) {
      gl = null;
    }

    if (gl) {
      glResources = initWebGL(gl);
      if (glResources) {
        isWebGL = true;
      } else {
        const replacement = canvas.cloneNode(false);
        if (canvas.parentNode) {
          canvas.parentNode.replaceChild(replacement, canvas);
          canvas = replacement;
        }
        gl = null;
      }
    }

    if (!isWebGL) {
      try {
        ctx2d = canvas.getContext('2d');
      } catch (_) {
        ctx2d = null;
      }
    }

    // Attach WebGL context lifecycle listeners
    if (canvas.addEventListener) {
      canvas.addEventListener('webglcontextlost', onContextLost, false);
      canvas.addEventListener('webglcontextrestored', onContextRestored, false);
    }

    // IntersectionObserver offscreen lifecycle optimization
    const targetElement = container || canvas;
    if (global.IntersectionObserver && targetElement) {
      intersectionObserver = new global.IntersectionObserver((entries) => {
        for (const entry of entries) {
          isVisible = !!entry.isIntersecting;
          if (isVisible) {
            if (!isReducedMotion) {
              startLoop();
            } else {
              renderFrame(0.5);
            }
          } else {
            stopLoop();
          }
        }
      }, { threshold: 0.05 });

      intersectionObserver.observe(targetElement);
    }

    // Resize listener
    if (global.addEventListener) {
      global.addEventListener('resize', updateDimensions, { passive: true });
    }

    updateDimensions();

    // Start or render initial frame
    if (isReducedMotion) {
      renderFrame(0.5);
    } else {
      startLoop();
    }
  }

  // Teardown & Disposal
  function disposeHeroNode() {
    stopLoop();

    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }

    if (mediaQueryList) {
      if (mediaQueryList.removeEventListener) {
        mediaQueryList.removeEventListener('change', onMotionPreferenceChange);
      } else if (mediaQueryList.removeListener) {
        mediaQueryList.removeListener(onMotionPreferenceChange);
      }
      mediaQueryList = null;
    }

    if (global.removeEventListener) {
      global.removeEventListener('resize', updateDimensions);
    }

    if (canvas && canvas.removeEventListener) {
      canvas.removeEventListener('webglcontextlost', onContextLost);
      canvas.removeEventListener('webglcontextrestored', onContextRestored);
    }

    if (gl && glResources) {
      if (gl.deleteProgram && glResources.program) gl.deleteProgram(glResources.program);
      if (gl.deleteShader && glResources.vs) gl.deleteShader(glResources.vs);
      if (gl.deleteShader && glResources.fs) gl.deleteShader(glResources.fs);
      if (gl.deleteBuffer && glResources.coreVertexBuffer) gl.deleteBuffer(glResources.coreVertexBuffer);
      if (gl.deleteBuffer && glResources.coreColorBuffer) gl.deleteBuffer(glResources.coreColorBuffer);
      if (gl.deleteBuffer && glResources.cageVertexBuffer) gl.deleteBuffer(glResources.cageVertexBuffer);
      if (gl.deleteBuffer && glResources.cageColorBuffer) gl.deleteBuffer(glResources.cageColorBuffer);
      glResources = null;
    }

    if (ctx2d && canvas) {
      ctx2d.clearRect(0, 0, canvas.width || 300, canvas.height || 220);
    }

    gl = null;
    ctx2d = null;
    canvas = null;
    container = null;
    isWebGL = false;
    isContextLost = false;
  }

  // Export disposal hook
  global._disposeHeroNode = disposeHeroNode;

  // Auto-initialize when DOM is ready
  const doc = global.document;
  if (doc) {
    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', initHeroScene, { once: true });
    } else {
      initHeroScene();
    }
  }

})(typeof window !== 'undefined' ? window : globalThis);
