from flask import Flask, render_template_string
from pyngrok import ngrok
from threading import Thread
import json
import socket
import time

#kill existing ngrok tunnel (if exists) for updating
ngrok.set_auth_token("NGROK-AUTH-TOKEN")
ngrok.kill()
time.sleep(1)

def free_port():
    s = socket.socket(); s.bind(('',0)); p = s.getsockname()[1]; s.close(); return p

PORT = free_port()
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
  <body style="margin:0;overflow:hidden;background:#0a0a0a">
  <canvas id="c"></canvas>
  <div id="info" style="
    position:fixed;
    bottom:16px;
    left:50%;
    transform:translateX(-50%);
    color:#555;
    font-family:monospace;
    font-size:12px;
    text-align:center
  ">
    {{ degrees }} degrees / {{ paths|length }} paths / drag / scroll to zoom
  </div>

  <script>
  const PATHS   = {{ paths|tojson }};
  const DEGREES = {{ degrees }};

  const canvas = document.getElementById('c');
  const ctx    = canvas.getContext('2d');
  let dpr = window.devicePixelRatio || 1;
  let pan = {x:0, y:0}, zoom = 1;
  let dragging = null, dragStart = null, panStart = null;

  //store nodes and edges across all paths in maps
  const nodeMap = {};
  PATHS.forEach(path => {
    path.forEach(title => {
      if (!nodeMap[title]) {
        const isStart = title === PATHS[0][0];
        const isEnd   = title === PATHS[0][PATHS[0].length - 1];
        nodeMap[title] = {
          title: title.replace(/_/g, ' '),
          x: (Math.random() - 0.5) * 400,
          y: (Math.random() - 0.5) * 400,
          vx: 0, vy: 0, fx: 0, fy: 0,
          isEnd: isStart || isEnd
        };
      }
    });
  });

  const edgeSet = new Set();
  const edges   = [];
  PATHS.forEach(path => {
    path.slice(1).forEach((title, i) => {
      const key = path[i] + '|||' + title;
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        edges.push({ a: nodeMap[path[i]], b: nodeMap[title] });
      }
    });
  });

  //NODES array for physics iteration
  const NODES = Object.values(nodeMap);

  function initPositions() {
    const W = window.innerWidth, H = window.innerHeight;
    for (const n of NODES) { n.x += W/2; n.y += H/2; }
  }

  function resize() {
    canvas.width  = window.innerWidth  * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width  = window.innerWidth  + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resize);
  resize();
  initPositions();

  //physics
  const SPRING_LEN = 160, SPRING_K = 0.03, REPULSE_K = 8000, DAMPING = 0.85;

  function physics() {
    for (const n of NODES) { n.fx = 0; n.fy = 0; }

    for (const {a, b} of edges) {
      const dx = b.x-a.x, dy = b.y-a.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 1;
      const f = (dist - SPRING_LEN) * SPRING_K;
      a.fx += dx/dist*f; a.fy += dy/dist*f;
      b.fx -= dx/dist*f; b.fy -= dy/dist*f;
    }

    for (let i = 0; i < NODES.length; i++) {
      for (let j = i+1; j < NODES.length; j++) {
        const a = NODES[i], b = NODES[j];
        const dx = b.x-a.x, dy = b.y-a.y;
        const d2 = Math.max(dx*dx + dy*dy, 1), d = Math.sqrt(d2);
        const f = REPULSE_K / d2;
        a.fx -= dx/d*f; a.fy -= dy/d*f;
        b.fx += dx/d*f; b.fy += dy/d*f;
      }
    }

    for (const n of NODES) {
      if (n === dragging) continue;
      n.vx = (n.vx + n.fx) * DAMPING;
      n.vy = (n.vy + n.fy) * DAMPING;
      const speed = Math.sqrt(n.vx*n.vx + n.vy*n.vy);
      if (speed > 10) { n.vx = n.vx/speed*10; n.vy = n.vy/speed*10; }
      n.x += n.vx;
      n.y += n.vy;
    }
  }

  function draw() {
    const W = window.innerWidth, H = window.innerHeight;
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    ctx.lineWidth = 1.5 / zoom;
    for (const {a, b} of edges) {
      ctx.beginPath();
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(255,180,0,0.35)';
      ctx.stroke();
    }

    for (const n of NODES) {
      const r = n.isEnd ? 28 : 20;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI*2);
      ctx.fillStyle   = n.isEnd ? '#ffb300' : '#2a1f00';
      ctx.strokeStyle = n.isEnd ? '#ffb300' : '#cc8800';
      ctx.lineWidth   = (n.isEnd ? 2 : 1) / zoom;
      ctx.fill(); ctx.stroke();

      ctx.fillStyle = n.isEnd ? '#000' : '#ffb300';
      ctx.font = `bold ${(n.isEnd ? 13 : 11) / zoom}px monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(n.isEnd ? (n.title === PATHS[0][0].replace(/_/g,' ') ? 'A' : 'B') : '', n.x, n.y);

      const label = n.title.length > 24 ? n.title.slice(0, 23) + '…' : n.title;
      ctx.fillStyle = '#998866';
      ctx.font = `${11 / zoom}px monospace`;
      ctx.textBaseline = 'top';
      ctx.fillText(label, n.x, n.y + r + 6/zoom);
    }

    ctx.restore();
  }

  function loop() { physics(); draw(); requestAnimationFrame(loop); }
  loop();

  //interaction
  function toWorld(ex, ey) { return { x: (ex-pan.x)/zoom, y: (ey-pan.y)/zoom }; }

  function hitTest(ex, ey) {
    const w = toWorld(ex, ey);
    for (let i = NODES.length-1; i >= 0; i--) {
      const n = NODES[i], r = n.isEnd ? 28 : 20;
      if ((w.x-n.x)**2 + (w.y-n.y)**2 <= r*r) return n;
    }
    return null;
  }

  canvas.addEventListener('mousedown', e => {
    const n = hitTest(e.offsetX, e.offsetY);
    if (n) { dragging=n; dragStart={mx:e.offsetX,my:e.offsetY,nx:n.x,ny:n.y}; }
    else   { panStart={mx:e.offsetX,my:e.offsetY,px:pan.x,py:pan.y}; }
  });
  canvas.addEventListener('mousemove', e => {
    if (dragging && dragStart) {
      dragging.x = dragStart.nx + (e.offsetX-dragStart.mx)/zoom;
      dragging.y = dragStart.ny + (e.offsetY-dragStart.my)/zoom;
      dragging.vx = 0; dragging.vy = 0;
    } else if (panStart) {
      pan.x = panStart.px + (e.offsetX-panStart.mx);
      pan.y = panStart.py + (e.offsetY-panStart.my);
    }
  });
  canvas.addEventListener('mouseup',    () => { dragging=null; dragStart=null; panStart=null; });
  canvas.addEventListener('mouseleave', () => { dragging=null; dragStart=null; panStart=null; });
  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const f  = e.deltaY < 0 ? 1.1 : 0.9;
    const wx = (e.offsetX-pan.x)/zoom, wy = (e.offsetY-pan.y)/zoom;
    zoom = Math.max(0.05, Math.min(5, zoom*f));
    pan.x = e.offsetX - wx*zoom;
    pan.y = e.offsetY - wy*zoom;
  }, { passive: false });
  </script>
  </body>
</html>
"""

with open("path_result.json", encoding="utf-8") as f:
    path_data = json.load(f)

@app.route("/")
def home():
    return render_template_string(
        HTML,
        paths=path_data["paths"],
        degrees=path_data["degrees"]
    )

#flask's app.run will halt every other script block, so we need to run this in a thread
Thread(target=lambda: app.run(port=PORT, use_reloader=False), daemon=True).start()
url = ngrok.connect(PORT)
print(url)