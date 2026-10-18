// Lead Finder Pro Enterprise - PWA & Google Sheets Intelligence
let currentJobId = null;
let eventSource = null;
let allLeads = [];
let currentFilter = 'all'; // all | no-website | whatsapp | email | unclaimed
let searchQuery = '';
let selectedSearchMode = 'standard';
let taxonomyData = null;

// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => {
        console.log('[PWA] Service Worker registered:', reg.scope);
      })
      .catch(err => {
        console.warn('[PWA] Service Worker registration failed:', err);
      });
  });
}

// PWA Install Prompt Listener
let deferredInstallPrompt = null;
const installPwaBtn = document.getElementById('installPwaBtn');

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent Chrome mini-infobar on mobile
  e.preventDefault();
  deferredInstallPrompt = e;
  if (installPwaBtn) {
    installPwaBtn.style.display = 'inline-flex';
    if (window.lucide) lucide.createIcons();
  }
});

if (installPwaBtn) {
  installPwaBtn.addEventListener('click', async () => {
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      const { outcome } = await deferredInstallPrompt.userChoice;
      if (outcome === 'accepted') {
        showToast('LeadFinder Pro installed successfully!', '🎉');
        installPwaBtn.style.display = 'none';
      }
      deferredInstallPrompt = null;
    }
  });
}

window.addEventListener('appinstalled', () => {
  if (installPwaBtn) installPwaBtn.style.display = 'none';
  showToast('LeadFinder Pro is installed on your device!', '🚀');
});

// Online / Offline Status Handlers
const offlineNotice = document.getElementById('offlineNotice');
window.addEventListener('offline', () => {
  if (offlineNotice) offlineNotice.style.display = 'flex';
});
window.addEventListener('online', () => {
  if (offlineNotice) offlineNotice.style.display = 'none';
  showToast('Internet restored! Online.', '🌐');
});

// DOM Elements
const businessTypeInput = document.getElementById('businessTypeInput');
const locationInput = document.getElementById('locationInput');
const maxResultsSelect = document.getElementById('maxResultsSelect');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusDot = document.getElementById('statusDot');
const engineStatusText = document.getElementById('engineStatusText');

const statTotalLeads = document.getElementById('statTotalLeads');
const statNoWebsite = document.getElementById('statNoWebsite');
const statWhatsApp = document.getElementById('statWhatsApp');
const statEmail = document.getElementById('statEmail');
const statUnclaimed = document.getElementById('statUnclaimed');
const statNoWebPct = document.getElementById('statNoWebPct');
const statTargetSub = document.getElementById('statTargetSub');

const terminalSection = document.getElementById('terminalSection');
const terminalBody = document.getElementById('terminalBody');

const leadsTableBody = document.getElementById('leadsTableBody');
const emptyState = document.getElementById('emptyState');
const tableSearchInput = document.getElementById('tableSearchInput');

const filterDropdown = document.getElementById('filterDropdown');

const openGSheetsBtn = document.getElementById('openGSheetsBtn');
const exportExcelBtn = document.getElementById('exportExcelBtn');
const exportCsvBtn = document.getElementById('exportCsvBtn');
const copyPhonesBtn = document.getElementById('copyPhonesBtn');
const copyEmailsBtn = document.getElementById('copyEmailsBtn');

const toast = document.getElementById('toastMessage');
const toastIcon = document.getElementById('toastIcon');
const toastText = document.getElementById('toastText');

const taxonomyModal = document.getElementById('taxonomyModal');
const openTaxonomyBtn = document.getElementById('openTaxonomyBtn');
const closeTaxonomyBtn = document.getElementById('closeTaxonomyBtn');
const taxonomyModalBody = document.getElementById('taxonomyModalBody');
const taxonomySearch = document.getElementById('taxonomySearch');
const browseNicheLink = document.getElementById('browseNicheLink');
const browseLocationLink = document.getElementById('browseLocationLink');
const modalTabLocations = document.getElementById('modalTabLocations');
const modalTabCategories = document.getElementById('modalTabCategories');
const modalHeaderTitle = document.getElementById('modalHeaderTitle');

const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeToggleIcon = document.getElementById('themeToggleIcon');
const themeToggleText = document.getElementById('themeToggleText');

