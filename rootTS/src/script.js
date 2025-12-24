(async () => {
  // ========================================
  // ELEMENT REFERENCES
  // ========================================
  
  const el = {
    tokenStatus: document.getElementById("tokenStatus"),
    envList: document.getElementById("envList"),
    envPanel: document.getElementById("envPanel"),
    toggleEnvBtn: document.getElementById("toggleEnvBtn"),
    authorizeBtn: document.getElementById("authorizeBtn"),
    fetchConfigBtn: document.getElementById("fetchConfigBtn"),
    setupDefaultConfigBtn: document.getElementById("setupDefaultConfigBtn"),
    categorySummary: document.getElementById("categorySummary"),
    categoryTree: document.getElementById("categoryTree"),
    statusSetsHost: document.getElementById("StatusSets"),
    customFieldsHost: document.getElementById("CustomFields"),
    fetchAssetsInfo: document.getElementById("fetchAssetsInfo"),
    toastContainer: document.getElementById("toastContainer"),
    statusSetsLoading: document.getElementById("statusSetsLoading"),
    customFieldsLoading: document.getElementById("customFieldsLoading"),
    categoriesLoading: document.getElementById("categoriesLoading"),
    createStatusSetForm: document.getElementById("createStatusSetForm"),
    statusSetsTableBody: document.getElementById("statusSetsTableBody"),
    resetStatusSetForm: document.getElementById("resetStatusSetForm"),
    createCustomFieldForm: document.getElementById("createCustomFieldForm"),
    customFieldsTableBody: document.getElementById("customFieldsTableBody"),
    resetCustomFieldForm: document.getElementById("resetCustomFieldForm"),
    createCategoryForm: document.getElementById("createCategoryForm"),
    categoryCardsContainer: document.getElementById("categoryCardsContainer"),
    resetCategoryForm: document.getElementById("resetCategoryForm"),
    loadConfigStructureBtn: document.getElementById("loadConfigStructureBtn"),
    downloadConfigJsonBtn: document.getElementById("downloadConfigJsonBtn"),
    copyConfigJsonBtn: document.getElementById("copyConfigJsonBtn"),
    configStructureLoading: document.getElementById("configStructureLoading"),
    configStructureContent: document.getElementById("configStructureContent"),
    configStructureError: document.getElementById("configStructureError"),
    configSummary: document.getElementById("configSummary"),
    configJsonViewer: document.getElementById("configJsonViewer"),
    configErrorMessage: document.getElementById("configErrorMessage"),
    createIssueForm: document.getElementById("createIssueForm"),
    updateIssueForm: document.getElementById("updateIssueForm"),
    fetchIssuesBtn: document.getElementById("fetchIssuesBtn"),
    issuesLoading: document.getElementById("issuesLoading"),
    issueSubtypesDisplay: document.getElementById("issueSubtypesDisplay"),
    recentIssuesDisplay: document.getElementById("recentIssuesDisplay"),
    activityLogTableBody: document.getElementById("activityLogTableBody"),
    activityLogLoading: document.getElementById("activityLogLoading"),
    toggleConfigBtn: document.getElementById("toggleConfigBtn"),
    activityLogView: document.getElementById("activityLogView"),
    configurationView: document.getElementById("configurationView"),
    initialSetupBtn: document.getElementById("initialSetupBtn"),
  };


  // ========================================
  // TOAST NOTIFICATION SYSTEM
  // ========================================
  
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

  // ========================================
  // CATEGORY TREE RENDERING
  // ========================================

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

  el.toggleEnvBtn?.addEventListener("click", () => {
    el.envPanel.hidden = !el.envPanel.hidden;
  });
  // ========================================
  // BUTTON HANDLERS
  // ========================================

  el.authorizeBtn?.addEventListener("click", () => {
    window.location.href = "/authorize";
  });

  el.initialSetupBtn?.addEventListener("click", async () => {
    showToast('warning', 'Doing all initial setup', 'This will reload the page...', 3000);
    setTimeout(() => {
      window.location.href = "/do_all_initial_setup";
    }, 500);
  });

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

  // ========================================
  // ISSUES HANDLING
  // ========================================

  el.createIssueForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
      title: document.getElementById('issueTitle').value,
      status: document.getElementById('issueStatus').value,
      issue_subtype_id: document.getElementById('issueSubtypeId').value,
      description: document.getElementById('issueDescription').value || undefined,
      location_description: document.getElementById('issueLocation').value || undefined,
    };

    try {
      const response = await fetch('/create_issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (response.redirected) {
        window.location.href = response.url;
        return;
      }

      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        console.error('Non-JSON response:', text.substring(0, 200));
        showToast('error', 'Server Error', 'Server returned an error page. Check authentication or server logs.');
        return;
      }

      if (response.ok) {
        showToast('success', 'Issue Created', `Issue ID: ${data.id}`);
        el.createIssueForm.reset();
      } else {
        showToast('error', 'Creation Failed', data.error || 'Unknown error');
      }
    } catch (err) {
      showToast('error', 'Request Error', err.message);
      console.error('Create issue error:', err);
    }
  });

  el.updateIssueForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
      issue_guid: document.getElementById('updateIssueGuid').value,
      status_value: document.getElementById('updateIssueStatus').value,
    };

    try {
      const response = await fetch('/update_issue_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (response.redirected) {
        window.location.href = response.url;
        return;
      }

      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        console.error('Non-JSON response:', text.substring(0, 200));
        showToast('error', 'Server Error', 'Server returned an error page. Check authentication or server logs.');
        return;
      }

      if (response.ok) {
        showToast('success', 'Status Updated', `Issue status changed to ${formData.status_value}`);
        el.updateIssueForm.reset();
      } else {
        showToast('error', 'Update Failed', data.error || 'Unknown error');
      }
    } catch (err) {
      showToast('error', 'Request Error', err.message);
      console.error('Update issue error:', err);
    }
  });

  el.fetchIssuesBtn?.addEventListener('click', async () => {
    showLoading(el.issuesLoading);
    
    try {
      const response = await fetch('/fetch_issue_subtypes', {
        credentials: 'include'
      });

      if (response.redirected) {
        window.location.href = response.url;
        return;
      }

      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const text = await response.text();
        console.error('Non-JSON response:', text.substring(0, 200));
        showToast('error', 'Server Error', 'Server returned an error page. Check authentication or server logs.');
        hideLoading(el.issuesLoading);
        return;
      }

      if (data.success) {
        let subtypesHtml = '<h3>Issue Types & Subtypes</h3>';
        subtypesHtml += '<div class="issues-table-wrapper"><table class="issues-table"><thead><tr><th>Type</th><th>Subtype</th><th>ID</th><th>Source</th></tr></thead><tbody>';
        
        for (const [typeKey, typeData] of Object.entries(data.grouped_by_type || {})) {
          typeData.forEach((subtype, index) => {
            subtypesHtml += `
              <tr>
                <td>${index === 0 ? typeKey : ''}</td>
                <td>${subtype.subtype}</td>
                <td><code>${subtype.id}</code></td>
                <td>${subtype.source}</td>
              </tr>
            `;
          });
        }
        
        subtypesHtml += '</tbody></table></div>';
        el.issueSubtypesDisplay.innerHTML = subtypesHtml;

        if (data.recent_issues && data.recent_issues.length > 0) {
          let issuesHtml = '<h3>Recent Issues</h3>';
          issuesHtml += '<div class="issues-table-wrapper"><table class="issues-table"><thead><tr><th>Issue ID</th><th>Title</th><th>Status</th><th>Type</th></tr></thead><tbody>';
          
          data.recent_issues.slice(0, 20).forEach(issue => {
            issuesHtml += `
              <tr>
                <td><code>${issue.id || 'N/A'}</code></td>
                <td>${issue.title || 'N/A'}</td>
                <td>${issue.status || 'N/A'}</td>
                <td>${issue.issueTypeName || 'N/A'}</td>
              </tr>
            `;
          });
          
          issuesHtml += '</tbody></table></div>';
          el.recentIssuesDisplay.innerHTML = issuesHtml;
        }

        showToast('success', 'Issues Loaded', `Found ${data.total_count} subtypes`);
      } else {
        showToast('error', 'Load Failed', data.error || 'Unknown error');
      }
    } catch (err) {
      showToast('error', 'Request Error', err.message);
      console.error('Fetch issues error:', err);
    } finally {
      hideLoading(el.issuesLoading);
    }
  });

  // ========================================
  // TAB SWITCHING
  // ========================================

  document.querySelectorAll('.forge-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      
      document.querySelectorAll('.forge-tab').forEach(t => {
        if (t === tab) {
          t.classList.add('active');
          t.setAttribute('aria-selected', 'true');
        } else {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
    }
  });
  
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
// ========================================
// INITIAL LOAD
// ========================================
await loadStatus();
await renderStatusSetsPreview();
await renderCustomFieldsPreview();

// ==============================
// TOGGLE BUTTON FUNCTIONALITY
// ========================================

})();