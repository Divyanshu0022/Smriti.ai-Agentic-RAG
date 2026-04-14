document.addEventListener('DOMContentLoaded', () => {
    // ─── DOM References ──────────────────────────────────────
    const uploadForm = document.getElementById('uploadForm');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadSpin = document.getElementById('uploadSpin');
    const fileInput = document.getElementById('fileInput');
    const uploadBtnText = document.querySelector('#uploadBtn span');

    const chatForm = document.getElementById('chatForm');
    const queryInput = document.getElementById('queryInput');
    const chatContainer = document.getElementById('chatContainer');
    
    const evalBtn = document.getElementById('evalBtn');
    const evalData = document.getElementById('evalData');
    const tsneModal = document.getElementById('tsneModal');

    const clearKbBtn = document.getElementById('clearKbBtn');
    const kbStatusText = document.getElementById('kbStatusText');
    const kbStatus = document.getElementById('kbStatus');

    const compareToggle = document.getElementById('compareToggle');
    const modeText = document.getElementById('modeText');
    const modelSelector = document.getElementById('modelSelector');
    const chatModeSelector = document.getElementById('chatModeSelector');

    // ─── Sidebar Tab Switching ───────────────────────────────
    document.querySelectorAll('.sidebar-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.sidebar-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');

            // Load data when switching tabs
            if (tab.dataset.tab === 'tab-summaries') loadSummaries();
            if (tab.dataset.tab === 'tab-history') loadHistory();
        });
    });

    // ─── File Selection UI ───────────────────────────────────
    const uploadAreaSpan = document.querySelector('.upload-area span');
    const uploadAreaIcon = document.querySelector('.upload-area i');
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadAreaSpan.textContent = fileInput.files[0].name;
            uploadAreaSpan.style.color = 'var(--accent)';
            uploadAreaIcon.className = 'fa-solid fa-file-circle-check cloud-icon';
            uploadAreaIcon.style.color = 'var(--accent)';
        } else {
            uploadAreaSpan.textContent = 'Select Document';
            uploadAreaSpan.style.color = '';
            uploadAreaIcon.className = 'fa-solid fa-cloud-arrow-up cloud-icon';
            uploadAreaIcon.style.color = '';
        }
    });

    // ─── Comparison Mode Toggle ──────────────────────────────
    compareToggle.addEventListener('change', () => {
        if (compareToggle.checked) {
            modeText.textContent = 'Compare Mode';
            modeText.style.color = 'var(--warning, #D29922)';
        } else {
            modeText.textContent = 'RAG Mode';
            modeText.style.color = '';
        }
    });

    // ─── Knowledge Base Status ───────────────────────────────
    async function refreshKbStatus() {
        try {
            const res = await fetch('/api/kb-status');
            const data = await res.json();
            if (data.status === 'ready' && data.doc_count > 0) {
                kbStatusText.textContent = `${data.doc_count} chunks · ${data.file_count || 0} file${(data.file_count || 0) !== 1 ? 's' : ''}`;
                kbStatus.className = 'kb-status kb-ready';
                clearKbBtn.style.display = 'flex';
            } else {
                kbStatusText.textContent = 'No documents loaded';
                kbStatus.className = 'kb-status kb-empty';
                clearKbBtn.style.display = 'none';
            }
        } catch {
            kbStatusText.textContent = 'Status unavailable';
            kbStatus.className = 'kb-status kb-empty';
        }
    }
    refreshKbStatus();

    // ─── Clear Knowledge Base ────────────────────────────────
    clearKbBtn.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear the entire Knowledge Base? This cannot be undone.')) return;
        clearKbBtn.disabled = true;
        clearKbBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Clearing...';
        try {
            const res = await fetch('/api/clear-kb', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                uploadStatus.innerHTML = `<i class="fa-solid fa-check"></i> ${data.message}`;
                uploadStatus.className = 'status-msg text-success';
                refreshKbStatus();
            } else {
                uploadStatus.textContent = data.error || 'Failed to clear KB.';
                uploadStatus.className = 'status-msg text-error';
            }
        } catch {
            uploadStatus.textContent = 'Network error.';
            uploadStatus.className = 'status-msg text-error';
        } finally {
            clearKbBtn.disabled = false;
            clearKbBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i> Clear Knowledge Base';
        }
    });
    
    // ─── File Upload ─────────────────────────────────────────
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) return;

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        uploadSpin.style.display = 'inline-block';
        uploadBtnText.textContent = 'Processing...';
        uploadStatus.className = 'status-msg';
        uploadStatus.innerHTML = '<span style="color:var(--text-secondary)">Ingesting & generating summary...</span>';

        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (response.ok) {
                uploadStatus.innerHTML = `<i class="fa-solid fa-check"></i> ${data.message}`;
                uploadStatus.className = 'status-msg text-success';
                fileInput.value = '';
                uploadAreaSpan.textContent = 'Select Document';
                uploadAreaSpan.style.color = '';
                uploadAreaIcon.className = 'fa-solid fa-cloud-arrow-up cloud-icon';
                uploadAreaIcon.style.color = '';
                refreshKbStatus();

                // Show summary in chat
                if (data.summary) {
                    appendMessage('ai', `📄 **Document Summary:**\n\n${data.summary}`);
                }
            } else {
                uploadStatus.textContent = data.error || 'Upload failed.';
                uploadStatus.className = 'status-msg text-error';
            }
        } catch (err) {
            uploadStatus.textContent = 'Network error.';
            uploadStatus.className = 'status-msg text-error';
        } finally {
            uploadSpin.style.display = 'none';
            uploadBtnText.textContent = 'Ingest Data';
        }
    });

    // ─── Chat ────────────────────────────────────────────────
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        const mode = chatModeSelector.value;
        const model = modelSelector.value;
        const isCompare = compareToggle.checked;
        appendMessage('user', query);
        queryInput.value = '';

        if (isCompare) {
            // Comparison mode: run standard RAG vs Direct LLM
            const thinkingId = appendLoader('Comparing RAG vs Direct LLM...');
            chatContainer.scrollTop = chatContainer.scrollHeight;

            try {
                const response = await fetch('/api/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, model })
                });
                const data = await response.json();
                document.getElementById(thinkingId)?.remove();

                if (response.ok) {
                    appendComparisonMessage(data.rag, data.direct);
                } else {
                    appendMessage('ai', "Error: " + (data.error || "Unknown error."));
                }
            } catch {
                document.getElementById(thinkingId)?.remove();
                appendMessage('ai', "Error connecting to the server.");
            }
        } else {
            // New Flexible Mode: RAG, Long Context, or Direct
            const modeLabels = { 'rag': '📚 Standard RAG', 'long_context': '⚡ Long Context (Vector-less)', 'direct': '🧠 Direct LLM' };
            const thinkingId = appendLoader(modeLabels[mode] || 'Thinking');
            chatContainer.scrollTop = chatContainer.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, mode, model })
                });
                const data = await response.json();
                document.getElementById(thinkingId)?.remove();

                if (response.ok) {
                    appendMessage('ai', data.answer, data.chunks, data.scores, data.sources, data.response_time_ms, data.cached);
                } else {
                    appendMessage('ai', "Error: " + (data.error || "Unknown error."));
                }
            } catch {
                document.getElementById(thinkingId)?.remove();
                appendMessage('ai', "Error connecting to the server.");
            }
        }
    });

    // ─── Agentic Audit Actions ───────────────────────────────
    document.querySelectorAll('.audit-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const auditType = btn.dataset.type;
            const thinkingId = appendLoader(`Performing ${auditType} audit...`);
            
            try {
                const res = await fetch('/api/audit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: auditType })
                });
                const data = await res.json();
                document.getElementById(thinkingId)?.remove();

                if (res.ok) {
                    appendMessage('ai', `🛡️ **${auditType.toUpperCase()} AUDIT REPORT**\n\n${data.audit}`);
                } else {
                    appendMessage('ai', "Audit failed: " + data.error);
                }
            } catch {
                document.getElementById(thinkingId)?.remove();
                appendMessage('ai', "Error connecting to the server.");
            }
        });
    });
    // ─── Message Rendering ───────────────────────────────────

    function appendMessage(role, text, chunks = null, scores = null, sources = null, responseTime = null, cached = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-msg`;
        
        let icon = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
        
        let contentHtml = `<div class="msg-content">${marked.parse(text)}`;

        // Smart Action Center for AI messages
        if (role === 'ai') {
            const contentId = 'content-' + Date.now();
            contentHtml += `
                <div class="msg-actions">
                    <button class="msg-action-btn" onclick="takeAction('${contentId}', 'email')" title="Email this content"><i class="fa-solid fa-envelope"></i> Email Report</button>
                </div>
                <div id="${contentId}" style="display:none;">${text}</div>
            `;
        }
        
        // Metadata bar (sources, timing, cache)
        if (role === 'ai' && (sources?.length || responseTime)) {
            contentHtml += `<div class="msg-meta">`;
            if (sources?.length) {
                contentHtml += `<span class="meta-tag source-tag"><i class="fa-solid fa-file"></i> ${sources.join(', ')}</span>`;
            }
            if (responseTime) {
                contentHtml += `<span class="meta-tag time-tag"><i class="fa-solid fa-clock"></i> ${responseTime}ms</span>`;
            }
            if (cached) {
                contentHtml += `<span class="meta-tag cache-tag"><i class="fa-solid fa-bolt"></i> Cached</span>`;
            }
            contentHtml += `</div>`;
        }

        // Chunks with similarity scores
        if (chunks?.length > 0) {
            const chunksId = 'chunks-' + Date.now();
            contentHtml += `
                <div class="chunks-badge" onclick="document.getElementById('${chunksId}').style.display = document.getElementById('${chunksId}').style.display === 'none' ? 'block' : 'none'">
                    <i class="fa-solid fa-magnifying-glass"></i> View Retrieved Context (${chunks.length} chunks)
                </div>
                <div id="${chunksId}" class="chunks-container" style="display: none;">
                    ${chunks.map((chunk, i) => {
                        const score = scores?.[i];
                        const scoreHtml = score !== undefined ? `<div class="chunk-score"><i class="fa-solid fa-arrows-to-dot"></i> Distance: ${score}</div>` : '';
                        return `<div class="chunk-item">${scoreHtml}${marked.parse(chunk)}</div>`;
                    }).join('')}
                </div>
            `;
        }
        
        contentHtml += `</div>`;
        msgDiv.innerHTML = `<div class="msg-avatar">${icon}</div>${contentHtml}`;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendComparisonMessage(ragData, directData) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-msg comparison-msg';
        
        const chunksId = 'comp-chunks-' + Date.now();
        let chunksSection = '';
        if (ragData.chunks?.length) {
            chunksSection = `
                <div class="chunks-badge" onclick="document.getElementById('${chunksId}').style.display = document.getElementById('${chunksId}').style.display === 'none' ? 'block' : 'none'" style="margin-top:8px">
                    <i class="fa-solid fa-magnifying-glass"></i> RAG Context (${ragData.chunks.length} chunks)
                </div>
                <div id="${chunksId}" class="chunks-container" style="display: none;">
                    ${ragData.chunks.map((chunk, i) => {
                        const score = ragData.scores?.[i];
                        const sh = score !== undefined ? `<div class="chunk-score"><i class="fa-solid fa-arrows-to-dot"></i> Distance: ${score}</div>` : '';
                        return `<div class="chunk-item">${sh}${marked.parse(chunk)}</div>`;
                    }).join('')}
                </div>`;
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-scale-balanced"></i></div>
            <div class="msg-content">
                <div class="compare-grid">
                    <div class="compare-col compare-rag">
                        <div class="compare-header"><i class="fa-solid fa-database"></i> RAG Mode <span class="meta-tag time-tag">${ragData.response_time_ms}ms</span></div>
                        <div class="compare-body">${marked.parse(ragData.answer)}</div>
                        ${chunksSection}
                    </div>
                    <div class="compare-col compare-direct">
                        <div class="compare-header"><i class="fa-solid fa-brain"></i> Direct LLM <span class="meta-tag time-tag">${directData.response_time_ms}ms</span></div>
                        <div class="compare-body">${marked.parse(directData.answer)}</div>
                    </div>
                </div>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendLoader(text = 'Thinking') {
        const divId = 'loader-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-msg';
        msgDiv.id = divId;
        msgDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-content">
                <div class="thinking">${text} <span></span><span></span><span></span></div>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        return divId;
    }

    // ─── Summaries Panel ─────────────────────────────────────
    async function loadSummaries() {
        const container = document.getElementById('summariesList');
        try {
            const res = await fetch('/api/summaries');
            const data = await res.json();
            if (data.summaries?.length) {
                container.innerHTML = data.summaries.map(s => `
                    <div class="summary-card">
                        <div class="summary-header">
                            <i class="fa-solid fa-file-pdf"></i>
                            <strong>${s.filename}</strong>
                            <span class="summary-meta">${s.chunk_count} chunks · ${s.word_count} words</span>
                        </div>
                        <div class="summary-body">${marked.parse(s.summary_text)}</div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="hint text-center">No summaries yet. Upload a document first.</p>';
            }
        } catch {
            container.innerHTML = '<p class="hint text-center text-error">Failed to load summaries.</p>';
        }
    }

    // ─── Query History Panel ─────────────────────────────────
    async function loadHistory() {
        const container = document.getElementById('historyList');
        const statsContainer = document.getElementById('queryStats');
        try {
            const res = await fetch('/api/query-history');
            const data = await res.json();

            // Stats
            if (data.stats) {
                const s = data.stats;
                statsContainer.innerHTML = `
                    <div class="stats-row">
                        <div class="stat-item"><span class="stat-num">${s.total_queries}</span><span class="stat-label">Queries</span></div>
                        <div class="stat-item"><span class="stat-num">${s.avg_response_time_ms}ms</span><span class="stat-label">Avg Time</span></div>
                    </div>
                `;
            }

            // History list
            if (data.history?.length) {
                container.innerHTML = data.history.slice(0, 20).map(h => `
                    <div class="history-item">
                        <div class="history-query"><i class="fa-solid fa-user"></i> ${escapeHtml(h.query)}</div>
                        <div class="history-meta">
                            <span class="meta-tag">${h.mode === 'rag' ? '📚 RAG' : '🧠 Direct'}</span>
                            <span class="meta-tag time-tag">${h.response_time_ms || 0}ms</span>
                            ${h.num_chunks_retrieved ? `<span class="meta-tag">${h.num_chunks_retrieved} chunks</span>` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="hint text-center">No queries yet.</p>';
            }
        } catch {
            container.innerHTML = '<p class="hint text-center text-error">Failed to load history.</p>';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ─── Evaluation ──────────────────────────────────────────
    evalBtn.addEventListener('click', async () => {
        const btnText = evalBtn.innerText;
        evalBtn.innerText = 'Calculating...';
        evalBtn.disabled = true;
        try {
            const response = await fetch('/api/evaluate');
            const data = await response.json();
            if (response.ok) {
                document.getElementById('mrrValue').textContent = data.metrics.mrr.toFixed(2);
                document.getElementById('ndcgValue').textContent = data.metrics.ndcg.toFixed(2);
                evalData.style.display = 'flex';
                if (data.plot_url) {
                    document.getElementById('tsneImgContainer').innerHTML = `<img src="${data.plot_url}?t=${Date.now()}" alt="t-SNE Plot">`;
                    tsneModal.style.display = 'flex';
                } else {
                    document.getElementById('tsneImgContainer').innerHTML = '<p class="hint">Not enough data for t-SNE (need ≥ 4 chunks).</p>';
                    tsneModal.style.display = 'flex';
                }
            }
        } catch (e) {
            console.error('Evaluation error', e);
        } finally {
            evalBtn.innerText = btnText;
            evalBtn.disabled = false;
        }
    });

    // ─── Modal ───────────────────────────────────────────────
    document.querySelector('.close-btn').onclick = () => tsneModal.style.display = "none";
    window.onclick = (e) => { if (e.target == tsneModal) tsneModal.style.display = "none"; };
});

// ─── Global Agentic Actions ─────────────────────────────────────
async function takeAction(elementId, type) {
    const content = document.getElementById(elementId).innerText;
    const recipient = prompt("Enter recipient email:", "interviewer@example.com");
    if (!recipient) return;
    
    try {
        const res = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: type, content, recipient })
        });
        const data = await res.json();
        alert(data.message);
    } catch (e) {
        alert("Action failed. Check console.");
        console.error(e);
    }
}
