// ═══════════════════════════════════════════════════════════
//   PREMIUM UI JAVASCRIPT
//   Includes Themes, GSAP animations, tsParticles, and all API Logic
// ═══════════════════════════════════════════════════════════

// ─── Theme Management ────────────────────────────────────
const themeBtns = document.querySelectorAll('.theme-btn');
const htmlEl = document.documentElement;

themeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    // Remove active
    themeBtns.forEach(b => b.classList.remove('active'));
    // Add active
    btn.classList.add('active');
    // Set theme
    const theme = btn.getAttribute('data-theme');
    htmlEl.setAttribute('data-theme', theme);
    localStorage.setItem('ai_worker_theme', theme);

    // Animate change with GSAP
    gsap.fromTo("body", { opacity: 0.8 }, { duration: 0.5, opacity: 1, ease: "power2.out" });
  });
});

// Load saved theme
const savedTheme = localStorage.getItem('ai_worker_theme');
if (savedTheme) {
  htmlEl.setAttribute('data-theme', savedTheme);
  themeBtns.forEach(b => {
    if (b.getAttribute('data-theme') === savedTheme) b.classList.add('active');
    else b.classList.remove('active');
  });
}

// ─── Particles Configuration (tsParticles) ───────────────
async function loadParticles() {
  await tsParticles.load("tsparticles", {
    fpsLimit: 60,
    interactivity: {
      events: { onHover: { enable: true, mode: "repulse" }, resize: true },
      modes: { repulse: { distance: 100, duration: 0.4 } }
    },
    particles: {
      color: { value: "#ffffff" },
      links: { color: "#ffffff", distance: 150, enable: true, opacity: 0.35, width: 2.5 },
      move: { direction: "none", enable: true, outModes: { default: "bounce" }, random: false, speed: 0.8, straight: false },
      number: { density: { enable: true, area: 800 }, value: 40 },
      opacity: { value: 0.1 },
      shape: { type: "circle" },
      size: { value: { min: 1, max: 2 } }
    },
    detectRetina: true
  });
}
window.addEventListener('DOMContentLoaded', loadParticles);

// ─── Sidebar Toggle ──────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
sidebarToggle.addEventListener('click', () => {
  sidebar.classList.toggle('collapsed');
});

// ─── Sidebar Tabs ────────────────────────────────────────
const stabs = document.querySelectorAll('.stab');
const spanels = document.querySelectorAll('.sidebar-panel');
stabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const targetId = tab.getAttribute('data-tab');
    
    // Switch active states
    stabs.forEach(t => t.classList.toggle('active', t === tab));
    spanels.forEach(p => p.classList.toggle('active', p.id === targetId));
    
    // Refresh data when switching to specific panels
    if (targetId === 'panel-history') loadHistory();
    if (targetId === 'panel-summaries') loadSummaries();
  });
});

// ─── Global State & DOM ───────────────────────────────────
const chatContainer = document.getElementById('chatContainer');
const welcomeScreen = document.getElementById('welcomeScreen');
const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');

const modelSelector = document.getElementById('modelSelector');
const chatModeSelector = document.getElementById('chatModeSelector');
const compareToggle = document.getElementById('compareToggle');
const modelBadge = document.getElementById('modelBadge');

// Update Model Badge
modelSelector.addEventListener('change', (e) => {
  const selectedText = e.target.options[e.target.selectedIndex].text;
  modelBadge.textContent = selectedText;
});

// Auto-resize input
queryInput.addEventListener('input', function () {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  if (this.value.trim() === '') this.style.height = 'auto';
});

// Submit on Enter (Shift+Enter for newline)
queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit'));
  }
});

// Focus helper
window.fillQuery = function (element) {
  queryInput.value = element.textContent.trim().replace(/^[\u2700-\u27BF|📄|🔍|⚠️]\s*/, ''); // Remove emojis
  queryInput.focus();
};

// ─── API Integrations ────────────────────────────────────

// Render Markdown using Marked.js
function formatResponse(text) {
  if (!text) return "";
  return marked.parse(text);
}

