(async () => {
  const el = {
    tokenStatus: document.getElementById("tokenStatus"),
    envList: document.getElementById("envList"),
    envPanel: document.getElementById("envPanel"),
    toggleEnvBtn: document.getElementById("toggleEnvBtn"),
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
    toastContainer: document.getElementById("toastContainer"),
    statusSetsLoading: document.getElementById("statusSetsLoading"),
    customFieldsLoading: document.getElementById("customFieldsLoading"),
    categoriesLoading: document.getElementById("categoriesLoading"),
  };

  // Toast notification system
  function showToast(type, title, message = '', duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `forge-toast toast-${type}`;
    
    const icons = {
      success: '<path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>',
      error: '<path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>',
      warning: '<path d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"/>'
    };
    
    const escapeHtml = (text) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };
    
    toast.innerHTML = `
      <svg viewBox="0 0 20 20" fill="currentColor">
        ${icons[type] || icons.error}
      </svg>
      <div class="forge-toast-content">
        <div class="forge-toast-title">${escapeHtml(title)}</div>
        ${message ? `<div class="forge-toast-message">${escapeHtml(message)}</div>` : ''}
      </div>
      <button class="forge-toast-close" aria-label="Close">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>
        </svg>
      </button>
    `;
    
    const closeBtn = toast.querySelector('.forge-toast-close');
    closeBtn.addEventListener('click', () => {
      toast.style.animation = 'slideOut 0.3s ease-in';
      setTimeout(() => toast.remove(), 300);
    });
    
    el.toastContainer.appendChild(toast);
    
    if (duration > 0) {
      setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  }

  // Add slideOut animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideOut {
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);

  function showLoading(container) {
    if (container) container.hidden = false;
  }

  function hideLoading(container) {
    if (container) container.hidden = true;
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
    if (!tok) { el.tokenStatus.textContent = "Unknown"; return; }
    const base = `${tok.valid ? "VALID" : "MISSING/EXPIRED"}`;
    const extra = tok.expiresAt ? ` — Expires: ${tok.expiresAt}${tok.expiresInMinutes != null ? ` (~${tok.expiresInMinutes} min)` : ""}` : "";
    el.tokenStatus.textContent = base + extra;
  }

  function buildTreeUL(nodes) {
    const container = document.createElement("div");
    
    (nodes || []).forEach(node => {
      const nodeDiv = buildCategoryNode(node);
      container.appendChild(nodeDiv);
    });
    
    return container;
  }

  function buildCategoryNode(node) {
    const nodeDiv = document.createElement("div");
    nodeDiv.className = "category-node";
    
    const card = document.createElement("div");
    card.className = "category-card";
    
    // Header with icon, name, and ID
    const header = document.createElement("div");
    header.className = "category-card-header";
    
    const icon = document.createElement("div");
    icon.className = "category-icon";
    icon.innerHTML = `
      <svg viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 4a1 1 0 011-1h10a1 1 0 011 1v8a1 1 0 01-1 1H3a1 1 0 01-1-1V4zm2 1v6h8V5H4z"/>
      </svg>
    `;
    
    const name = document.createElement("div");
    name.className = "category-name";
    name.textContent = node.categoryName || "(Unnamed Category)";
    
    const id = document.createElement("div");
    id.className = "category-id";
    id.textContent = `ID: ${node.categoryId || 'N/A'}`;
    
    header.appendChild(icon);
    header.appendChild(name);
    header.appendChild(id);
    
    // Details section
    const details = document.createElement("div");
    details.className = "category-details";
    
    // Status Set
    const statusSet = document.createElement("div");
    statusSet.className = "category-status-set";
    statusSet.innerHTML = `
      <svg viewBox="0 0 16 16" fill="currentColor">
        <circle cx="8" cy="8" r="6"/>
      </svg>
      <span class="${node.statusSetName && node.statusSetName !== 'No Status Set (system)' ? 'status-badge' : 'no-status-badge'}">
        ${node.statusSetName || 'No Status Set'}
      </span>
    `;
    
    details.appendChild(statusSet);
    
    // Custom Attributes - display inline, no tooltip
    if (node.customAttributes && node.customAttributes.length > 0) {
      const attrsContainer = document.createElement("div");
      attrsContainer.className = "category-attributes-inline";
      
      node.customAttributes.forEach(attr => {
        const tag = document.createElement("span");
        tag.className = "attribute-tag";
        tag.textContent = attr;
        attrsContainer.appendChild(tag);
      });
      
      details.appendChild(attrsContainer);
    }
    
    card.appendChild(header);
    card.appendChild(details);
    nodeDiv.appendChild(card);
    
    // Render children recursively
    if (node.children && node.children.length > 0) {
      const childrenContainer = document.createElement("div");
      childrenContainer.className = "category-children";
      
      node.children.forEach(child => {
        childrenContainer.appendChild(buildCategoryNode(child));
      });
      
      nodeDiv.appendChild(childrenContainer);
    }
    
    return nodeDiv;
  }

  async function loadCategories() {
    try {
      showLoading(el.categoriesLoading);
      const res = await fetch("/api/categories", { credentials: "include" });
      const data = await res.json();
      
      el.categorySummary.textContent = data.count 
        ? `${data.count} ${data.count === 1 ? 'category' : 'categories'} loaded.` 
        : "No categories found. Please ensure categories.csv exists in the output folder.";
      
      el.categoryTree.innerHTML = "";
      
      if (data.tree && data.tree.length > 0) {
        el.categoryTree.appendChild(buildTreeUL(data.tree));
      } else if (data.count > 0) {
        // Has categories but no tree structure
        el.categoryTree.innerHTML = `
          <div class="category-empty">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
            </svg>
            <p>Categories loaded but hierarchy structure is not available</p>
          </div>
        `;
      } else {
        el.categoryTree.innerHTML = `
          <div class="category-empty">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
            </svg>
            <p>No categories found. Click 'Fetch Assets Config' to populate data.</p>
          </div>
        `;
      }
    } catch (e) {
      console.error("Categories load failed:", e);
      showToast('error', 'Failed to load categories', e.message);
      el.categorySummary.textContent = "Failed to load categories.";
      el.categoryTree.innerHTML = `
        <div class="category-empty">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
          </svg>
          <p>Error loading categories: ${e.message}</p>
        </div>
      `;
    } finally {
      hideLoading(el.categoriesLoading);
    }
  }

  async function loadStatus() {
    try {
      const res = await fetch("/api/status", { credentials: "include" });
      const data = await res.json();
      renderTokenStatus(data.token);
      renderEnv(data.env);
    } catch (e) {
      console.error("Status load failed:", e);
      showToast('error', 'Failed to load status', e.message);
    }
  }

  // Toggle environment panel
  el.toggleEnvBtn?.addEventListener("click", () => {
    el.envPanel.hidden = !el.envPanel.hidden;
  });

  // CSV previews
  async function renderStatusSetsPreview() {
    try {
      showLoading(el.statusSetsLoading);
      const res = await fetch("/api/preview/status_sets", { credentials: "include" });
      if (!res.ok) {
        el.statusSetsHost.textContent = "Failed to load status sets CSV.";
        return;
      }
      const { items = [] } = await res.json();
      console.log("Status Sets Preview Items:", items);
      
      if (items.length === 0) {
        el.statusSetsHost.innerHTML = '<p class="text-muted">No status sets found. Click "Fetch Assets Config" to load.</p>';
        return;
      }
      
      const wrap = document.createElement("div");
      wrap.className = "forge-table-wrapper";
      const table = document.createElement("table");
      table.className = "forge-table";
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
      showToast('error', 'Failed to render status sets', e.message);
      el.statusSetsHost.textContent = "Error rendering status sets preview.";
    } finally {
      hideLoading(el.statusSetsLoading);
    }
  }

  async function renderCustomFieldsPreview() {
    try {
      showLoading(el.customFieldsLoading);
      const res = await fetch("/api/preview/custom_fields", { credentials: "include" });
      if (!res.ok) {
        el.customFieldsHost.textContent = "Failed to load custom fields CSV.";
        return;
      }
      const { items = [] } = await res.json();
      console.log("Custom Fields Preview Items:", items);
      
      if (items.length === 0) {
        el.customFieldsHost.innerHTML = '<p class="text-muted">No custom fields found. Click "Fetch Assets Config" to load.</p>';
        return;
      }
      
      const wrap = document.createElement("div");
      wrap.className = "forge-table-wrapper";
      const table = document.createElement("table");
      table.className = "forge-table";
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
      showToast('error', 'Failed to render custom fields', e.message);
      el.customFieldsHost.textContent = "Error rendering custom fields preview.";
    } finally {
      hideLoading(el.customFieldsLoading);
    }
  }

  // Button handlers
  el.authorizeBtn?.addEventListener("click", () => {
    window.open("/authorize", "_blank", "noopener");
    showToast('warning', 'Authorization', 'OAuth window opened. Please complete login.', 0);
  });

  el.fetchConfigBtn?.addEventListener("click", async () => {
    showToast('warning', 'Fetching configuration', 'This will reload the page...', 3000);
    setTimeout(() => {
      window.location.href = "/fetch_assets_config";
    }, 500);
  });

  el.fetchAssetsInfo?.addEventListener("click", async () => {
    showToast('warning', 'Fetching all assets', 'This will reload the page...', 3000);
    setTimeout(() => {
      window.location.href = "/fetch_all_assets_info";
    }, 500);
  });

  el.createCategoriesBtn?.addEventListener("click", async () => {
    try {
      showLoading(el.categoriesLoading);
      const payloadRes = await fetch("/api/payload/categories", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        showToast('error', 'Failed to load categories JSON', t);
        return;
      }
      const payload = await payloadRes.json();
      console.log('Creating categories with payload:', payload);
      
      const resp = await fetch("/create_categories_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (resp.redirected) { window.location.href = resp.url; return; }
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        showToast('success', 'Categories created', `${data.created || 'Unknown'} categories created successfully.`);
        await loadCategories();
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create categories', text);
      }
    } catch (e) {
      console.error(e);
      showToast('error', 'Failed creating categories', e.message);
    } finally {
      hideLoading(el.categoriesLoading);
    }
  });

  // Creation buttons: fetch JSON directly from server-side files via payload APIs, then post as body
  el.createStatusBtn?.addEventListener("click", async () => {
    try {
      showLoading(el.statusSetsLoading);
      const payloadRes = await fetch("/api/payload/status_sets", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        showToast('error', 'Failed to load status sets JSON', t);
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
        showToast('success', 'Status sets created', `${data.created || 'Unknown'} status sets created successfully.`);
        await renderStatusSetsPreview();
        await loadCategories();
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create status sets', text);
      }
    } catch (e) {
      console.error(e);
      showToast('error', 'Failed creating status sets', e.message);
    } finally {
      hideLoading(el.statusSetsLoading);
    }
  });

  el.createFieldsBtn?.addEventListener("click", async () => {
    try {
      showLoading(el.customFieldsLoading);
      const payloadRes = await fetch("/api/payload/custom_fields", { credentials: "include" });
      if (!payloadRes.ok) {
        const t = await payloadRes.text();
        showToast('error', 'Failed to load custom fields JSON', t);
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
        showToast('success', 'Custom fields created', `${data.created || 'Unknown'} custom fields created successfully.`);
        await renderCustomFieldsPreview();
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create custom fields', text);
      }
    } catch (e) {
      console.error(e);
      showToast('error', 'Failed creating custom fields', e.message);
    } finally {
      hideLoading(el.customFieldsLoading);
    }
  });

  // Handle Update Asset Status form
  document.getElementById("updateAssetForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const assetGuid = document.getElementById("assetGuid")?.value.trim();
    const assetStatus = document.getElementById("assetStatus")?.value.trim();
    if (!assetGuid || !assetStatus) {
      showToast('error', 'Validation error', 'Both Asset GUID and New Status are required.');
      return;
    }
    try {
      console.log('Updating asset:', { asset_guid: assetGuid, status_value: assetStatus });
      
      const resp = await fetch("/update_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ asset_guid: assetGuid, status_value: assetStatus }),
      });
      const text = await resp.text();
      if (resp.ok) {
        showToast('success', 'Asset updated', 'Asset status updated successfully.');
        console.log("Update status response:", text);
        document.getElementById("updateAssetForm").reset();
      } else {
        showToast('error', 'Update failed', text);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Update failed', err.message);
    }
  });

  // Tab switching
  document.querySelectorAll('.forge-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      
      // Update tab buttons
      document.querySelectorAll('.forge-tab').forEach(t => {
        if (t === tab) {
          t.classList.add('active');
          t.setAttribute('aria-selected', 'true');
        } else {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        }
      });
      
      // Update tab panels
      document.querySelectorAll('.forge-tab-panel').forEach(panel => {
        if (panel.id === `tab-${tabName}`) {
          panel.classList.add('active');
          panel.hidden = false;
        } else {
          panel.classList.remove('active');
          panel.hidden = true;
        }
      });
    });
  });

  // Initial load
  await loadStatus();
  await loadCategories();
  await renderStatusSetsPreview();
  await renderCustomFieldsPreview();
})();