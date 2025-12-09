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
  // ACTIVITY LOG FUNCTIONALITY
  // ========================================

  async function loadActivityLog() {
    const tableBody = el.activityLogTableBody;
    const loading = el.activityLogLoading;

    if (!tableBody || !loading) return;

    try {
      loading.hidden = false;

      const response = await fetch('/fetch_activity_log');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const data = result.logs || result;
      loading.hidden = true;

      console.log('Activity log data received:', data);

      if (!Array.isArray(data) || data.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; padding: 20px;">
              No activity log entries found
            </td>
          </tr>
        `;
        return;
      }

      // Render the table with 6 columns
      tableBody.innerHTML = data.map(entry => `
        <tr>
          <td>${formatActivityTimestamp(entry.timestamp)}</td>
          <td>${escapeActivityHtml(entry.action_type || 'N/A')}</td>
          <td>${escapeActivityHtml(entry.username || 'N/A')}</td>
          <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" 
              title="${escapeActivityHtml(entry.raw_message || 'N/A')}">
            ${escapeActivityHtml(entry.raw_message || 'N/A')}
          </td>
          <td>
            ${entry.error 
              ? '<span class="error-badge">Error</span>' 
              : '<span class="success-badge">Success</span>'}
          </td>
          <td>
            <button class="forge-btn" onclick="window.showActivityLogDetails('${entry.id}')">View</button>
          </td>
        </tr>
      `).join('');

      console.log(`✓ Successfully loaded ${data.length} activity log entries`);
      showToast('success', 'Activity Log Loaded', `${data.length} entries loaded`);

    } catch (error) {
      console.error('Error loading activity log:', error);
      loading.hidden = true;

      tableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 20px;">
            <div style="color: var(--forge-error); margin-bottom: 12px;">
              <strong>⚠️ Error Loading Activity Log</strong>
            </div>
            <div style="color: var(--forge-text-muted); font-size: 0.875rem; margin-bottom: 8px;">
              ${escapeActivityHtml(error.message)}
            </div>
            <div style="color: var(--forge-text-muted); font-size: 0.75rem;">
              <strong>Check:</strong><br>
              1. Server is running (python main.py)<br>
              2. Activity log file exists at data/activity_log.json<br>
              3. Browser console for detailed errors
            </div>
          </td>
        </tr>
      `;
    }
  }

  function formatActivityTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    try {
      // Handle custom format: "2025-12-05 (10:46:48)"
      if (timestamp.includes('(') && timestamp.includes(')')) {
        // Extract the date part and time part
        const match = timestamp.match(/^(\d{4})-(\d{2})-(\d{2})\s*\((\d{2}):(\d{2}):(\d{2})\)$/);
        if (match) {
          const [, year, month, day, hour, minute] = match;
          // Format as: MM/DD/YYYY, HH:MM AM/PM
          const date = new Date(year, month - 1, day, hour, minute);
          const dateStr = date.toLocaleDateString();
          const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          return `${dateStr}, ${timeStr}`;
        }
      }
      // Fallback: try standard date parsing
      const date = new Date(timestamp);
      if (!isNaN(date.getTime())) {
        return date.toLocaleString();
      }
      return timestamp; // Return original if parsing fails
    } catch (e) {
      return timestamp; // Return original on error
    }
  }

  function escapeActivityHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  window.showActivityLogDetails = async function(entryId) {
    try {
      const response = await fetch('/fetch_activity_log');
      const result = await response.json();
      const data = result.logs || result;
      const entry = data.find(e => e.id === entryId);

      if (!entry) {
        showToast('error', 'Entry not found', 'Could not find the selected activity log entry');
        return;
      }

      displayActivityLogModal(entry);
    } catch (error) {
      console.error('Error fetching details:', error);
      showToast('error', 'Failed to load details', error.message);
    }
  };

  function displayActivityLogModal(entry) {
    const modal = document.createElement('div');
    modal.className = 'activity-log-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    `;

    const errorSection = entry.error
      ? `<div style="padding: 12px; background: rgba(234, 67, 53, 0.1); border-left: 4px solid #ea4335; margin-bottom: 16px; border-radius: 4px;">
          <strong style="color: #c5221f;">Error:</strong>
          <p style="margin: 4px 0 0 0; color: #c5221f;">${escapeActivityHtml(entry.error)}</p>
        </div>`
      : `<div style="padding: 12px; background: rgba(52, 168, 83, 0.1); border-left: 4px solid #34a853; margin-bottom: 16px; border-radius: 4px;">
          <strong style="color: #188038;">Status:</strong>
          <p style="margin: 4px 0 0 0; color: #188038;">Success</p>
        </div>`;

    const payloadSection = entry.payload
      ? `<div style="margin-top: 16px; padding: 12px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; border: 1px solid var(--forge-border);">
          <h4 style="margin: 0 0 8px 0; color: var(--forge-text);">Payload:</h4>
          <pre style="margin: 0; overflow-x: auto; font-size: 0.875rem; white-space: pre-wrap; word-wrap: break-word; color: var(--forge-text); font-family: monospace;">${escapeActivityHtml(JSON.stringify(entry.payload, null, 2))}</pre>
        </div>`
      : '';

    modal.innerHTML = `
      <div style="background: var(--forge-surface); border-radius: 8px; padding: 24px; max-width: 700px; max-height: 80vh; overflow-y: auto; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); border: 1px solid var(--forge-border);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; color: var(--forge-text);">${escapeActivityHtml(entry.action_type)}</h3>
          <button onclick="this.closest('.activity-log-modal').remove()" style="background: none; border: none; cursor: pointer; font-size: 24px; color: var(--forge-text-muted);">&times;</button>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
          <div>
            <label style="display: block; font-size: 0.875rem; color: var(--forge-text-muted); margin-bottom: 4px;">ID</label>
            <div style="font-family: monospace; font-size: 0.875rem; color: var(--forge-text);">${escapeActivityHtml(entry.id)}</div>
          </div>
          <div>
            <label style="display: block; font-size: 0.875rem; color: var(--forge-text-muted); margin-bottom: 4px;">Timestamp</label>
            <div style="font-size: 0.875rem; color: var(--forge-text);">${formatActivityTimestamp(entry.timestamp)}</div>
          </div>
          <div style="grid-column: 1 / -1;">
            <label style="display: block; font-size: 0.875rem; color: var(--forge-text-muted); margin-bottom: 4px;">Username</label>
            <div style="font-size: 0.875rem; color: var(--forge-text);">${escapeActivityHtml(entry.username)}</div>
          </div>
        </div>
        <div style="margin-bottom: 16px;">
          <label style="display: block; font-size: 0.875rem; color: var(--forge-text-muted); margin-bottom: 4px;">Raw Message</label>
          <div style="padding: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; font-size: 0.875rem; border: 1px solid var(--forge-border); color: var(--forge-text);">${escapeActivityHtml(entry.raw_message)}</div>
        </div>
        ${errorSection}
        ${payloadSection}
        <div style="display: flex; gap: 8px; margin-top: 20px;">
          <button onclick="this.closest('.activity-log-modal').remove()" class="forge-btn" style="flex: 1;">Close</button>
        </div>
      </div>
    `;

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });

    document.body.appendChild(modal);
  }


  // ========================================
  // DYNAMIC STATUS SET FORM (TABLE FORMAT)
  // ========================================

  const AUTODESK_COLOR_MAP = {
    'adsk-charcoal-500': { rgb: '94, 94, 94', label: 'Charcoal' },
    'adsk-blue-500': { rgb: '0, 103, 220', label: 'Blue' },
    'adsk-purple-500': { rgb: '129, 92, 200', label: 'Purple' },
    'adsk-yellow-500': { rgb: '255, 199, 0', label: 'Yellow' },
    'adsk-green-500': { rgb: '97, 191, 94', label: 'Green' },
    'adsk-red-500': { rgb: '232, 76, 61', label: 'Red' },
    'adsk-orange-500': { rgb: '255, 143, 0', label: 'Orange' },
    'adsk-pink-500': { rgb: '255, 105, 180', label: 'Pink' },
    'adsk-turquoise-500': { rgb: '64, 224, 208', label: 'Turquoise' },
    'adsk-dark-blue-500': { rgb: '29, 79, 145', label: 'Dark Blue' },
    'adsk-salmon-500': { rgb: '250, 128, 114', label: 'Salmon' },
    'adsk-brown-500': { rgb: '139, 90, 43', label: 'Brown' }
  };

  let statusSetRowCounter = 0;
  let statusValueRowCounter = 0;

  function createStatusValueRow(parentSetId) {
    statusValueRowCounter++;
    const valueId = `status-value-${statusValueRowCounter}`;
    
    const tr = document.createElement('tr');
    tr.className = 'status-value-row';
    tr.dataset.valueId = valueId;
    
    const labelCell = document.createElement('td');
    labelCell.innerHTML = `
      <input 
        type="text" 
        class="forge-input sv-label-input" 
        placeholder="e.g., Pending"
        required
      />
    `;
    
    const descCell = document.createElement('td');
    descCell.innerHTML = `
      <input 
        type="text" 
        class="forge-input sv-description-input" 
        placeholder="e.g., Pending"
        required
      />
    `;
    
    const colorCell = document.createElement('td');
    const colorOptions = Object.keys(AUTODESK_COLOR_MAP).map(colorKey => {
      const { rgb, label } = AUTODESK_COLOR_MAP[colorKey];
      return `<option value="${colorKey}" data-rgb="${rgb}">${label}</option>`;
    }).join('');
    
    colorCell.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="color-preview-circle" style="display: inline-block; width: 20px; height: 20px; border-radius: 50%; background-color: rgb(94, 94, 94); border: 1px solid var(--forge-border);"></span>
        <select class="forge-select sv-color-select" required style="flex: 1;">
          ${colorOptions}
        </select>
      </div>
    `;
    
    const removeCell = document.createElement('td');
    removeCell.style.textAlign = 'center';
    removeCell.innerHTML = `
      <button type="button" class="remove-status-value-btn" title="Remove status value">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
          <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
        </svg>
      </button>
    `;
    
    tr.appendChild(labelCell);
    tr.appendChild(descCell);
    tr.appendChild(colorCell);
    tr.appendChild(removeCell);
    
    const colorSelect = colorCell.querySelector('.sv-color-select');
    const previewCircle = colorCell.querySelector('.color-preview-circle');
    
    colorSelect.addEventListener('change', () => {
      const selectedOption = colorSelect.options[colorSelect.selectedIndex];
      const rgb = selectedOption.dataset.rgb;
      previewCircle.style.backgroundColor = `rgb(${rgb})`;
    });
    
    const removeBtn = removeCell.querySelector('.remove-status-value-btn');
    removeBtn.addEventListener('click', () => {
      const statusValuesTable = tr.closest('.status-values-nested-table');
      const tbody = statusValuesTable.querySelector('tbody');
      
      if (tbody.querySelectorAll('.status-value-row').length > 1) {
        tr.remove();
      } else {
        showToast('warning', 'Minimum Required', 'At least one status value is required per status set');
      }
    });
    
    return tr;
  }

  function createAddStatusValueButton(parentSetId) {
    const tr = document.createElement('tr');
    tr.className = 'add-status-value-tr';
    
    const td = document.createElement('td');
    td.colSpan = 4;
    td.innerHTML = `
      <button type="button" class="add-status-value-btn">
        <svg width="16" height="16" fill="currentColor">
          <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="2"/>
        </svg>
        Add Status Value
      </button>
    `;
    
    tr.appendChild(td);
    
    const btn = td.querySelector('.add-status-value-btn');
    btn.addEventListener('click', () => {
      const statusValuesTable = tr.closest('.status-values-nested-table');
      const tbody = statusValuesTable.querySelector('tbody');
      const newRow = createStatusValueRow(parentSetId);
      tbody.insertBefore(newRow, tr);
    });
    
    return tr;
  }

  function createStatusSetRow() {
    statusSetRowCounter++;
    const setId = `status-set-${statusSetRowCounter}`;
    
    const tr = document.createElement('tr');
    tr.className = 'status-set-row';
    tr.dataset.setId = setId;
    
    const nameCell = document.createElement('td');
    nameCell.innerHTML = `
      <input 
        type="text" 
        class="forge-input ss-name-input" 
        placeholder="e.g., Fabrication"
        required
      />
    `;
    
    const descCell = document.createElement('td');
    descCell.innerHTML = `
      <input 
        type="text" 
        class="forge-input ss-description-input" 
        placeholder="e.g., Stages of fabrication"
        required
      />
    `;
    
    const valuesCell = document.createElement('td');
    valuesCell.innerHTML = `
      <div class="status-values-container">
        <table class="status-values-nested-table">
          <thead>
            <tr>
              <th style="width: 30%">Status Label *</th>
              <th style="width: 35%">Description *</th>
              <th style="width: 30%">Colour *</th>
              <th style="width: 40px"></th>
            </tr>
          </thead>
          <tbody>
          </tbody>
        </table>
      </div>
    `;
    
    const tbody = valuesCell.querySelector('tbody');
    tbody.appendChild(createStatusValueRow(setId));
    tbody.appendChild(createAddStatusValueButton(setId));
    
    const removeCell = document.createElement('td');
    removeCell.style.textAlign = 'center';
    removeCell.innerHTML = `
      <button type="button" class="remove-status-set-btn" title="Remove status set">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
          <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
        </svg>
      </button>
    `;
    
    tr.appendChild(nameCell);
    tr.appendChild(descCell);
    tr.appendChild(valuesCell);
    tr.appendChild(removeCell);
    
    const removeBtn = removeCell.querySelector('.remove-status-set-btn');
    removeBtn.addEventListener('click', () => {
      const tbody = tr.parentElement;
      
      if (tbody.querySelectorAll('.status-set-row').length > 1) {
        tr.remove();
      } else {
        showToast('warning', 'Minimum Required', 'At least one status set is required');
      }
    });
    
    return tr;
  }

  function createAddStatusSetButton() {
    const tr = document.createElement('tr');
    tr.className = 'add-row-tr';
    
    const td = document.createElement('td');
    td.colSpan = 4;
    td.innerHTML = `
      <button type="button" class="add-row-btn">
        <svg width="16" height="16" fill="currentColor">
          <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="2"/>
        </svg>
        Add Status Set
      </button>
    `;
    
    tr.appendChild(td);
    
    const btn = td.querySelector('.add-row-btn');
    btn.addEventListener('click', () => {
      const newRow = createStatusSetRow();
      el.statusSetsTableBody.insertBefore(newRow, tr);
    });
    
    return tr;
  }

  function collectStatusSetsTableData() {
    const statusSetRows = el.statusSetsTableBody.querySelectorAll('.status-set-row');
    
    if (statusSetRows.length === 0) {
      showToast('error', 'Validation Error', 'At least one status set is required');
      return null;
    }
    
    const statusSets = [];
    
    for (const row of statusSetRows) {
      const name = row.querySelector('.ss-name-input').value.trim();
      const description = row.querySelector('.ss-description-input').value.trim();
      
      if (!name || !description) {
        showToast('error', 'Validation Error', 'Status set name and description are required for all rows');
        return null;
      }
      
      const statusValueRows = row.querySelectorAll('.status-value-row');
      
      if (statusValueRows.length === 0) {
        showToast('error', 'Validation Error', `At least one status value is required for "${name}"`);
        return null;
      }
      
      const statusLabels = [];
      const descriptions = [];
      const statusColors = [];
      
      for (const valueRow of statusValueRows) {
        const label = valueRow.querySelector('.sv-label-input').value.trim();
        const desc = valueRow.querySelector('.sv-description-input').value.trim();
        const color = valueRow.querySelector('.sv-color-select').value;
        
        if (!label || !desc || !color) {
          showToast('error', 'Validation Error', `All status value fields must be filled for "${name}"`);
          return null;
        }
        
        statusLabels.push(label);
        descriptions.push(desc);
        statusColors.push(color);
      }
      
      statusSets.push({
        name: name,
        status_set_description: description,
        status_label: statusLabels,
        description: descriptions,
        status_colors: statusColors
      });
    }
    
    return statusSets;
  }

  function resetStatusSetForm() {
    el.statusSetsTableBody.innerHTML = '';
    el.statusSetsTableBody.appendChild(createStatusSetRow());
    el.statusSetsTableBody.appendChild(createAddStatusSetButton());
  }

  // ========================================
  // DYNAMIC CUSTOM FIELDS FORM (TABLE FORMAT)
  // ========================================

  let customFieldRowCounter = 0;
  let availableStatusSets = [];
  let availableCustomFields = [];
  let availableCategories = [];
  let categoryCardCounter = 0;

  function createCustomFieldRow() {
    customFieldRowCounter++;
    const rowId = `cf-row-${customFieldRowCounter}`;
    
    const row = document.createElement('tr');
    row.dataset.rowId = rowId;
    row.innerHTML = `
      <td>
        <input 
          type="text" 
          class="cf-display-name" 
          placeholder="Material Type"
          required
        />
      </td>
      <td>
        <input 
          type="text" 
          class="cf-description" 
          placeholder="Type of material used..."
        />
      </td>
      <td>
        <select class="cf-data-type" required>
          <option value="text">Text</option>
          <option value="date">Date</option>
          <option value="boolean">Boolean</option>
          <option value="numeric">Numeric</option>
          <option value="select">Select</option>
          <option value="multi_select">Multi-Select</option>
        </select>
      </td>
      <td style="text-align: center;">
        <input type="checkbox" class="cf-required" />
      </td>
      <td>
        <input 
          type="text" 
          class="cf-enum-values" 
          placeholder="Steel, Concrete, Wood, Plastic"
          disabled
        />
      </td>
      <td>
        <input 
          type="text" 
          class="cf-default-value" 
          placeholder="Default..."
        />
      </td>
      <td>
        <button type="button" class="remove-row-btn" title="Remove row">
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
            <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
          </svg>
        </button>
      </td>
    `;
    
    const dataTypeSelect = row.querySelector('.cf-data-type');
    const enumValuesInput = row.querySelector('.cf-enum-values');
    const defaultValueInput = row.querySelector('.cf-default-value');
    const removeBtn = row.querySelector('.remove-row-btn');
    
    dataTypeSelect.addEventListener('change', () => {
      const dataType = dataTypeSelect.value;
      
      enumValuesInput.disabled = true;
      enumValuesInput.value = '';
      
      if (dataType === 'select' || dataType === 'multi_select') {
        enumValuesInput.disabled = false;
        enumValuesInput.required = true;
      } else {
        enumValuesInput.required = false;
      }
      
      if (dataType === 'date') {
        defaultValueInput.type = 'date';
        defaultValueInput.placeholder = '';
      } else if (dataType === 'numeric') {
        defaultValueInput.type = 'number';
        defaultValueInput.placeholder = '0';
      } else if (dataType === 'boolean') {
        const boolSelect = document.createElement('select');
        boolSelect.className = 'cf-default-value';
        boolSelect.innerHTML = `
          <option value="">None</option>
          <option value="true">True</option>
          <option value="false">False</option>
        `;
        defaultValueInput.replaceWith(boolSelect);
      } else {
        if (defaultValueInput.tagName === 'SELECT') {
          const textInput = document.createElement('input');
          textInput.type = 'text';
          textInput.className = 'cf-default-value';
          textInput.placeholder = 'Default...';
          defaultValueInput.replaceWith(textInput);
        } else {
          defaultValueInput.type = 'text';
          defaultValueInput.placeholder = 'Default...';
        }
      }
    });
    
    removeBtn.addEventListener('click', () => {
      const tbody = row.closest('tbody');
      const dataRows = tbody.querySelectorAll('tr:not(.add-row-tr)');
      if (dataRows.length > 1) {
        row.remove();
      } else {
        showToast('warning', 'Cannot remove', 'At least one row must remain');
      }
    });
    
    return row;
  }

  function createAddRowButton() {
    const row = document.createElement('tr');
    row.className = 'add-row-tr';
    row.innerHTML = `
      <td colspan="7" style="padding: 0; border: none;">
        <button type="button" class="add-row-btn">
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
          </svg>
          Add Row
        </button>
      </td>
    `;
    
    const addBtn = row.querySelector('.add-row-btn');
    addBtn.addEventListener('click', () => {
      const tbody = row.closest('tbody');
      const newRow = createCustomFieldRow();
      tbody.insertBefore(newRow, row);
    });
    
    return row;
  }

  function collectCustomFieldsTableData() {
    const tbody = document.getElementById('customFieldsTableBody');
    const rows = tbody.querySelectorAll('tr:not(.add-row-tr)');
    
    if (rows.length === 0) {
      showToast('error', 'No Fields', 'Please add at least one custom field row');
      return null;
    }
    
    const fields = [];
    
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const displayName = row.querySelector('.cf-display-name').value.trim();
      const description = row.querySelector('.cf-description').value.trim();
      const dataType = row.querySelector('.cf-data-type').value;
      const requiredOnIngress = row.querySelector('.cf-required').checked;
      const enumValuesInput = row.querySelector('.cf-enum-values').value.trim();
      
      if (!displayName || !dataType) {
        showToast('error', 'Validation Error', `Row ${i + 1}: Display name and data type are required`);
        return null;
      }
      
      const fieldData = {
        displayName: displayName,
        description: description || '',
        dataType: dataType,
        requiredOnIngress: requiredOnIngress,
        enumValues: [],
        maxLengthOnIngress: null,
        defaultValue: null
      };
      
      if (dataType === 'select' || dataType === 'multi_select') {
        if (!enumValuesInput) {
          showToast('error', 'Validation Error', `Row ${i + 1}: Enum values are required for select/multi_select`);
          return null;
        }
        
        const enumValues = enumValuesInput.split(',').map(v => v.trim()).filter(v => v);
        
        if (enumValues.length === 0) {
          showToast('error', 'Validation Error', `Row ${i + 1}: At least one enum value is required for select/multi_select`);
          return null;
        }
        
        fieldData.enumValues = enumValues;
      }
      
      if (dataType === 'text') {
        fieldData.maxLengthOnIngress = 50;
      }
      
      const defaultValueEl = row.querySelector('.cf-default-value');
      if (defaultValueEl && defaultValueEl.value) {
        if (dataType === 'boolean') {
          fieldData.defaultValue = defaultValueEl.value === 'true';
        } else if (dataType === 'numeric') {
          fieldData.defaultValue = parseFloat(defaultValueEl.value);
        } else {
          fieldData.defaultValue = defaultValueEl.value;
        }
      }
      
      fields.push(fieldData);
    }
    
    return fields;
  }

  function resetCustomFieldForm() {
    const tbody = document.getElementById('customFieldsTableBody');
    tbody.innerHTML = '';
    tbody.appendChild(createCustomFieldRow());
    tbody.appendChild(createAddRowButton());
  }

  // ========================================
  // DYNAMIC CATEGORY CARDS FORM
  // ========================================

  function createCategoryCard() {
    categoryCardCounter++;
    const cardId = `cat-card-${categoryCardCounter}`;
    
    const card = document.createElement('div');
    card.className = 'category-creation-card';
    card.dataset.cardId = cardId;
    
    card.innerHTML = `
      <div class="category-card-header">
        <button type="button" class="remove-category-btn" title="Remove category">
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
            <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
          </svg>
        </button>
      </div>
      
      <div class="category-card-body">
        <div class="category-form-row-main">
          <div class="category-form-group">
            <label>Category Name *</label>
            <input 
              type="text" 
              class="cat-name-input" 
              placeholder="Category name..." 
              required
            />
          </div>
          
          <div class="category-form-group">
            <label>Description *</label>
            <input 
              type="text" 
              class="cat-description-input" 
              placeholder="Brief description..." 
              required
            />
          </div>
          
          <div class="category-form-group">
            <label>Parent Category *</label>
            <select class="cat-parent-select" required>
              <option value="">Select parent...</option>
            </select>
          </div>
          
          <div class="category-form-group cat-statusset-group">
            <div style="display: flex; align-items: center; gap: 6px;">
              <svg width="14" height="14" fill="var(--forge-success)">
                <circle cx="7" cy="7" r="5"/>
              </svg>
              <label style="margin: 0; font-size: 0.75rem;">Status Set *</label>
            </div>
            <select class="cat-statusset-select" required>
              <option value="">Select status set...</option>
            </select>
            <div class="inheritance-warning" style="display: none;">
              <svg width="12" height="12" fill="var(--forge-warning)" style="flex-shrink: 0;">
                <path d="M7.938 2.016A.13.13 0 018 2.151V4.5a.5.5 0 01-1 0V2.15a.13.13 0 01.062-.135zm-.702 8.027a.75.75 0 10-1.5 0 .75.75 0 001.5 0z"/>
              </svg>
              <span style="font-size: 0.7rem; color: var(--forge-warning);">Inherited</span>
            </div>
          </div>
        </div>
        
        <div class="category-form-group cat-customfields-group">
          <div style="display: flex; align-items: center; gap: 8px;">
            <svg width="16" height="16" fill="var(--forge-warning)">
              <rect x="2" y="4" width="12" height="8" rx="2" />
            </svg>
            <label style="margin: 0;">Custom Attributes (Optional)</label>
          </div>
          <div class="custom-fields-selector">
            <div class="selected-fields-display">
              <span class="placeholder-text">Click to select custom fields...</span>
            </div>
            <div class="custom-fields-dropdown" style="display: none;">
            </div>
          </div>
          <div class="inheritance-warning" style="display: none;">
            <svg width="14" height="14" fill="var(--forge-warning)" style="flex-shrink: 0;">
              <path d="M7.938 2.016A.13.13 0 018 2.151V4.5a.5.5 0 01-1 0V2.15a.13.13 0 01.062-.135zm-.702 8.027a.75.75 0 10-1.5 0 .75.75 0 001.5 0z"/>
            </svg>
            <span style="font-size: 0.75rem; color: var(--forge-warning);">
              Inherited from parent category
            </span>
          </div>
        </div>
      </div>
    `;
    
    const parentSelect = card.querySelector('.cat-parent-select');
    availableCategories.forEach(cat => {
      const option = document.createElement('option');
      option.value = cat.category_id;
      option.textContent = `${cat.category_name} (ID: ${cat.category_id})`;
      option.dataset.parentId = cat.parent_id;
      parentSelect.appendChild(option);
    });
    
    const statusSetSelect = card.querySelector('.cat-statusset-select');
    const uniqueStatusSets = [...new Set(availableStatusSets.map(ss => ss.status_set_name))];
    uniqueStatusSets.forEach(ssName => {
      const option = document.createElement('option');
      option.value = ssName;
      option.textContent = ssName;
      statusSetSelect.appendChild(option);
    });
    
    if (uniqueStatusSets.includes('Default')) {
      statusSetSelect.value = 'Default';
    }
    
    const customFieldsDropdown = card.querySelector('.custom-fields-dropdown');
    availableCustomFields.forEach(cf => {
      const label = document.createElement('label');
      label.className = 'custom-field-checkbox-label';
      label.innerHTML = `
        <input type="checkbox" value="${cf.name}" />
        <span>${cf.display_name}</span>
      `;
      customFieldsDropdown.appendChild(label);
    });
    
    const selectedFieldsDisplay = card.querySelector('.selected-fields-display');
    selectedFieldsDisplay.addEventListener('click', () => {
      const dropdown = card.querySelector('.custom-fields-dropdown');
      dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    });
    
    const checkboxes = card.querySelectorAll('.custom-fields-dropdown input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        updateSelectedFieldsDisplay(card);
      });
    });
    
    document.addEventListener('click', (e) => {
      if (!card.contains(e.target)) {
        const dropdown = card.querySelector('.custom-fields-dropdown');
        dropdown.style.display = 'none';
      }
    });
    
    parentSelect.addEventListener('change', () => {
      const selectedOption = parentSelect.options[parentSelect.selectedIndex];
      if (!selectedOption.value) {
        enableStatusSetAndCustomFields(card);
        return;
      }
      
      const parentId = selectedOption.value;
      const grandParentId = selectedOption.dataset.parentId;
      
      if (parentId === '1' || grandParentId === '1') {
        enableStatusSetAndCustomFields(card);
      } else {
        disableStatusSetAndCustomFields(card);
      }
    });
    
    const removeBtn = card.querySelector('.remove-category-btn');
    removeBtn.addEventListener('click', () => {
      const container = card.closest('#categoryCardsContainer');
      const cards = container.querySelectorAll('.category-creation-card');
      if (cards.length > 1) {
        card.remove();
      } else {
        showToast('warning', 'Cannot remove', 'At least one category must remain');
      }
    });
    
    return card;
  }

  function updateSelectedFieldsDisplay(card) {
    const checkboxes = card.querySelectorAll('.custom-fields-dropdown input[type="checkbox"]:checked');
    const display = card.querySelector('.selected-fields-display');
    
    if (checkboxes.length === 0) {
      display.innerHTML = '<span class="placeholder-text">Click to select custom fields...</span>';
    } else {
      display.innerHTML = '';
      checkboxes.forEach((checkbox, index) => {
        const tag = document.createElement('span');
        tag.className = 'selected-field-tag';
        tag.textContent = checkbox.nextElementSibling.textContent;
        display.appendChild(tag);
        
        if (index < checkboxes.length - 1) {
          display.appendChild(document.createTextNode(' '));
        }
      });
    }
  }

  function disableStatusSetAndCustomFields(card) {
    const statusSetGroup = card.querySelector('.cat-statusset-group');
    const customFieldsGroup = card.querySelector('.cat-customfields-group');
    
    const statusSetSelect = card.querySelector('.cat-statusset-select');
    const customFieldsSelector = card.querySelector('.custom-fields-selector');
    
    statusSetSelect.disabled = true;
    statusSetSelect.value = '';
    customFieldsSelector.style.pointerEvents = 'none';
    customFieldsSelector.style.opacity = '0.5';
    
    card.querySelectorAll('.custom-fields-dropdown input[type="checkbox"]').forEach(cb => {
      cb.checked = false;
    });
    updateSelectedFieldsDisplay(card);
    
    statusSetGroup.querySelector('.inheritance-warning').style.display = 'flex';
    customFieldsGroup.querySelector('.inheritance-warning').style.display = 'flex';
  }

  function enableStatusSetAndCustomFields(card) {
    const statusSetGroup = card.querySelector('.cat-statusset-group');
    const customFieldsGroup = card.querySelector('.cat-customfields-group');
    
    const statusSetSelect = card.querySelector('.cat-statusset-select');
    const customFieldsSelector = card.querySelector('.custom-fields-selector');
    
    statusSetSelect.disabled = false;
    
    const uniqueStatusSets = [...new Set(availableStatusSets.map(ss => ss.status_set_name))];
    if (uniqueStatusSets.includes('Default')) {
      statusSetSelect.value = 'Default';
    }
    
    customFieldsSelector.style.pointerEvents = '';
    customFieldsSelector.style.opacity = '';
    
    statusSetGroup.querySelector('.inheritance-warning').style.display = 'none';
    customFieldsGroup.querySelector('.inheritance-warning').style.display = 'none';
  }

  function createAddCategoryButton() {
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'add-category-button-container';
    buttonContainer.innerHTML = `
      <button type="button" class="add-category-btn">
        <svg viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
        </svg>
        Add Category
      </button>
    `;
    
    const addBtn = buttonContainer.querySelector('.add-category-btn');
    addBtn.addEventListener('click', () => {
      const container = document.getElementById('categoryCardsContainer');
      const newCard = createCategoryCard();
      container.insertBefore(newCard, buttonContainer);
    });
    
    return buttonContainer;
  }

  function collectCategoriesData() {
    const cards = el.categoryCardsContainer.querySelectorAll('.category-creation-card');
    
    if (cards.length === 0) {
      showToast('error', 'Validation Error', 'At least one category is required');
      return null;
    }
    
    const categories = [];
    
    for (const card of cards) {
      const name = card.querySelector('.cat-name-input').value.trim();
      const description = card.querySelector('.cat-description-input').value.trim();
      const parentSelect = card.querySelector('.cat-parent-select');
      const statusSetSelect = card.querySelector('.cat-statusset-select');
      
      if (!name || !description) {
        showToast('error', 'Validation Error', 'Category name and description are required for all cards');
        return null;
      }
      
      if (!parentSelect.value) {
        showToast('error', 'Validation Error', `Parent category is required for "${name}"`);
        return null;
      }
      
      const selectedParentOption = parentSelect.options[parentSelect.selectedIndex];
      const parentId = parseInt(selectedParentOption.value);
      const parentName = selectedParentOption.textContent.split(' (ID:')[0];
      const grandParentId = selectedParentOption.dataset.parentId;
      
      const selectedFields = [];
      card.querySelectorAll('.custom-fields-dropdown input[type="checkbox"]:checked').forEach(cb => {
        selectedFields.push(cb.value);
      });
      
      let statusSetName = '';
      let customFields = [];
      
      if (parentId === 1 || grandParentId === '1') {
        if (!statusSetSelect.value) {
          showToast('error', 'Validation Error', `Status set is required for "${name}"`);
          return null;
        }
        statusSetName = statusSetSelect.value;
        customFields = selectedFields;
      } else {
        statusSetName = '';
        customFields = [];
      }
      
      categories.push({
        name: name,
        description: description,
        category_parent_name: parentName,
        category_parent_id: parentId,
        status_set_name: statusSetName,
        custom_fields: customFields
      });
    }
    
    return categories;
  }

  function resetCategoryForm() {
    el.categoryCardsContainer.innerHTML = '';
    el.categoryCardsContainer.appendChild(createCategoryCard());
    el.categoryCardsContainer.appendChild(createAddCategoryButton());
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
    
    const details = document.createElement("div");
    details.className = "category-details";
    
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
      
      availableCategories = [];
      const flattenCategories = (nodes, parentId = null) => {
        (nodes || []).forEach(node => {
          availableCategories.push({
            category_id: node.categoryId,
            category_name: node.categoryName,
            parent_id: parentId,
            status_set_name: node.statusSetName,
            custom_attributes: node.customAttributes || []
          });
          if (node.children && node.children.length > 0) {
            flattenCategories(node.children, node.categoryId);
          }
        });
      };
      flattenCategories(data.tree);
      
      el.categorySummary.textContent = data.count 
        ? `${data.count} ${data.count === 1 ? 'category' : 'categories'} loaded.` 
        : "No categories found. Please ensure categories.csv exists in the output folder.";
      
      el.categoryTree.innerHTML = "";
      
      if (data.tree && data.tree.length > 0) {
        el.categoryTree.appendChild(buildTreeUL(data.tree));
      } else if (data.count > 0) {
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

  el.toggleEnvBtn?.addEventListener("click", () => {
    el.envPanel.hidden = !el.envPanel.hidden;
  });

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
      
      availableStatusSets = items.flatMap(item => 
        (item.statuses || []).map(status => ({
          status_set_name: item.name,
          status_set_id: item.statusSetId,
          status_id: status.statusId,
          status_label: status.label,
          status_description: status.description
        }))
      );
      
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
      
      availableCustomFields = items.map(item => ({
        name: item.name || '',
        display_name: item.displayName || '',
        description: item.description || '',
        data_type: item.dataType || '',
        required: item.requiredOnIngress || false
      }));
      
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

  // ========================================
  // BUTTON HANDLERS
  // ========================================

  el.authorizeBtn?.addEventListener("click", () => {
    window.location.href = "/authorize";
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

  el.setupDefaultConfigBtn?.addEventListener("click", async () => {
    if (!confirm("This will create all default status sets, custom fields, and categories from the initial setup files. Continue?")) {
      return;
    }
    
    try {
      showToast("warning", "Setting up default configuration...", "This may take a moment");
      
      const response = await fetch("/setup_initial_configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include"
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      showToast("success", "Default configuration created", "Refreshing data...");
      
      await loadCategories();
      await renderStatusSetsPreview();
      await renderCustomFieldsPreview();
      
      showToast("success", "Configuration complete", "All default configs have been set up");
    } catch (err) {
      console.error("Setup default config error:", err);
      showToast("error", "Setup failed", err.message);
    }
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

  el.resetStatusSetForm?.addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all status sets? All entered data will be lost.')) {
      resetStatusSetForm();
      showToast('success', 'Form cleared', 'All status sets have been cleared.');
    }
  });

  el.createStatusSetForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const statusSetsData = collectStatusSetsTableData();
    if (!statusSetsData) {
      return;
    }
    
    try {
      console.log('Creating status sets with payload:', statusSetsData);
      
      const resp = await fetch("/create_status_sets_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(statusSetsData),
      });
      
      if (resp.redirected) { 
        window.location.href = resp.url; 
        return; 
      }
      
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        const totalStatusValues = statusSetsData.reduce((sum, set) => sum + set.status_label.length, 0);
        showToast('success', 'Status sets created', `${statusSetsData.length} status set(s) created successfully with ${totalStatusValues} total status values.`);
        
        resetStatusSetForm();
        await renderStatusSetsPreview();
        
        const statusSetsTab = document.querySelector('.forge-tab[data-tab="status-sets"]');
        if (statusSetsTab) {
          statusSetsTab.click();
        }
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create status set', text);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to create status set', err.message);
    }
  });

  el.resetCustomFieldForm?.addEventListener('click', (e) => {
    e.preventDefault();
    if (confirm('Are you sure you want to clear all rows? All data will be lost.')) {
      resetCustomFieldForm();
      showToast('success', 'Form reset', 'All rows have been cleared.');
    }
  });

  el.createCustomFieldForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fieldsData = collectCustomFieldsTableData();
    if (!fieldsData) {
      return;
    }
    
    try {
      console.log('Creating custom fields with payload:', fieldsData);
      
      const resp = await fetch("/create_custom_fields_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(fieldsData),
      });
      
      if (resp.redirected) { 
        window.location.href = resp.url; 
        return; 
      }
      
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        showToast('success', 'Custom fields created', `Successfully created ${fieldsData.length} custom field(s).`);
        
        resetCustomFieldForm();
        await renderCustomFieldsPreview();
        
        const customFieldsTab = document.querySelector('.forge-tab[data-tab="custom-fields"]');
        if (customFieldsTab) {
          customFieldsTab.click();
        }
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create custom fields', text);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to create custom fields', err.message);
    }
  });

  el.resetCategoryForm?.addEventListener('click', () => {
    if (confirm('Are you sure you want to clear all category cards?')) {
      resetCategoryForm();
    }
  });

  el.createCategoryForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const categoriesData = collectCategoriesData();
    if (!categoriesData) {
      return;
    }
    
    try {
      console.log('Creating categories with payload:', categoriesData);
      
      const resp = await fetch("/create_categories_from_json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(categoriesData),
      });
      
      if (resp.redirected) { 
        window.location.href = resp.url; 
        return; 
      }
      
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}));
        showToast('success', 'Categories created', `${categoriesData.length} ${categoriesData.length === 1 ? 'category' : 'categories'} created successfully.`);
        
        resetCategoryForm();
        await loadCategories();
        
        const categoriesTab = document.querySelector('.forge-tab[data-tab="categories"]');
        if (categoriesTab) {
          categoriesTab.click();
        }
      } else {
        const text = await resp.text();
        showToast('error', 'Failed to create categories', text);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to create categories', err.message);
    }
  });

  // ========================================
  // CATEGORY STATUS DEFAULT TAB
  // ========================================

  let categoryStatusDefaultData = null;

  async function loadCategoryStatusDefault() {
    try {
      if (el.configStructureLoading) el.configStructureLoading.hidden = false;
      if (el.configStructureContent) el.configStructureContent.style.display = 'none';
      if (el.configStructureError) el.configStructureError.style.display = 'none';

      const resp = await fetch('/api/category_status_default');
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || `HTTP ${resp.status}`);
      }

      categoryStatusDefaultData = await resp.json();

      if (el.configStructureLoading) el.configStructureLoading.hidden = true;
      if (el.configStructureContent) el.configStructureContent.style.display = 'block';

      renderCategoryStatusDefaultSummary(categoryStatusDefaultData);

      if (el.configJsonViewer) {
        el.configJsonViewer.textContent = JSON.stringify(categoryStatusDefaultData, null, 2);
      }

      if (el.downloadConfigJsonBtn) el.downloadConfigJsonBtn.disabled = false;

      showToast('success', 'Category Status Default Loaded', `Loaded ${categoryStatusDefaultData.length || 0} category default status mappings`);
    } catch (err) {
      console.error('Failed to load category status default:', err);
      if (el.configStructureLoading) el.configStructureLoading.hidden = true;
      if (el.configStructureError) {
        el.configStructureError.style.display = 'block';
        if (el.configErrorMessage) el.configErrorMessage.textContent = err.message;
      }
      showToast('error', 'Failed to Load Category Status Default', err.message);
    }
  }

  function renderCategoryStatusDefaultSummary(data) {
    if (!el.configSummary) return;

    const totalCategories = data.length || 0;
    const uniqueStatuses = new Set(data.map(d => d.default_status_id).filter(Boolean)).size;
    const ifcGlobalIdName = data.length > 0 ? data[0].IFCGlobalID_cat_name : 'N/A';

    const summaryCards = [
      {
        label: 'Total Categories',
        value: totalCategories,
        icon: '<path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h12a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6z"/>',
        color: 'var(--forge-primary)'
      },
      {
        label: 'Unique Default Statuses',
        value: uniqueStatuses,
        icon: '<circle cx="10" cy="10" r="8"/>',
        color: 'var(--forge-success)'
      },
      {
        label: 'IFCGlobalID Field',
        value: ifcGlobalIdName,
        icon: '<path d="M3 6a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V6zm2 0v8h10V6H5z"/>',
        color: 'var(--forge-warning)'
      }
    ];

    el.configSummary.innerHTML = summaryCards.map(card => `
      <div style="padding: 16px; background: var(--forge-bg-secondary); border-radius: 8px; border: 1px solid var(--forge-border);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
          <svg width="20" height="20" fill="${card.color}" style="flex-shrink: 0;">
            ${card.icon}
          </svg>
          <div style="font-size: 0.75rem; color: var(--forge-text-muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">
            ${card.label}
          </div>
        </div>
        <div style="font-size: 1.5rem; font-weight: 700; color: var(--forge-text);">
          ${card.value}
        </div>
      </div>
    `).join('');
  }

  el.loadConfigStructureBtn?.addEventListener('click', async () => {
    await loadCategoryStatusDefault();
  });

  el.downloadConfigJsonBtn?.addEventListener('click', () => {
    if (!categoryStatusDefaultData) {
      showToast('warning', 'No Data', 'Please load the category status default data first');
      return;
    }

    const blob = new Blob([JSON.stringify(categoryStatusDefaultData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `category-status-default-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('success', 'Downloaded', 'Category status default JSON downloaded successfully');
  });

  el.copyConfigJsonBtn?.addEventListener('click', async () => {
    if (!categoryStatusDefaultData) {
      showToast('warning', 'No Data', 'Please load the category status default data first');
      return;
    }

    try {
      await navigator.clipboard.writeText(JSON.stringify(categoryStatusDefaultData, null, 2));
      showToast('success', 'Copied', 'JSON copied to clipboard');
    } catch (err) {
      showToast('error', 'Copy Failed', 'Failed to copy to clipboard');
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
await loadCategories();
await renderStatusSetsPreview();
await renderCustomFieldsPreview();

// Load activity log immediately (since it's the front page)
await loadActivityLog();

if (el.statusSetsTableBody) {
  el.statusSetsTableBody.appendChild(createStatusSetRow());
  el.statusSetsTableBody.appendChild(createAddStatusSetButton());
}
if (el.customFieldsTableBody) {
  el.customFieldsTableBody.appendChild(createCustomFieldRow());
  el.customFieldsTableBody.appendChild(createAddRowButton());
}
if (el.categoryCardsContainer) {
  el.categoryCardsContainer.appendChild(createCategoryCard());
  el.categoryCardsContainer.appendChild(createAddCategoryButton());
}

// ========================================
// TOGGLE BUTTON FUNCTIONALITY
// ========================================
let isShowingActivityLog = true;

el.toggleConfigBtn?.addEventListener('click', () => {
  isShowingActivityLog = !isShowingActivityLog;
  
  if (isShowingActivityLog) {
    // Show activity log, hide configuration
    el.activityLogView.hidden = false;
    el.configurationView.hidden = true;
    el.toggleConfigBtn.innerHTML = `
      <svg width="16" height="16" fill="currentColor">
        <path d="M3 9h6V3H3v6zm8 0h6V3h-6v6zM3 21h6v-6H3v6zm8 0h6v-6h-6v6z"/>
      </svg>
      Configuration
    `;
  } else {
    // Show configuration, hide activity log
    el.activityLogView.hidden = true;
    el.configurationView.hidden = false;
    el.toggleConfigBtn.innerHTML = `
      <svg width="16" height="16" fill="currentColor">
        <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18L19.82 8 12 11.82 4.18 8 12 4.18zM4 9.73l7 3.5v6.95l-7-3.5V9.73zm16 0v6.95l-7 3.5v-6.95l7-3.5z"/>
      </svg>
      Activity Log
    `;
  }
});
})();