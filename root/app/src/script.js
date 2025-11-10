(async () => {
  const el = {
    msg: document.getElementById("msg"),
    tokenStatus: document.getElementById("tokenStatus"),
    currentUser: document.getElementById("currentUser"),
    envList: document.getElementById("envList"),
    authorizeBtn: document.getElementById("authorizeBtn"),
    fetchConfigBtn: document.getElementById("fetchConfigBtn"),
    createStatusBtn: document.getElementById("createStatusBtn"),
    createFieldsBtn: document.getElementById("createFieldsBtn"),
    createCategoriesBtn: document.getElementById("createCategoriesBtn"),
    categorySummary: document.getElementById("categorySummary"),
    categoryTree: document.getElementById("categoryTree"),
    statusSetsHost: document.getElementById("StatusSets"),
    customFieldsHost: document.getElementById("CustomFields"),
    fetchAssetsInfo: document.getElementById("fetchAssetsInfo"),
  };

  function setMsg(text) {
    if (!text) { el.msg.hidden = true; el.msg.textContent = ""; return; }
    el.msg.hidden = false;
    el.msg.textContent = text;
  }

  function renderEnv(env) {
    el.envList.innerHTML = "";
    Object.entries(env || {}).forEach(([k, v]) => {
      const li = document.createElement("li");
      li.textContent = `${k}: ${v}`;
      el.envList.appendChild(li);
    });
  }

  function renderTokenStatus(tok) {
    if (!tok) { el.tokenStatus.textContent = "Token: unknown"; return; }
    const base = `Token: ${tok.valid ? "VALID" : "MISSING/EXPIRED"}`;
    const extra = tok.expiresAt ? ` — expires at ${tok.expiresAt}${tok.expiresInMinutes != null ? ` (~${tok.expiresInMinutes} min)` : ""}` : "";
    el.tokenStatus.textContent = base + extra;
  }

  function buildTreeUL(nodes) {
    const ul = document.createElement("ul");
    ul.className = "tree";
    (nodes || []).forEach(n => {
      const li = document.createElement("li");
      const label = document.createElement("div");
      label.innerHTML = `<strong>${n.categoryName || "(unnamed)"}</strong>` +
        (n.statusSetName ? ` — Status Set: ${n.statusSetName}` : "");
      li.appendChild(label);
      if (n.children && n.children.length) {
        li.appendChild(buildTreeUL(n.children));
      }
      ul.appendChild(li);
    });
    return ul;
  }

  async function loadStatus() {
    try {
      const res = await fetch("/api/status", { credentials: "include" });
      const data = await res.json();
      setMsg(data.message);
      renderTokenStatus(data.token);
      el.currentUser.textContent = data.user || "-";
      renderEnv(data.env);
    } catch (e) {
      console.error("Status load failed:", e);
      setMsg("Failed to load status.");
    }
  }

  async function loadCategories() {
    try {
      const res = await fetch("/api/categories", { credentials: "include" });
      const data = await res.json();
      el.categorySummary.textContent = data.count ? `${data.count} categories loaded.` : "No categories loaded. Click 'Fetch Assets Config'.";
      el.categoryTree.innerHTML = "";
      if (data.tree && data.tree.length) {
        el.categoryTree.appendChild(buildTreeUL(data.tree));
      }
    } catch (e) {
      console.error("Categories load failed:", e);
      el.categorySummary.textContent = "Failed to load categories.";
    }
  }

  // CSV previews
  async function renderStatusSetsPreview() {
    try {
      const res = await fetch("/api/preview/status_sets", { credentials: "include" });
      if (!res.ok) {
        el.statusSetsHost.textContent = "Failed to load status sets CSV.";
        return;
      }
      const { items = [] } = await res.json();
      console.log("Status Sets Preview Items:", items);
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      const table = document.createElement("table");
      table.className = "table";
      table.innerHTML = `
        <thead>
          <tr>
            <th style="width:15%">Status Set Name</th>
            <th style="width:15%">Status Set ID</th>
            <th>Statuses (label — description - id)</th>
          </tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");
      items.forEach(item => {
        const tr = document.createElement("tr");
        const td = txt => { const d = document.createElement("td"); d.textContent = txt; return d; };
        const list = document.createElement("ul");
        list.className = "small";
        (item.statuses || []).forEach(s => {
          const li = document.createElement("li");
          const bits = [s.label || "", s.description || "", s.statusId || ""].filter(Boolean).join(" — ");
          li.textContent = bits;
          list.appendChild(li);
        });
        tr.appendChild(td(item.name || ""));
        tr.appendChild(td(item.statusSetId || ""));
        const tdList = document.createElement("td"); tdList.appendChild(list); tr.appendChild(tdList);
        tbody.appendChild(tr);
      });
      wrap.appendChild(table);
      el.statusSetsHost.innerHTML = "";
      el.statusSetsHost.appendChild(wrap);
    } catch (e) {
      console.error(e);
      el.statusSetsHost.textContent = "Error rendering status sets preview.";
    }
  }

  async function renderCustomFieldsPreview() {
    try {
      const res = await fetch("/api/preview/custom_fields", { credentials: "include" });
      if (!res.ok) {
        el.customFieldsHost.textContent = "Failed to load custom fields CSV.";
        return;
      }
      const { items = [] } = await res.json();
      console.log("Custom Fields Preview Items:", items);
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      const table = document.createElement("table");
      table.className = "table";
      table.innerHTML = `
        <thead>
          <tr>
            <th style="width:15%">Display Name</th>
            <th style="width:6%">Type</th>
            <th style="width:6%">Required</th>
            <th style="width:45%">Enum Values</th>
            <th style="width:28%">Description</th>
          </tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");
      items.forEach(item => {
        const tr = document.createElement("tr");
        const td = txt => { const d = document.createElement("td"); d.textContent = txt; return d; };
        const enumText = Array.isArray(item.enumValues)
          ? item.enumValues.map(ev => ev.label + (ev.id ? ` (${ev.id})` : "")).join(", ")
          : "";
        tr.appendChild(td(item.displayName || ""));
        tr.appendChild(td(item.dataType || ""));
        tr.appendChild(td(item.requiredOnIngress ? "Yes" : "No"));
        tr.appendChild(td(enumText));
        tr.appendChild(td(item.description || ""));
        tbody.appendChild(tr);
      });
      wrap.appendChild(table);
      el.customFieldsHost.innerHTML = "";
      el.customFieldsHost.appendChild(wrap);
    } catch (e) {
      console.error(e);
      el.customFieldsHost.textContent = "Error rendering custom fields preview.";
    }
  }

  // Button handlers
  el.authorizeBtn?.addEventListener("click", () => {
    window.open("/authorize", "_blank", "noopener");
  });

  el.fetchConfigBtn?.addEventListener("click", async () => {
    window.location.href = "/fetch_assets_config";
  });

  el.fetchAssetsInfo?.addEventListener("click", async () => {
    window.location.href = "/fetch_all_assets_info";
  });

  el.createCategoriesBtn?.addEventListener("click", async () => {
    try {
      const payloadRes = await fetch("/api/payload/categories", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        setMsg(`Failed to load categories JSON: ${t}`);
        return;
      }
      const payload = await payloadRes.json();
      const resp = await fetch("/create_categories_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (resp.redirected) { window.location.href = resp.url; return; }
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setMsg(`Created categories${data.created != null ? `: ${data.created}` : ""}.`);
        await loadCategories();
      } else {
        const text = await resp.text();
        setMsg(`Failed: ${text}`);
      }
    } catch (e) {
      console.error(e);
      setMsg("Failed creating categories. Check console.");
    }
  });

  // Creation buttons: fetch JSON directly from server-side files via payload APIs, then post as body
  el.createStatusBtn?.addEventListener("click", async () => {
    try {
      const payloadRes = await fetch("/api/payload/status_sets", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        setMsg(`Failed to load status sets JSON: ${t}`);
        return;
      }
      const payload = await payloadRes.json();
      console.log("Creating status sets with payload:", payload);
      // Post to creation endpoint
      const resp = await fetch("/create_status_sets_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (resp.redirected) { window.location.href = resp.url; return; }
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setMsg(`Created status sets${data.created != null ? `: ${data.created}` : ""}.`);
        await renderStatusSetsPreview();
        await loadCategories();
      } else {
        const text = await resp.text();
        setMsg(`Failed: ${text}`);
      }
    } catch (e) {
      console.error(e);
      setMsg("Failed creating status sets. Check console.");
    }
  });

  el.createFieldsBtn?.addEventListener("click", async () => {
    try {
      const payloadRes = await fetch("/api/payload/custom_fields", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        setMsg(`Failed to load custom fields JSON: ${t}`);
        return;
      }
      const payload = await payloadRes.json();
      console.log("Creating custom fields with payload:", payload);
      const resp = await fetch("/create_custom_fields_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (resp.redirected) { window.location.href = resp.url; return; }
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setMsg(`Created custom fields${data.created != null ? `: ${data.created}` : ""}.`);
        await renderCustomFieldsPreview();
      } else {
        const text = await resp.text();
        setMsg(`Failed: ${text}`);
      }
    } catch (e) {
      console.error(e);
      setMsg("Failed creating custom fields. Check console.");
    }
  });

  // Handle Update Asset Status form
  document.getElementById("updateAssetForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const assetGuid = document.getElementById("assetGuid")?.value.trim();
    const assetStatus = document.getElementById("assetStatus")?.value.trim();
    if (!assetGuid || !assetStatus) {
      setMsg("Asset GUID and New Status are required.");
      return;
    }
    try {
      const resp = await fetch("/update_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ asset_guid: assetGuid, status_value: assetStatus }),
      });
      const text = await resp.text();
      if (resp.ok) {
        setMsg("Asset status update submitted successfully.");
        console.log("Update status response:", text);
        // Optionally refresh categories or other UI
        // await loadCategories();
      } else {
        setMsg(`Failed to update asset status: ${text}`);
      }
    } catch (err) {
      console.error(err);
      setMsg("Failed to update asset status. Check console.");
    }
  });

  // Initial load
  await loadStatus();
  await loadCategories();
  await renderStatusSetsPreview();
  await renderCustomFieldsPreview();
})();