/**
 * Graphili — D3.js Force-Directed Code Graph
 *
 * Reads graph JSON from /api/graph, renders an interactive
 * Obsidian-style force graph with pan, zoom, drag, search,
 * click-to-inspect, and directional edge arrows.
 */

(async function () {
  "use strict";

  // ── Design tokens ──────────────────────────────────────────
  const NODE_COLORS = {
    api:      "#10b981",
    function: "#38bdf8",
    class:    "#a78bfa",
    method:   "#fbbf24",
  };

  const NODE_RADII = {
    api:      14,
    class:    12,
    function: 8,
    method:   7,
  };

  const GLOW_COLORS = {
    api:      "rgba(16,185,129,0.5)",
    function: "rgba(56,189,248,0.5)",
    class:    "rgba(167,139,250,0.5)",
    method:   "rgba(251,191,36,0.5)",
  };

  function getRadius(d)  { return NODE_RADII[d.type]  || 8; }
  function getColor(d)   { return NODE_COLORS[d.type]  || "#64748b"; }
  function getGlow(d)    { return GLOW_COLORS[d.type]  || "rgba(100,116,139,0.5)"; }

  // ── Fetch graph data ───────────────────────────────────────
  let data;
  try {
    const res = await fetch("/api/graph");
    data = await res.json();
  } catch (err) {
    document.body.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;
                  color:#94a3b8;font-family:Inter,sans-serif;font-size:16px;">
        Failed to load graph data. Make sure the server is running.
      </div>`;
    return;
  }

  const nodes = data.nodes;
  const links = data.edges;

  // ── Build adjacency maps ───────────────────────────────────
  const outgoing = {};  // nodeId -> [targetId, ...]
  const incoming = {};  // nodeId -> [sourceId, ...]
  const nodeMap  = {};  // nodeId -> node object

  nodes.forEach(n => { nodeMap[n.id] = n; });
  links.forEach(e => {
    const src = typeof e.source === "object" ? e.source.id : e.source;
    const tgt = typeof e.target === "object" ? e.target.id : e.target;
    if (!outgoing[src]) outgoing[src] = [];
    outgoing[src].push(tgt);
    if (!incoming[tgt]) incoming[tgt] = [];
    incoming[tgt].push(src);
  });

  // ── Update stats bar ──────────────────────────────────────
  document.getElementById("stat-nodes").textContent = nodes.length;
  document.getElementById("stat-edges").textContent = links.length;
  document.getElementById("stat-apis").textContent  = nodes.filter(n => n.is_api).length;

  // ── SVG setup ─────────────────────────────────────────────
  const width  = window.innerWidth;
  const height = window.innerHeight;

  const svg = d3.select("#graph-svg")
    .attr("width", width)
    .attr("height", height);

  // ── Defs: arrow markers + glow filters ────────────────────
  const defs = svg.append("defs");

  // Arrow marker (default)
  defs.append("marker")
    .attr("id", "arrowhead")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 10)
    .attr("refY", 0)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto")
    .append("path")
      .attr("d", "M0,-4L10,0L0,4")
      .attr("fill", "#3a3a5c");

  // Highlighted arrow marker
  defs.append("marker")
    .attr("id", "arrowhead-highlight")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 10)
    .attr("refY", 0)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto")
    .append("path")
      .attr("d", "M0,-4L10,0L0,4")
      .attr("fill", "#38bdf8");

  // Glow filter for nodes
  const glowFilter = defs.append("filter")
    .attr("id", "glow")
    .attr("x", "-50%").attr("y", "-50%")
    .attr("width", "200%").attr("height", "200%");
  glowFilter.append("feGaussianBlur")
    .attr("stdDeviation", "3")
    .attr("result", "blur");
  glowFilter.append("feMerge")
    .selectAll("feMergeNode")
    .data(["blur", "SourceGraphic"])
    .join("feMergeNode")
      .attr("in", d => d);

  // ── Main container (zoom/pan target) ──────────────────────
  const g = svg.append("g");

  // ── Zoom behaviour ────────────────────────────────────────
  const zoomBehavior = d3.zoom()
    .scaleExtent([0.05, 6])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });
  svg.call(zoomBehavior);

  // ── Force simulation ──────────────────────────────────────
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(160)
      .strength(0.4))
    .force("charge", d3.forceManyBody()
      .strength(-500)
      .distanceMax(600))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide()
      .radius(d => getRadius(d) + 16)
      .strength(0.7))
    .force("x", d3.forceX(width / 2).strength(0.03))
    .force("y", d3.forceY(height / 2).strength(0.03));

  // ── Draw edges ────────────────────────────────────────────
  const linkGroup = g.append("g").attr("class", "edges");

  const link = linkGroup.selectAll("line")
    .data(links)
    .join("line")
      .attr("class", "edge-line")
      .attr("marker-end", "url(#arrowhead)");

  // ── Draw nodes ────────────────────────────────────────────
  const nodeGroup = g.append("g").attr("class", "nodes");

  const node = nodeGroup.selectAll("g")
    .data(nodes)
    .join("g")
      .attr("class", "node-group")
      .call(drag(simulation))
      .on("click", onNodeClick);

  // Outer glow ring
  node.append("circle")
    .attr("r", d => getRadius(d) + 4)
    .attr("fill", "none")
    .attr("stroke", d => getColor(d))
    .attr("stroke-width", 1)
    .attr("stroke-opacity", 0.15)
    .attr("class", "node-glow-ring");

  // Main circle
  node.append("circle")
    .attr("r", d => getRadius(d))
    .attr("fill", d => getColor(d))
    .attr("class", "node-circle")
    .style("filter", "url(#glow)");

  // Label
  node.append("text")
    .text(d => d.name.length > 22 ? d.name.slice(0, 20) + "…" : d.name)
    .attr("dy", d => getRadius(d) + 16)
    .attr("text-anchor", "middle")
    .attr("class", "node-label");

  // ── Simulation tick ───────────────────────────────────────
  simulation.on("tick", () => {
    link.each(function (d) {
      const dx = d.target.x - d.source.x;
      const dy = d.target.y - d.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const targetR = getRadius(d.target) + 5;
      const sourceR = getRadius(d.source) + 5;

      d3.select(this)
        .attr("x1", d.source.x + (dx / dist) * sourceR)
        .attr("y1", d.source.y + (dy / dist) * sourceR)
        .attr("x2", d.target.x - (dx / dist) * targetR)
        .attr("y2", d.target.y - (dy / dist) * targetR);
    });

    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  // ── Drag behaviour ────────────────────────────────────────
  function drag(sim) {
    return d3.drag()
      .on("start", (event, d) => {
        if (!event.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) sim.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
  }

  // ── Node click → highlight + sidebar ──────────────────────
  let selectedNode = null;

  function onNodeClick(event, d) {
    event.stopPropagation();
    selectedNode = d;
    highlightNode(d);
    openSidebar(d);
  }

  // Click empty space to deselect
  svg.on("click", () => {
    selectedNode = null;
    resetHighlight();
    closeSidebar();
  });

  function highlightNode(d) {
    const connectedIds = new Set();
    connectedIds.add(d.id);
    (outgoing[d.id] || []).forEach(id => connectedIds.add(id));
    (incoming[d.id] || []).forEach(id => connectedIds.add(id));

    // Dim unrelated nodes
    node.select(".node-circle")
      .transition().duration(200)
      .attr("opacity", n => connectedIds.has(n.id) ? 1 : 0.12);
    node.select(".node-glow-ring")
      .transition().duration(200)
      .attr("stroke-opacity", n => connectedIds.has(n.id) ? 0.3 : 0.02);
    node.select(".node-label")
      .transition().duration(200)
      .attr("opacity", n => connectedIds.has(n.id) ? 1 : 0.06);

    // Highlight connected edges
    link
      .transition().duration(200)
      .attr("opacity", e => {
        const src = typeof e.source === "object" ? e.source.id : e.source;
        const tgt = typeof e.target === "object" ? e.target.id : e.target;
        return (src === d.id || tgt === d.id) ? 1 : 0.05;
      })
      .attr("stroke", e => {
        const src = typeof e.source === "object" ? e.source.id : e.source;
        const tgt = typeof e.target === "object" ? e.target.id : e.target;
        return (src === d.id || tgt === d.id) ? "#38bdf8" : "#2a2a45";
      })
      .attr("stroke-width", e => {
        const src = typeof e.source === "object" ? e.source.id : e.source;
        const tgt = typeof e.target === "object" ? e.target.id : e.target;
        return (src === d.id || tgt === d.id) ? 2.2 : 1.2;
      })
      .attr("marker-end", e => {
        const src = typeof e.source === "object" ? e.source.id : e.source;
        const tgt = typeof e.target === "object" ? e.target.id : e.target;
        return (src === d.id || tgt === d.id)
          ? "url(#arrowhead-highlight)"
          : "url(#arrowhead)";
      });
  }

  function resetHighlight() {
    node.select(".node-circle")
      .transition().duration(300)
      .attr("opacity", 1);
    node.select(".node-glow-ring")
      .transition().duration(300)
      .attr("stroke-opacity", 0.15);
    node.select(".node-label")
      .transition().duration(300)
      .attr("opacity", 1);

    link
      .transition().duration(300)
      .attr("opacity", 0.6)
      .attr("stroke", "#2a2a45")
      .attr("stroke-width", 1.2)
      .attr("marker-end", "url(#arrowhead)");
  }

  // ── Search ────────────────────────────────────────────────
  const searchInput = document.getElementById("search-input");

  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();

    if (!query) {
      resetHighlight();
      return;
    }

    const matchIds = new Set();
    nodes.forEach(n => {
      if (n.name.toLowerCase().includes(query) || n.id.toLowerCase().includes(query)) {
        matchIds.add(n.id);
      }
    });

    node.select(".node-circle")
      .transition().duration(200)
      .attr("opacity", n => matchIds.has(n.id) ? 1 : 0.08);
    node.select(".node-glow-ring")
      .transition().duration(200)
      .attr("stroke-opacity", n => matchIds.has(n.id) ? 0.4 : 0.01);
    node.select(".node-label")
      .transition().duration(200)
      .attr("opacity", n => matchIds.has(n.id) ? 1 : 0.04);

    link
      .transition().duration(200)
      .attr("opacity", 0.04);
  });

  // Escape to clear search
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      searchInput.value = "";
      resetHighlight();
      searchInput.blur();
    }
  });

  // ── Sidebar ───────────────────────────────────────────────
  const sidebar      = document.getElementById("sidebar");
  const sidebarName  = document.getElementById("sidebar-name");
  const sidebarId    = document.getElementById("sidebar-id");
  const sidebarBadge = document.getElementById("sidebar-type-badge");
  const sidebarBody  = document.getElementById("sidebar-body");
  const sidebarClose = document.getElementById("sidebar-close");

  sidebarClose.addEventListener("click", (e) => {
    e.stopPropagation();
    closeSidebar();
    selectedNode = null;
    resetHighlight();
  });

  function openSidebar(d) {
    sidebar.classList.add("open");

    // Header
    sidebarName.textContent = d.name;
    sidebarId.textContent   = d.id;
    sidebarBadge.textContent = d.type.toUpperCase();
    sidebarBadge.className   = `type-badge ${d.type}`;

    // Body — build sections
    let html = "";

    // API badge
    if (d.is_api && d.api_method && d.api_route) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-api-badge">
            <span class="sidebar-api-method">${d.api_method}</span>
            ${escapeHtml(d.api_route)}
          </div>
        </div>`;
    }

    // Auto-summary
    html += `
      <div class="sidebar-section">
        <div class="sidebar-section-title">Summary</div>
        <div class="sidebar-summary">${generateSummary(d)}</div>
      </div>`;

    // File location
    html += `
      <div class="sidebar-section">
        <div class="sidebar-section-title">Location</div>
        <span class="sidebar-file-link">${escapeHtml(d.file)} : line ${d.line}</span>
      </div>`;

    // Arguments
    const visibleArgs = (d.args || []).filter(a => a.name !== "self");
    if (visibleArgs.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-section-title">Arguments</div>
          <table class="args-table">
            <tr><th>Name</th><th>Type</th></tr>
            ${visibleArgs.map(a => `
              <tr>
                <td>${escapeHtml(a.name)}</td>
                <td>${a.type ? escapeHtml(a.type) : '<span style="color:var(--text-dim)">any</span>'}</td>
              </tr>`).join("")}
          </table>
        </div>`;
    }

    // Return type
    if (d.return_type) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-section-title">Returns</div>
          <span style="font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--accent-class);">
            ${escapeHtml(d.return_type)}
          </span>
        </div>`;
    }

    // Docstring
    if (d.docstring) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-section-title">Docstring</div>
          <div class="sidebar-summary" style="font-style:italic;">
            ${escapeHtml(d.docstring)}
          </div>
        </div>`;
    }

    // Outgoing edges (calls)
    const out = outgoing[d.id] || [];
    if (out.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-section-title">Calls (${out.length})</div>
          <ul class="edge-list">
            ${out.map(id => `
              <li class="edge-list-item" data-node-id="${escapeHtml(id)}">
                <span class="edge-arrow outgoing">→</span>
                ${escapeHtml(shortName(id))}
              </li>`).join("")}
          </ul>
        </div>`;
    }

    // Incoming edges (called by)
    const inc = incoming[d.id] || [];
    if (inc.length > 0) {
      html += `
        <div class="sidebar-section">
          <div class="sidebar-section-title">Called by (${inc.length})</div>
          <ul class="edge-list">
            ${inc.map(id => `
              <li class="edge-list-item" data-node-id="${escapeHtml(id)}">
                <span class="edge-arrow incoming">←</span>
                ${escapeHtml(shortName(id))}
              </li>`).join("")}
          </ul>
        </div>`;
    }

    sidebarBody.innerHTML = html;

    // Make edge list items clickable → navigate to that node
    sidebarBody.querySelectorAll(".edge-list-item").forEach(el => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const targetId = el.getAttribute("data-node-id");
        const targetNode = nodes.find(n => n.id === targetId);
        if (targetNode) {
          // Pan to node
          const transform = d3.zoomTransform(svg.node());
          const x = transform.applyX(targetNode.x);
          const y = transform.applyY(targetNode.y);
          svg.transition().duration(500).call(
            zoomBehavior.transform,
            d3.zoomIdentity
              .translate(width / 2, height / 2)
              .scale(transform.k)
              .translate(-targetNode.x, -targetNode.y)
          );
          // Select it
          selectedNode = targetNode;
          highlightNode(targetNode);
          openSidebar(targetNode);
        }
      });
    });
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
  }

  // ── Helpers ───────────────────────────────────────────────

  function generateSummary(d) {
    const parts = [];

    // Humanize name
    const humanName = d.name
      .replace(/_/g, " ")
      .replace(/\b\w/g, c => c.toUpperCase());
    parts.push(humanName + ".");

    // Args summary
    const visibleArgs = (d.args || []).filter(a => a.name !== "self");
    if (visibleArgs.length > 0) {
      const argStr = visibleArgs
        .map(a => a.type ? `${a.name} (${a.type})` : a.name)
        .join(", ");
      parts.push(`Takes ${argStr}.`);
    }

    // Return type
    if (d.return_type) {
      parts.push(`Returns ${d.return_type}.`);
    }

    // Calls count
    const out = outgoing[d.id] || [];
    if (out.length > 0) {
      parts.push(`Calls ${out.length} function${out.length > 1 ? "s" : ""}.`);
    }

    // Called by count
    const inc = incoming[d.id] || [];
    if (inc.length > 0) {
      parts.push(`Called by ${inc.length} function${inc.length > 1 ? "s" : ""}.`);
    }

    return parts.join(" ");
  }

  function shortName(id) {
    const parts = id.split(".");
    return parts.length > 1 ? parts.slice(-2).join(".") : id;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;");
  }

  // ── Resize handler ────────────────────────────────────────
  window.addEventListener("resize", () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    svg.attr("width", w).attr("height", h);
    simulation.force("center", d3.forceCenter(w / 2, h / 2));
    simulation.alpha(0.1).restart();
  });

})();