// Light Theme as Default, with Dark Mode Toggle
function initTheme() {
  const savedTheme = localStorage.getItem('leadfinder_theme') || 'light';
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark');
    themeToggleIcon.innerText = '☀️';
    themeToggleText.innerText = 'Light';
  } else {
    document.documentElement.classList.remove('dark');
    themeToggleIcon.innerText = '🌙';
    themeToggleText.innerText = 'Dark';
  }
}
initTheme();

themeToggleBtn.addEventListener('click', () => {
  const isDark = document.documentElement.classList.toggle('dark');
  if (isDark) {
    localStorage.setItem('leadfinder_theme', 'dark');
    themeToggleIcon.innerText = '☀️';
    themeToggleText.innerText = 'Light';
    showToast('Dark theme activated', '🌙', 1800);
  } else {
    localStorage.setItem('leadfinder_theme', 'light');
    themeToggleIcon.innerText = '🌙';
    themeToggleText.innerText = 'Dark';
    showToast('Light theme activated', '☀️', 1800);
  }
});

// Initialize Lucide Icons on Load
function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}
document.addEventListener('DOMContentLoaded', refreshIcons);
window.addEventListener('load', refreshIcons);

// Current Modal Tab: 'locations' or 'categories'
let currentModalTab = 'locations';

// Fetch Taxonomy Data from Backend
async function loadTaxonomy() {
  try {
    const res = await fetch('/api/taxonomy');
    if (res.ok) {
      taxonomyData = await res.json();
    }
  } catch (err) {
    console.error('Failed to load taxonomy:', err);
  }
}
loadTaxonomy();

// Category and Locations Browser Modal
function renderTaxonomyModal(filter = '') {
  if (!taxonomyData) return;
  const q = filter.toLowerCase().trim();
  let html = '';

  if (currentModalTab === 'locations') {
    // Show Locations
    if (taxonomyData.locations) {
      for (const [groupName, items] of Object.entries(taxonomyData.locations)) {
        const filteredItems = items.filter(i => i.toLowerCase().includes(q));
        if (filteredItems.length > 0) {
          html += `
            <div class="tax-group">
              <div class="tax-group-title">📍 ${escapeHtml(groupName)}</div>
              <div class="tax-chips">
                ${filteredItems.map(item => `
                  <button type="button" class="tax-chip" data-sel-loc="${escapeHtml(item)}">
                    ${escapeHtml(item)}
                  </button>
                `).join('')}
              </div>
            </div>
          `;
        }
      }
    }
    if (!html) {
      html = '<p style="color: var(--text-tertiary); padding: 12px 0;">No matching locations found.</p>';
    }
  } else {
    // Show Business Categories
    if (taxonomyData.industries) {
      for (const [groupName, items] of Object.entries(taxonomyData.industries)) {
        const filteredItems = items.filter(i => i.toLowerCase().includes(q));
        if (filteredItems.length > 0) {
          html += `
            <div class="tax-group">
              <div class="tax-group-title">💼 ${escapeHtml(groupName)}</div>
              <div class="tax-chips">
                ${filteredItems.map(item => `
                  <button type="button" class="tax-chip" data-sel-niche="${escapeHtml(item)}">
                    ${escapeHtml(item)}
                  </button>
                `).join('')}
              </div>
            </div>
          `;
        }
      }
    }
    if (!html) {
      html = '<p style="color: var(--text-tertiary); padding: 12px 0;">No matching categories found.</p>';
    }
  }

  taxonomyModalBody.innerHTML = html;
}

function setModalTab(tab) {
  currentModalTab = tab;
  taxonomySearch.value = '';
  if (tab === 'locations') {
    if (modalTabLocations) modalTabLocations.classList.add('active');
    if (modalTabCategories) modalTabCategories.classList.remove('active');
    if (modalHeaderTitle) modalHeaderTitle.innerText = 'Select Top Hub / Location';
    taxonomySearch.placeholder = 'Search cities, states, industrial hubs...';
  } else {
    if (modalTabCategories) modalTabCategories.classList.add('active');
    if (modalTabLocations) modalTabLocations.classList.remove('active');
    if (modalHeaderTitle) modalHeaderTitle.innerText = 'Select Business Category / Niche';
    taxonomySearch.placeholder = 'Search niches, stores, manufacturing...';
  }
  renderTaxonomyModal();
  refreshIcons();
}

if (modalTabLocations) modalTabLocations.addEventListener('click', () => setModalTab('locations'));
if (modalTabCategories) modalTabCategories.addEventListener('click', () => setModalTab('categories'));

