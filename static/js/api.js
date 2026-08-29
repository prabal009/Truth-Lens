/**
 * TruthLens — API Client Wrapper
 * Handles all fetch requests to the Flask backend
 */

const API_BASE = '/api';

const api = {
    
    // Status indicator DOM element
    dot: document.getElementById('status-dot'),

    setStatus(isOk) {
        if(this.dot) {
            this.dot.style.backgroundColor = isOk ? 'var(--success)' : 'var(--danger)';
            this.dot.style.boxShadow = isOk ? '0 0 10px var(--success)' : '0 0 10px var(--danger)';
        }
    },

    async fetch(endpoint, options = {}) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.headers || {})
                }
            });
            this.setStatus(res.ok);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'API Error');
            return data;
        } catch (err) {
            this.setStatus(false);
            console.error(`[API Error] ${endpoint}:`, err);
            throw err;
        }
    },

    // ── Endpoints ───────────────────────────────────────────

    async analyze(text) {
        return this.fetch('/predict', {
            method: 'POST',
            body: JSON.stringify({ text })
        });
    },

    async getHistory() {
        return this.fetch('/history');
    },

    async getAnnouncements(category = '', q = '') {
        const params = new URLSearchParams();
        if (category) params.append('category', category);
        if (q) params.append('q', q);
        return this.fetch(`/announcements?${params.toString()}`);
    },

    async addAnnouncement(payload) {
        return this.fetch('/announcements', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async getReports(sort = 'latest') {
        return this.fetch(`/community?sort=${sort}`);
    },

    async submitReport(text, context) {
        return this.fetch('/community/report', {
            method: 'POST',
            body: JSON.stringify({ text, context })
        });
    },

    async voteReport(reportId, voteType) {
        return this.fetch('/community/vote', {
            method: 'POST',
            body: JSON.stringify({ report_id: reportId, vote: voteType })
        });
    },

    async getStats() {
        return this.fetch('/stats');
    },
    
    async getModelInfo() {
        return this.fetch('/model_info');
    }
};

window.api = api;