// Ensure welcome screen gets hidden
function hideWelcome() {
  if (welcomeScreen && welcomeScreen.style.display !== 'none') {
    gsap.to(welcomeScreen, {
      opacity: 0, duration: 0.3, onComplete: () => {
        welcomeScreen.style.display = 'none';
        welcomeScreen.remove();
      }
    });
  }
}

// Scroll chat to bottom
function scrollToBottom() {
  setTimeout(() => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }, 50);
}

// ─── Appending Messages ──────────────────────────────────
function appendUserMessage(text) {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'message user-msg';
  div.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
    <div class="msg-body">
      <div class="msg-role">You</div>
      <div class="msg-content">${text}</div>
    </div>
  `;
  chatContainer.appendChild(div);
  scrollToBottom();
}

function appendAIMessage(htmlContent, meta = null, actions = true, isProfileAudit = false) {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'message ai-msg';

  let metaHtml = '';
  if (meta) {
    metaHtml = '<div class="msg-meta">';
    // Time label is enough, we don't need misleading model names
    if (meta.time) metaHtml += `<span class="meta-chip time"><i class="fa-solid fa-stopwatch"></i> ${meta.time}ms</span>`;
    if (meta.cached) metaHtml += `<span class="meta-chip cached"><i class="fa-solid fa-bolt"></i> Cached</span>`;
    if (meta.sources && meta.sources.length) {
      meta.sources.forEach(src => {
        metaHtml += `<span class="meta-chip source"><i class="fa-solid fa-file-pdf"></i> ${src}</span>`;
      });
    }
    metaHtml += '</div>';

    if (meta.chunks && meta.chunks.length > 0 && !meta.chunks[0].includes("FULL DOCUMENT CONTEXT")) {
      metaHtml += `
        <div class="chunks-badge" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'flex' : 'none'">
           <i class="fa-solid fa-layer-group"></i> View ${meta.chunks.length} Context Chunks
        </div>
        <div class="chunks-container" style="display:none;">
          ${meta.chunks.map((c, i) => {
        let conf = 'N/A';
        if (meta.scores && meta.scores[i] !== undefined) {
          conf = Math.max(0, 100 - (meta.scores[i] * 100)).toFixed(1) + '%';
        }
        return `
            <div class="chunk-item">
              <div class="chunk-score" style="margin-bottom:4px; font-size:11px; color:var(--accent);">✦ Confidence: ${conf} (distance: ${meta.scores[i]})</div>
              ${c}
            </div>
            `;
      }).join('')}
        </div>
       `;
    }
  }

  let actionsHtml = '';
  if (actions && htmlContent && htmlContent.trim() !== "") {
    const rawContent = encodeURIComponent(htmlContent);
    actionsHtml = `
      <div class="msg-actions">
        <button class="msg-action-btn" onclick="takeAction('email', decodeURIComponent('${rawContent}'))"><i class="fa-regular fa-envelope"></i> Email Report</button>
        <button class="msg-action-btn" onclick="takeAction('export', decodeURIComponent('${rawContent}'))"><i class="fa-solid fa-file-export"></i> Professional Brief</button>
        ${isProfileAudit ? `<button class="msg-action-btn" onclick="appendSheetFromAudit()" title="Append this profile to Google Sheet"><i class="fa-solid fa-file-export"></i> Append to Sheet</button>` : ''}
      </div>
    `;
  }

  div.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-brain"></i></div>
    <div class="msg-body">
      <div class="msg-role">AI Worker</div>
      <div class="msg-content">${htmlContent}</div>
      ${metaHtml}
      ${actionsHtml}
    </div>
  `;
  chatContainer.appendChild(div);
  scrollToBottom();
}