openTaxonomyBtn.addEventListener('click', () => {
  taxonomyModal.style.display = 'flex';
  setModalTab('categories');
});

browseNicheLink.addEventListener('click', () => {
  taxonomyModal.style.display = 'flex';
  setModalTab('categories');
});

browseLocationLink.addEventListener('click', () => {
  taxonomyModal.style.display = 'flex';
  setModalTab('locations');
});

closeTaxonomyBtn.addEventListener('click', () => {
  taxonomyModal.style.display = 'none';
});
window.addEventListener('click', (e) => {
  if (e.target === taxonomyModal) taxonomyModal.style.display = 'none';
});

taxonomySearch.addEventListener('input', (e) => {
  renderTaxonomyModal(e.target.value);
});

taxonomyModalBody.addEventListener('click', (e) => {
  const nicheChip = e.target.closest('[data-sel-niche]');
  if (nicheChip) {
    businessTypeInput.value = nicheChip.getAttribute('data-sel-niche');
    taxonomyModal.style.display = 'none';
    businessTypeInput.focus();
    return;
  }
  const locChip = e.target.closest('[data-sel-loc]');
  if (locChip) {
    locationInput.value = locChip.getAttribute('data-sel-loc');
    taxonomyModal.style.display = 'none';
    locationInput.focus();
    return;
  }
});

