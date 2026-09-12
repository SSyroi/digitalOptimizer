// AMS Digital Optimizer & Synthesizer Frontend Application

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const verilogEditor = document.getElementById("verilog-editor");
  const exampleSelect = document.getElementById("example-select");
  const virtuosoLibInput = document.getElementById("virtuoso-lib-input");
  const btnSynthesize = document.getElementById("btn-synthesize");
  const drawerToggle = document.getElementById("drawer-toggle");
  const drawerContent = document.getElementById("drawer-content");
  const cellChipsContainer = document.getElementById("cell-chips-container");
  const cellCountBadge = document.getElementById("cell-count-badge");

  // Output Elements
  const metricDffs = document.getElementById("metric-dffs");
  const metricGates = document.getElementById("metric-gates");
  const metricTransistors = document.getElementById("metric-transistors");
  const registersList = document.getElementById("registers-list");
  const outputsList = document.getElementById("outputs-list");
  const codeVeriloga = document.getElementById("code-veriloga");
  const tbodyBom = document.getElementById("tbody-bom");
  const tbodyInstances = document.getElementById("tbody-instances");
  const codeNetlist = document.getElementById("code-netlist");
  const verifCard = document.getElementById("verif-card");
  const verifTitle = document.getElementById("verif-title");
  const verifDesc = document.getElementById("verif-desc");
  const verifDetails = document.getElementById("verif-details");

  // Action Buttons
  const btnCopyEquations = document.getElementById("btn-copy-equations");
  const btnCopyVa = document.getElementById("btn-copy-va");
  const btnDownloadVa = document.getElementById("btn-download-va");
  const btnDownloadBom = document.getElementById("btn-download-bom");
  const btnShowSkill = document.getElementById("btn-show-skill");
  const btnShowSpice = document.getElementById("btn-show-spice");
  const btnDownloadNetlist = document.getElementById("btn-download-netlist");

  let examplesData = {};
  let currentResult = null;
  let currentNetlistView = "skill"; // 'skill' or 'spice'

  // Tab Switching
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // Drawer Toggle
  drawerToggle.addEventListener("click", () => {
    const isHidden = drawerContent.style.display === "none";
    drawerContent.style.display = isHidden ? "block" : "none";
    drawerToggle.querySelector(".drawer-arrow").textContent = isHidden ? "▼" : "▲";
  });

  // Load Library & Examples on Startup
  async function init() {
    try {
      const [libRes, exRes] = await Promise.all([
        fetch("/api/library").then((r) => r.json()),
        fetch("/api/examples").then((r) => r.json()),
      ]);

      // Render Library Cells
      renderLibraryChips(libRes);

      // Render Examples Dropdown
      examplesData = exRes;
      exampleSelect.innerHTML = '<option value="">-- Choose Example --</option>';
      Object.keys(examplesData).forEach((fname) => {
        const opt = document.createElement("option");
        opt.value = fname;
        opt.textContent = formatExampleName(fname);
        exampleSelect.appendChild(opt);
      });

      // Default load first example if available
      const exampleKeys = Object.keys(examplesData);
      if (exampleKeys.length > 0) {
        exampleSelect.value = exampleKeys[0];
        verilogEditor.value = examplesData[exampleKeys[0]];
        // Trigger initial synthesis
        runSynthesis();
      }
    } catch (err) {
      console.error("Failed to load initial data:", err);
    }
  }

  function formatExampleName(fname) {
    if (fname === "gray_counter.v") return "3-bit Gray Counter (Glitch-Free)";
    if (fname === "sar_adc_ctrl.v") return "4-bit SAR ADC Logic Controller";
    if (fname === "bandgap_trim_fsm.v") return "Bandgap Trimming FSM";
    if (fname === "clock_divider_rst.v") return "Clock Divider with Reset";
    return fname;
  }

  function renderLibraryChips(lib) {
    const cells = lib.cells || {};
    cellCountBadge.textContent = Object.keys(cells).length;
    cellChipsContainer.innerHTML = "";

    Object.values(cells).forEach((c) => {
      const chip = document.createElement("div");
      chip.className = "cell-chip";
      chip.innerHTML = `
        <strong>${c.name}</strong>
        <span class="chip-cost">(${c.cost}T)</span>
      `;
      chip.title = `${c.name}: ${c.function || c.cell_type}`;
      cellChipsContainer.appendChild(chip);
    });
  }

  // Example Selection Handler
  exampleSelect.addEventListener("change", () => {
    const selected = exampleSelect.value;
    if (selected && examplesData[selected]) {
      verilogEditor.value = examplesData[selected];
      runSynthesis();
    }
  });

  // Run Synthesis Handler
  async function runSynthesis() {
    const code = verilogEditor.value.trim();
    if (!code) {
      alert("Please enter behavioral Verilog code.");
      return;
    }

    btnSynthesize.disabled = true;
    btnSynthesize.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
        <line x1="12" y1="2" x2="12" y2="6"></line>
        <line x1="12" y1="18" x2="12" y2="22"></line>
        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
        <line x1="2" y1="12" x2="6" y2="12"></line>
        <line x1="18" y1="12" x2="22" y2="12"></line>
        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
      </svg>
      <span>Optimizing...</span>
    `;

    try {
      const res = await fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verilog_code: code,
          virtuoso_lib: virtuosoLibInput.value.trim() || "MY_AMS_LIB",
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Synthesis failed");
      }

      currentResult = await res.json();
      displayResults(currentResult);
    } catch (err) {
      alert("Error: " + err.message);
      console.error(err);
    } finally {
      btnSynthesize.disabled = false;
      btnSynthesize.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span>Synthesize & Optimize</span>
      `;
    }
  }

  btnSynthesize.addEventListener("click", runSynthesis);

  // Keyboard shortcut Ctrl+Enter / Cmd+Enter
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      runSynthesis();
    }
  });

  // Display Results Function
  function displayResults(data) {
    // 1. Metrics
    const dffCount = data.registers.length;
    metricDffs.textContent = dffCount;
    metricGates.textContent = data.total_gates;
    metricTransistors.textContent = `~${data.total_transistors}`;

    // 2. Nested Gate Equations
    renderEquationCards(data.registers, registersList, "DFF D-Input");
    renderEquationCards(data.outputs, outputsList, "Combinational Out");

    // 3. Verilog-A Code
    codeVeriloga.textContent = data.veriloga_code;

    // 4. BOM Table
    tbodyBom.innerHTML = "";
    data.bom.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong style="color: var(--primary-light)">${row.cell_name}</strong></td>
        <td>${row.category}</td>
        <td>${row.count}</td>
        <td>~${row.transistors_per_cell}</td>
        <td><strong style="color: var(--accent-emerald)">~${row.total_transistors}</strong></td>
      `;
      tbodyBom.appendChild(tr);
    });
    // Add Total Row
    const trTot = document.createElement("tr");
    trTot.style.fontWeight = "700";
    trTot.style.backgroundColor = "rgba(255,255,255,0.03)";
    trTot.innerHTML = `
      <td>TOTAL</td>
      <td>-</td>
      <td>${data.total_gates} instances</td>
      <td>-</td>
      <td>~${data.total_transistors}</td>
    `;
    tbodyBom.appendChild(trTot);

    // 5. Instance Wiring Table
    tbodyInstances.innerHTML = "";
    data.instances.forEach((inst) => {
      const tr = document.createElement("tr");
      const conns = Object.entries(inst.connections)
        .map(([p, n]) => `<strong>${p}</strong> &rarr; <code>${n}</code>`)
        .join(", ");
      tr.innerHTML = `
        <td><code>${inst.name}</code></td>
        <td><strong style="color: var(--primary-light)">${inst.cell}</strong></td>
        <td>${conns}</td>
      `;
      tbodyInstances.appendChild(tr);
    });

    // 6. Netlist Subtabs (SKILL vs SPICE)
    updateNetlistView();

    // 7. Formal Verification Card
    const v = data.verification;
    if (v && v.is_equivalent) {
      verifCard.className = "verif-result-card status-passed";
      verifTitle.textContent = "Formal Equivalence Verified: 100% Match";
      verifDesc.textContent = v.message;
      verifDetails.innerHTML = `
        <div class="verif-stat-box">
          <div class="verif-stat-label">Verified Signals</div>
          <div class="verif-stat-value">${v.signals_count}</div>
        </div>
        <div class="verif-stat-box">
          <div class="verif-stat-label">State Pattern Evaluations</div>
          <div class="verif-stat-value">${v.patterns_count}</div>
        </div>
        <div class="verif-stat-box">
          <div class="verif-stat-label">Logic Mismatches</div>
          <div class="verif-stat-value" style="color: var(--accent-emerald)">0</div>
        </div>
      `;
    } else {
      verifCard.className = "verif-result-card status-failed";
      verifTitle.textContent = "Formal Equivalence Check Failed";
      verifDesc.textContent = v ? v.message : "Mismatches detected";
      verifDetails.innerHTML = (v && v.mismatches ? v.mismatches.map((m) => `<div style="color: var(--accent-rose); font-family: var(--font-mono); font-size: 0.8rem;">${m}</div>`).join("") : "");
    }
  }

  function renderEquationCards(items, container, defaultType) {
    if (!items || items.length === 0) {
      container.innerHTML = `<p class="placeholder-text">None found in design.</p>`;
      return;
    }
    container.innerHTML = "";
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "equation-card";
      card.innerHTML = `
        <div class="card-header">
          <span class="card-target">${item.target}</span>
          <span class="card-type-tag">${item.type || defaultType}</span>
        </div>
        <div class="card-formula">${highlightFormula(item.expr)}</div>
      `;
      container.appendChild(card);
    });
  }

  function highlightFormula(expr) {
    // Highlight gate function calls like NAND2, NOR3, MUX2 with colored tags
    return expr.replace(/\b([A-Z0-9_]+)\s*\(/g, '<strong style="color: #6ee7b7">$1</strong>(');
  }

  function updateNetlistView() {
    if (!currentResult) return;
    if (currentNetlistView === "skill") {
      codeNetlist.textContent = currentResult.skill_script;
      btnShowSkill.classList.add("active");
      btnShowSpice.classList.remove("active");
    } else {
      codeNetlist.textContent = currentResult.spice_netlist;
      btnShowSpice.classList.add("active");
      btnShowSkill.classList.remove("active");
    }
  }

  btnShowSkill.addEventListener("click", () => {
    currentNetlistView = "skill";
    updateNetlistView();
  });

  btnShowSpice.addEventListener("click", () => {
    currentNetlistView = "spice";
    updateNetlistView();
  });

  // Copy & Download Handlers
  btnCopyEquations.addEventListener("click", () => {
    if (!currentResult) return;
    const lines = [];
    currentResult.registers.forEach((r) => lines.push(`${r.target} = ${r.expr};`));
    currentResult.outputs.forEach((o) => lines.push(`${o.target} = ${o.expr};`));
    navigator.clipboard.writeText(lines.join("\n"));
    showCopied(btnCopyEquations, "Copied Formulas!");
  });

  btnCopyVa.addEventListener("click", () => {
    if (!currentResult) return;
    navigator.clipboard.writeText(currentResult.veriloga_code);
    showCopied(btnCopyVa, "Copied Verilog-A!");
  });

  btnDownloadVa.addEventListener("click", () => {
    if (!currentResult) return;
    downloadFile(`${currentResult.module_name || "ams_block"}_va.va`, currentResult.veriloga_code);
  });

  btnDownloadBom.addEventListener("click", () => {
    if (!currentResult) return;
    downloadFile(`${currentResult.module_name || "ams_block"}_schematic_guide.md`, currentResult.schematic_report);
  });

  btnDownloadNetlist.addEventListener("click", () => {
    if (!currentResult) return;
    if (currentNetlistView === "skill") {
      downloadFile(`${currentResult.module_name || "ams_block"}.il`, currentResult.skill_script);
    } else {
      downloadFile(`${currentResult.module_name || "ams_block"}.sp`, currentResult.spice_netlist);
    }
  });

  function showCopied(btn, text) {
    const orig = btn.textContent;
    btn.textContent = text;
    setTimeout(() => (btn.textContent = orig), 1500);
  }

  function downloadFile(filename, content) {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  init();
});