function createStreamingAIMessage() {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'message ai-msg stream-msg';

  div.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-brain"></i></div>
    <div class="msg-body" style="width:100%;">
      <div class="msg-role">AI Worker (Typing...) <i class="fa-solid fa-circle-notch fa-spin"></i></div>
      <div class="msg-content stream-content" style="min-height: 40px; margin-bottom: 5px;"></div>
      <div class="stream-meta"></div>
      <div class="stream-actions"></div>
    </div>
  `;
  chatContainer.appendChild(div);
  scrollToBottom();
  return {
    div,
    contentEl: div.querySelector('.stream-content'),
    metaEl: div.querySelector('.stream-meta'),
    actionsEl: div.querySelector('.stream-actions'),
    roleEl: div.querySelector('.msg-role')
  };
}

function appendThinking() {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'message ai-msg thinking-msg';
  div.id = 'thinkingMsg';
  div.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-brain"></i></div>
    <div class="msg-body">
      <div class="msg-content" style="padding:0; background:transparent; border:none;">
        <div class="thinking-dot"><span></span><span></span><span></span></div>
      </div>
      <div class="thinking-label">Synthesizing response...</div>
    </div>
  `;
  chatContainer.appendChild(div);
  scrollToBottom();
  return div;
}

function removeThinking() {
  const el = document.getElementById('thinkingMsg');
  if (el) el.remove();
}