// Toast notification helper
let toastTimeout = null;
function showToast(msg, icon = 'ℹ️', duration = 3000) {
  if (toastTimeout) clearTimeout(toastTimeout);
  toastIcon.innerText = icon;
  toastText.innerText = msg;
  toast.classList.add('show');
  toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// Utility: HTML Escape
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Engine Status Badge update
function setEngineRunning(running) {
  if (running) {
    statusDot.classList.add('active');
    engineStatusText.innerText = 'Extracting Leads...';
    startBtn.disabled = true;
    stopBtn.style.display = 'inline-flex';
    terminalSection.style.display = 'block';
  } else {
    statusDot.classList.remove('active');
    engineStatusText.innerText = 'Engine Ready';
    startBtn.disabled = false;
    stopBtn.style.display = 'none';
  }
}

// Append Terminal Log
function appendTerminalLog(message, level = 'info') {
  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = `log-entry ${level}`;
  div.innerHTML = `<span style="color: var(--text-tertiary); margin-right: 8px;">[${time}]</span> ${escapeHtml(message)}`;
  terminalBody.appendChild(div);
  terminalBody.scrollTop = terminalBody.scrollHeight;
}

// Update KPI Stats
function updateStats() {
  const total = allLeads.length;
  const noWeb = allLeads.filter(l => l && l.has_website === 'NO').length;
  const waReady = allLeads.filter(l => l && l.whatsapp_url && l.whatsapp_url.length > 0).length;
  const emails = allLeads.filter(l => l && l.email && l.email.includes('@')).length;
  const unclaimed = allLeads.filter(l => l && l.profile_status && l.profile_status.includes('Unclaimed')).length;

  statTotalLeads.innerText = total;
  statNoWebsite.innerText = noWeb;
  statWhatsApp.innerText = waReady;
  statEmail.innerText = emails;
  statUnclaimed.innerText = unclaimed;

  if (total > 0) {
    const pct = Math.round((noWeb / total) * 100);
    statNoWebPct.innerText = `${pct}% Need Websites`;
  } else {
    statNoWebPct.innerText = 'Ready for Pitch';
  }

  // Update Filter Dropdown label counts
  if (filterDropdown && filterDropdown.options && filterDropdown.options.length >= 5) {
    filterDropdown.options[0].text = `📋 All Leads (${total})`;
    filterDropdown.options[1].text = `🔥 No Website / Hot Pitch (${noWeb})`;
    filterDropdown.options[2].text = `💬 WhatsApp Direct (${waReady})`;
    filterDropdown.options[3].text = `✉️ With Verified Email (${emails})`;
    filterDropdown.options[4].text = `🛡️ Unclaimed GMB Profiles (${unclaimed})`;
  }
}

// Render Leads Table
function renderTable() {
  let filtered = allLeads;

  // Filter Tab
  if (currentFilter === 'no-website') {
    filtered = filtered.filter(l => l.has_website === 'NO');
  } else if (currentFilter === 'whatsapp') {
    filtered = filtered.filter(l => l.whatsapp_url && l.whatsapp_url.length > 0);
  } else if (currentFilter === 'email') {
    filtered = filtered.filter(l => l.email && l.email.includes('@'));
  } else if (currentFilter === 'unclaimed') {
    filtered = filtered.filter(l => l.profile_status && l.profile_status.includes('Unclaimed'));
  }

  // Search input filter
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(l => 
      (l.name && l.name.toLowerCase().includes(q)) ||
      (l.phone && l.phone.toLowerCase().includes(q)) ||
      (l.category && l.category.toLowerCase().includes(q)) ||
      (l.address && l.address.toLowerCase().includes(q)) ||
      (l.email && l.email.toLowerCase().includes(q))
    );
  }

  leadsTableBody.innerHTML = '';

  if (filtered.length === 0) {
    emptyState.style.display = 'block';
    refreshIcons();
    return;
  }
  emptyState.style.display = 'none';

  filtered.forEach((lead, idx) => {
    const tr = document.createElement('tr');

    // Website badge
    let webBadge = '';
    if (lead.has_website === 'NO') {
      webBadge = `<span class="badge-no-web"><i data-lucide="alert-circle" style="width: 12px; height: 12px;"></i> No Website (Pitch)</span>`;
    } else {
      const cleanUrl = lead.website.replace(/^https?:\/\//i, '').replace(/^www\./i, '').split('/')[0];
      webBadge = `<a href="${escapeHtml(lead.website)}" target="_blank" rel="noopener" class="badge-has-web" title="Visit: ${escapeHtml(lead.website)}">
        <i data-lucide="globe" style="width: 12px; height: 12px;"></i> ${escapeHtml(cleanUrl)}
      </a>`;
    }

    // Profile status badge
    let profileBadge = '';
    if (lead.profile_status && lead.profile_status.includes('Unclaimed')) {
      profileBadge = `<span class="badge-unclaimed"><i data-lucide="shield-alert" style="width: 12px; height: 12px;"></i> Unclaimed (Opportunity)</span>`;
    } else {
      profileBadge = `<span class="badge-claimed"><i data-lucide="check-circle-2" style="width: 12px; height: 12px;"></i> Verified</span>`;
    }

    // Contact and WhatsApp button
    let contactCell = '<span style="color: var(--text-tertiary); font-size: 12px;">No Phone Listed</span>';
    if (lead.phone && lead.phone !== 'Not Available' && lead.phone !== 'No Phone') {
      const waButton = lead.whatsapp_url ? `
        <a href="${escapeHtml(lead.whatsapp_url)}" target="_blank" rel="noopener" class="wa-btn" title="Open direct WhatsApp chat">
          <i data-lucide="message-circle" style="width: 11px; height: 11px;"></i> WhatsApp
        </a>
      ` : '';

      // Social Media Icons if available
      let socialsHtml = '';
      if (lead.socials) {
        if (lead.socials.instagram) {
          socialsHtml += `<a href="${escapeHtml(lead.socials.instagram)}" target="_blank" rel="noopener" class="social-icon-btn ig" title="Instagram Profile"><i data-lucide="instagram"></i></a>`;
        }
        if (lead.socials.facebook) {
          socialsHtml += `<a href="${escapeHtml(lead.socials.facebook)}" target="_blank" rel="noopener" class="social-icon-btn fb" title="Facebook Page"><i data-lucide="facebook"></i></a>`;
        }
        if (lead.socials.linkedin) {
          socialsHtml += `<a href="${escapeHtml(lead.socials.linkedin)}" target="_blank" rel="noopener" class="social-icon-btn li" title="LinkedIn Profile"><i data-lucide="linkedin"></i></a>`;
        }
      }

      contactCell = `
        <div style="display: flex; align-items: center; white-space: nowrap; flex-wrap: wrap; gap: 4px;">
          <a href="tel:${escapeHtml(lead.phone)}" class="phone-link">${escapeHtml(lead.phone)}</a>
          ${waButton}
          ${socialsHtml}
        </div>
      `;
    }

    // Email
    let emailCell = '<span style="color: var(--text-tertiary);">-</span>';
    if (lead.email && lead.email.includes('@')) {
      emailCell = `<a href="mailto:${escapeHtml(lead.email)}" class="email-pill" title="Send Email">
        <i data-lucide="mail" style="width: 12px; height: 12px;"></i> ${escapeHtml(lead.email)}
      </a>`;
    } else if (lead.email === 'Scanning...') {
      emailCell = `<span style="color: var(--text-tertiary); font-size: 11px;">Scanning...</span>`;
    }

    // Rating
    let ratingDisplay = '<span style="color: var(--text-tertiary);">-</span>';
    if (lead.rating && lead.rating !== 'N/A') {
      ratingDisplay = `
        <div class="rating-badge">
          <span>★</span> <span>${escapeHtml(lead.rating)}</span>
          <span class="reviews-cnt">(${escapeHtml(lead.reviews_count || '0')})</span>
        </div>
      `;
    }

    // Maps link
    let mapsLink = '-';
    if (lead.maps_url && lead.maps_url.startsWith('http')) {
      mapsLink = `<a href="${escapeHtml(lead.maps_url)}" target="_blank" rel="noopener" class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" title="Open in Google Maps">
        <i data-lucide="map" style="width: 13px; height: 13px;"></i> View
      </a>`;
    }

    tr.innerHTML = `
      <td style="color: var(--text-tertiary); font-size: 12px; font-weight: 600;">${idx + 1}</td>
      <td>
        <div class="business-name">${escapeHtml(lead.name)}</div>
        <div class="business-category">${escapeHtml(lead.category)}</div>
      </td>
      <td>${contactCell}</td>
      <td>${emailCell}</td>
      <td>${webBadge}</td>
      <td>${profileBadge}</td>
      <td>${ratingDisplay}</td>
      <td><div class="address-text">${escapeHtml(lead.address)}</div></td>
      <td style="text-align: center;">${mapsLink}</td>
    `;

    leadsTableBody.appendChild(tr);
  });

  refreshIcons();
}

// 🟢 GOOGLE SHEETS 1-CLICK INTEGRATION
openGSheetsBtn.addEventListener('click', () => {
  if (allLeads.length === 0) {
    showToast('Search leads first to export to Google Sheets.', '⚠️');
    return;
  }

  // Tab-Separated Values (TSV) pastes seamlessly into Google Sheets cells
  const headers = [
    "S.No",
    "Business Name",
    "Category",
    "Phone Number",
    "WhatsApp Link",
    "Email Address",
    "Has Website?",
    "Website URL",
    "Google Profile Status",
    "Rating",
    "Reviews Count",
    "Full Address",
    "Google Maps URL"
  ];

  const rows = allLeads.map((l, i) => [
    i + 1,
    (l.name || '').replace(/[\t\n]/g, ' '),
    (l.category || '').replace(/[\t\n]/g, ' '),
    (l.phone || '').replace(/[\t\n]/g, ' '),
    l.whatsapp_url || '',
    (l.email && l.email.includes('@')) ? l.email : '',
    l.has_website || 'NO',
    (l.website === 'None (Opportunity)') ? '' : (l.website || ''),
    l.profile_status || '',
    l.rating || '',
    l.reviews_count || '',
    (l.address || '').replace(/[\t\n]/g, ' '),
    l.maps_url || ''
  ]);

  const tsvContent = [
    headers.join('\t'),
    ...rows.map(r => r.join('\t'))
  ].join('\n');

  navigator.clipboard.writeText(tsvContent).then(() => {
    window.open('https://sheets.new', '_blank');
    showToast('Copied all data! Press Ctrl + V in the opened Google Sheet.', '🟢', 5500);
  }).catch(() => {
    window.open('https://sheets.new', '_blank');
    showToast('Opened Google Sheet! Download CSV/Excel below.', '🟢');
  });
});

// Start Scraping Action
startBtn.addEventListener('click', async () => {
  const businessType = businessTypeInput.value.trim();
  const location = locationInput.value.trim();
  const maxResults = parseInt(maxResultsSelect.value, 10) || 20;

  if (!businessType) {
    showToast('Please enter a business category or niche', '⚠️');
    businessTypeInput.focus();
    return;
  }
  if (!location) {
    showToast('Please enter a location or city', '⚠️');
    locationInput.focus();
    return;
  }

  allLeads = [];
  terminalBody.innerHTML = '';
  statTargetSub.innerText = `Target: ${maxResults}`;
  updateStats();
  renderTable();
  setEngineRunning(true);
  appendTerminalLog(`Initiating search: "${businessType}" in "${location}" [Mode: ${selectedSearchMode}] (Target: ${maxResults} unique leads)...`, 'info');

  try {
    const res = await fetch('/api/scrape/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_type: businessType,
        location: location,
        max_results: maxResults,
        headless: true,
        search_mode: selectedSearchMode
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to start scraping engine');
    }

    currentJobId = data.job_id;
    exportExcelBtn.href = `/api/scrape/export/excel/${currentJobId}`;
    exportCsvBtn.href = `/api/scrape/export/csv/${currentJobId}`;

    // Connect to Server-Sent Events (SSE) stream
    if (eventSource) {
      eventSource.close();
    }

    eventSource = new EventSource(`/api/scrape/stream/${currentJobId}`);

    eventSource.addEventListener('log', (e) => {
      try {
        const payload = JSON.parse(e.data);
        appendTerminalLog(payload.message || e.data, 'info');
      } catch (_) {}
    });

    eventSource.addEventListener('status', (e) => {
      try {
        const payload = JSON.parse(e.data);
        appendTerminalLog(payload.message || e.data, 'info');
      } catch (_) {}
    });

    eventSource.addEventListener('lead', (e) => {
      try {
        const payload = JSON.parse(e.data);
        const lead = (payload && payload.data) ? payload.data : payload;
        if (!lead || typeof lead !== 'object') return;
        allLeads.push(lead);
        updateStats();
        renderTable();
        appendTerminalLog(`Verified Lead #${allLeads.length}: ${lead.name || 'Business'} (${lead.phone || 'No phone'}) [Web: ${lead.has_website || 'NO'}]`, 'success');
      } catch (err) {
        console.error('Error handling lead event:', err);
      }
    });

    eventSource.addEventListener('complete', (e) => {
      try {
        const payload = JSON.parse(e.data);
        appendTerminalLog(`Scraping job completed! Captured ${allLeads.length} verified unique leads.`, 'success');
        setEngineRunning(false);
        eventSource.close();
        showToast(`Scraped ${allLeads.length} genuine leads successfully!`, '🎉');
      } catch (_) {}
    });

    eventSource.addEventListener('error', (e) => {
      try {
        const payload = JSON.parse(e.data);
        appendTerminalLog(`Error: ${payload.message}`, 'error');
      } catch (_) {
        appendTerminalLog('Stream closed or connection interrupted.', 'warning');
      }
      setEngineRunning(false);
      if (eventSource) eventSource.close();
    });

    eventSource.onerror = (err) => {
      console.warn('SSE Error event:', err);
      setEngineRunning(false);
      if (eventSource) eventSource.close();
    };

  } catch (err) {
    appendTerminalLog(`Error: ${err.message}`, 'error');
    showToast(err.message, '❌');
    setEngineRunning(false);
  }
});

// Stop Scraping Action
stopBtn.addEventListener('click', async () => {
  if (!currentJobId) return;
  appendTerminalLog('Stopping scraper gracefully...', 'warning');
  try {
    await fetch(`/api/scrape/stop/${currentJobId}`, { method: 'POST' });
    showToast('Stopping scraping engine...', '⏹');
  } catch (err) {
    console.error(err);
  }
});

// Filter Dropdown Change Listener
if (filterDropdown) {
  filterDropdown.addEventListener('change', () => {
    currentFilter = filterDropdown.value;
    renderTable();
  });
}

// Search Input
tableSearchInput.addEventListener('input', (e) => {
  searchQuery = e.target.value.trim();
  renderTable();
});

// Copy Phone Numbers
copyPhonesBtn.addEventListener('click', () => {
  const phones = allLeads
    .map(l => l.phone)
    .filter(p => p && p !== 'Not Available' && p !== 'No Phone');
  const unique = [...new Set(phones)];

  if (unique.length === 0) {
    showToast('No phone numbers available.', '⚠️');
    return;
  }
  navigator.clipboard.writeText(unique.join('\n')).then(() => {
    showToast(`Copied ${unique.length} verified phone numbers!`, '📞');
  });
});

// Copy Emails
copyEmailsBtn.addEventListener('click', () => {
  const emails = allLeads
    .map(l => l.email)
    .filter(e => e && e.includes('@'));
  const unique = [...new Set(emails)];

  if (unique.length === 0) {
    showToast('No emails discovered yet.', '⚠️');
    return;
  }
  navigator.clipboard.writeText(unique.join('\n')).then(() => {
    showToast(`Copied ${unique.length} verified email addresses!`, '📧');
  });
});