function appendCompareMessage(ragData, directData) {
  hideWelcome();
  const div = document.createElement('div');
  div.className = 'message ai-msg';

  const ragHtml = formatResponse(ragData.answer);
  const directHtml = formatResponse(directData.answer);

  div.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid fa-scale-balanced"></i></div>
    <div class="msg-body" style="width: 100%;">
      <div class="msg-role">Comparison Mode</div>
      <div class="compare-grid">
        <div class="compare-col compare-rag">
          <div class="compare-col-header"><i class="fa-solid fa-database"></i> Augmented (RAG) [${ragData.response_time_ms}ms]</div>
          <div class="compare-col-body msg-content">${ragHtml}</div>
        </div>
        <div class="compare-col compare-direct">
          <div class="compare-col-header"><i class="fa-solid fa-microchip"></i> Direct LLM (No RAG) [${directData.response_time_ms}ms]</div>
          <div class="compare-col-body msg-content">${directHtml}</div>
        </div>
      </div>
    </div>
  `;
  chatContainer.appendChild(div);
  scrollToBottom();
}

// ─── Chat Submission ─────────────────────────────────────
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  const mode = chatModeSelector.value;
  const model = modelSelector.value;
  const isCompare = compareToggle.checked;

  appendUserMessage(query);
  queryInput.value = '';
  queryInput.style.height = 'auto';
  queryInput.focus();

  appendThinking();

  try {
    if (isCompare) {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });
      const data = await res.json();
      removeThinking();
      if (data.error) throw new Error(data.error);
      appendCompareMessage(data.rag, data.direct);
    } else {
      const res = await fetch('/api/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, mode: mode, model: model })
      });
      removeThinking();

      const streamUI = createStreamingAIMessage();
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let answerText = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let parts = buffer.split('\n\n');
        buffer = parts.pop();

        for (let part of parts) {
          if (part.startsWith('data: ')) {
            try {
              const data = JSON.parse(part.substring(6));

              if (data.type === 'error') {
                streamUI.contentEl.innerHTML = `<div style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.content}</div>`;
              } else if (data.type === 'chunk') {
                answerText += data.content;
                streamUI.contentEl.innerHTML = formatResponse(answerText);
                scrollToBottom();
              } else if (data.type === 'metadata') {
                streamUI.roleEl.textContent = 'AI Worker'; // remove spinner
                const m = data.data;
                m.modeStr = mode === 'long_context' ? 'Long Context Window' : (mode === 'direct' ? 'Direct LLM' : 'RAG Pipeline');

                let metaHtml = '<div class="msg-meta">';
                metaHtml += `<span class="meta-chip mode"><i class="fa-solid fa-microchip"></i> ${m.modeStr}</span>`;
                if (m.response_time_ms) metaHtml += `<span class="meta-chip time"><i class="fa-solid fa-stopwatch"></i> ${m.response_time_ms}ms</span>`;
                if (m.cached) metaHtml += `<span class="meta-chip cached"><i class="fa-solid fa-bolt"></i> Cached</span>`;
                if (m.sources && m.sources.length) {
                  m.sources.forEach(src => {
                    metaHtml += `<span class="meta-chip source"><i class="fa-solid fa-file-pdf"></i> ${src}</span>`;
                  });
                }
                metaHtml += '</div>';
                if (m.chunks && m.chunks.length > 0 && !m.chunks[0].includes("FULL DOCUMENT CONTEXT")) {
                  metaHtml += `
                    <div class="chunks-badge" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'flex' : 'none'">
                       <i class="fa-solid fa-layer-group"></i> View ${m.chunks.length} Context Chunks
                    </div>
                    <div class="chunks-container" style="display:none; margin-top:8px;">
                      ${m.chunks.map((c, i) => {
                    let conf = 'N/A';
                    if (m.scores && m.scores[i] !== undefined) {
                      conf = Math.max(0, 100 - (m.scores[i] * 100)).toFixed(1) + '%';
                    }
                    return `
                        <div class="chunk-item">
                          <div class="chunk-score" style="margin-bottom:4px; font-size:11px; color:var(--accent);">✦ Confidence: ${conf} (distance: ${m.scores[i]})</div>
                          <div style="font-size:12px;">${c}</div>
                        </div>
                        `;
                  }).join('')}
                    </div>
                   `;
                }
                streamUI.metaEl.innerHTML = metaHtml;

                const rawContent = encodeURIComponent(answerText);
                streamUI.actionsEl.innerHTML = `
                  <div class="msg-actions" style="margin-top:10px;">
                    <button class="msg-action-btn" onclick="takeAction('email', decodeURIComponent('${rawContent}'))"><i class="fa-regular fa-envelope"></i> Email Report</button>
                    <button class="msg-action-btn" onclick="takeAction('export', decodeURIComponent('${rawContent}'))"><i class="fa-solid fa-file-export"></i> Professional Brief</button>
                  </div>
                 `;
                scrollToBottom();
              }
            } catch (e) {
              console.error("SSE Parse Error", e);
            }
          }
        }
      }
    }
    loadHistory(); // Refresh history
  } catch (error) {
    removeThinking();
    appendAIMessage(`<div style="color:var(--danger)"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${error.message}</div>`, null, false);
  }
});

// ─── File Upload ─────────────────────────────────────────
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const uploadSpanText = document.getElementById('uploadSpanText');
const uploadStatus = document.getElementById('uploadStatus');
const uploadSpin = document.getElementById('uploadSpin');
const uploadBoltIcon = document.getElementById('uploadBoltIcon');
const uploadBtnText = document.getElementById('uploadBtnText');
const uploadBtn = document.getElementById('uploadBtn');

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    uploadSpanText.textContent = fileInput.files[0].name;
    uploadSpanText.style.color = 'var(--accent)';
  } else {
    uploadSpanText.textContent = 'Drop PDF or TXT here';
    uploadSpanText.style.color = 'var(--text-secondary)';
  }
});

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (fileInput.files.length === 0) {
    uploadStatus.innerHTML = '<span class="error">Select a file first.</span>';
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  uploadSpin.style.display = 'inline-block';
  uploadBoltIcon.style.display = 'none';
  uploadBtnText.textContent = 'Ingesting...';
  uploadBtn.disabled = true;
  uploadStatus.innerHTML = '';

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Upload failed');

    uploadStatus.innerHTML = `<span class="success"><i class="fa-solid fa-check"></i> ${data.message}</span>`;
    checkKbStatus();
    loadSummaries();

    fileInput.value = '';
    uploadSpanText.textContent = 'Drop PDF or TXT here';
    uploadSpanText.style.color = 'var(--text-secondary)';

  } catch (error) {
    uploadStatus.innerHTML = `<span class="error"><i class="fa-solid fa-circle-xmark"></i> ${error.message}</span>`;
  } finally {
    uploadSpin.style.display = 'none';
    uploadBoltIcon.style.display = 'inline-block';
    uploadBtnText.textContent = 'Ingest';
    uploadBtn.disabled = false;
  }
});

// ─── Agentic Audit Buttons ───────────────────────────────
document.querySelectorAll('.audit-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const type = btn.getAttribute('data-type');
    const label = type === 'risk' ? 'Risk Audit' : (type === 'legal' ? 'Legal Audit' : 'Professional Profile');
    appendUserMessage(`*Triggered ${label}*`);
    appendThinking();
    try {
      const model = document.getElementById('modelSelector').value;
      
      const res = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: type, model: model })
      });
      const data = await res.json();
      removeThinking();
      if (data.error) throw new Error(data.error);

      const isProf = type === 'professional';
      const formattedAudit = formatResponse(`**${type.toUpperCase()} AUDIT REPORT**\n\n${data.audit}`);
      appendAIMessage(formattedAudit, null, true, isProf);
      loadHistory();
    } catch (error) {
      removeThinking();
      appendAIMessage(`<div style="color:var(--danger)">Error running audit: ${error.message}</div>`, null, false);
    }
  });
});

// ─── Email / Export Actions ──────────────────────────────
window.takeAction = async function (actionType, rawContent) {
  const recipient = prompt("Enter recipient email address:");
  if (!recipient) return;

  appendUserMessage(`*Executing ${actionType.toUpperCase()} action to ${recipient}...*`);
  appendThinking();

  try {
    const res = await fetch('/api/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: actionType,
        content: rawContent,
        recipient: recipient
      })
    });
    const data = await res.json();
    removeThinking();
    if (res.ok && data.success) {
      appendAIMessage(`✅ Action successful! ${data.message}`, null, false);
    } else {
      throw new Error(data.message || data.error || 'Action failed');
    }
  } catch (e) {
    removeThinking();
    appendAIMessage(`❌ Action failed: ${e.message}`, null, false);
  }
};

// ─── KB Status ───────────────────────────────────────────
const kbDot = document.getElementById('kbDot');
const kbStatusText = document.getElementById('kbStatusText');
const clearKbBtn = document.getElementById('clearKbBtn');
async function checkKbStatus() {
  try {
    const res = await fetch('/api/kb-status');
    const data = await res.json();
    if (data.status === 'ready' && data.doc_count > 0) {
      kbDot.className = 'kb-dot kb-ready';
      kbStatusText.textContent = `${data.file_count} files (${data.doc_count} chunks)`;
      clearKbBtn.style.display = 'inline-flex';
    } else {
      kbDot.className = 'kb-dot kb-empty';
      kbStatusText.textContent = 'Knowledge Base Empty';
      clearKbBtn.style.display = 'none';
      document.getElementById('historyList').innerHTML = '<p class="hint-text">No queries yet.</p>';
      document.getElementById('summariesList').innerHTML = '<p class="hint-text">No summaries yet.</p>';
      document.getElementById('queryStats').innerHTML = '';
    }
  } catch (e) {
    kbStatusText.textContent = 'Status error';
  }
}

clearKbBtn.addEventListener('click', async () => {
  if (!confirm('Are you sure you want to clear the entire knowledge base?')) return;
  try {
    await fetch('/api/clear-kb', { method: 'POST' });
    checkKbStatus();
    loadHistory();
    loadSummaries();
  } catch (e) {
    alert("Failed to clear KB");
  }
});

// ─── Evaluation / t-SNE Modal ────────────────────────────
const evalBtn = document.getElementById('evalBtn');
const evalData = document.getElementById('evalData');
const mrrValue = document.getElementById('mrrValue');
const ndcgValue = document.getElementById('ndcgValue');
const tsneModal = document.getElementById('tsneModal');
const tsneImgContainer = document.getElementById('tsneImgContainer');
const closeModal = document.getElementById('closeModal');

evalBtn.addEventListener('click', async () => {
  const originalHtml = evalBtn.innerHTML;
  evalBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Eval...';
  evalBtn.disabled = true;

  try {
    const res = await fetch('/api/evaluate');
    const data = await res.json();

    evalData.style.display = 'flex';
    mrrValue.textContent = data.metrics.mrr.toFixed(2);
    ndcgValue.textContent = data.metrics.ndcg.toFixed(2);

    if (data.plot_url) {
      // Append timestamp to bust cache
      tsneImgContainer.innerHTML = `<img src="${data.plot_url}?t=${new Date().getTime()}" alt="t-SNE Embeddings">`;
      tsneModal.style.display = 'flex';
    } else {
      tsneImgContainer.innerHTML = '<p style="color:var(--text-muted); text-align:center;">Not enough data points for t-SNE plot yet. Upload at least 4 chunks.</p>';
      tsneModal.style.display = 'flex';
    }
  } catch (e) {
    alert("Evaluation failed.");
  } finally {
    evalBtn.innerHTML = originalHtml;
    evalBtn.disabled = false;
  }
});

closeModal.addEventListener('click', () => { tsneModal.style.display = 'none'; });
tsneModal.addEventListener('click', (e) => { if (e.target === tsneModal) tsneModal.style.display = 'none'; });

// ─── History & Summaries ─────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch('/api/query-history');
    const data = await res.json();
    const hl = document.getElementById('historyList');
    if (!data.history || data.history.length === 0) {
      hl.innerHTML = '<p class="hint-text">No queries yet.</p>';
    } else {
      hl.innerHTML = data.history.slice(0, 20).map(item => `
        <div class="history-item">
          <div class="h-query"><i class="fa-solid fa-user"></i> ${item.query}</div>
          <div class="h-meta">
            <span class="meta-chip">${item.mode === 'rag' ? '📚 RAG' : '🧠 Direct'}</span>
            <span class="meta-chip time-tag">${item.response_time_ms || 0}ms</span>
            ${item.num_chunks_retrieved ? `<span class="meta-chip">${item.num_chunks_retrieved} chunks</span>` : ''}
          </div>
        </div>
      `).join('');
    }

    const qs = document.getElementById('queryStats');
    if (data.stats) {
      const s = data.stats;
      qs.innerHTML = `
        <div class="stat-pill"><span class="num">${s.total_queries}</span><span class="lbl">Queries</span></div>
        <div class="stat-pill"><span class="num">${s.avg_response_time_ms}ms</span><span class="lbl">Avg Time</span></div>
      `;
    }
  } catch (e) {
    console.error("Failed to load history", e);
  }
}

async function loadSummaries() {
  try {
    const res = await fetch('/api/summaries');
    const data = await res.json();
    const sl = document.getElementById('summariesList');
    if (!data.summaries || data.summaries.length === 0) {
      sl.innerHTML = '<p class="hint-text">No summaries yet.</p>';
    } else {
      sl.innerHTML = data.summaries.map(item => `
        <div class="summary-card">
          <div class="summary-header">
            <i class="fa-solid fa-file-pdf"></i>
            <strong>${item.filename}</strong>
            <span class="summary-meta">${item.chunk_count} chunks · ${item.word_count} words</span>
          </div>
          <div class="summary-body">${formatResponse(item.summary_text)}</div>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error("Failed to load summaries", e);
  }
}

// ─── Init ────────────────────────────────────────────────
checkKbStatus();
loadHistory();
loadSummaries();

// ─── Append to sheet from audit ──────────────────────────────
async function appendSheetFromAudit() {
    const model = document.getElementById('modelSelector').value;
    alert("Triggered Append to Sheet Agent. Please wait while it processes the document...");
    try {
        const res = await fetch('/api/profile_audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: model })
        });
        const data = await res.json();
            
        if (data.success) {
            alert("✅ Successfully appended profile to Google Sheet!");
        } else {
            alert("❌ Action failed: " + (data.error || data.message));
        }
    } catch (e) {
        alert("❌ Error connecting to server.");
        console.error(e);
    }
}
