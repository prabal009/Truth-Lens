/**
 * TruthLens — Community Reports UI logic
 */

const Community = {
    
    currentSort: 'latest',

    init() {
        this.bindEvents();
    },

    load() {
        this.fetchReports();
    },

    bindEvents() {
        // Filters
        const filters = document.getElementById('community-filters');
        if (filters) {
            filters.addEventListener('click', (e) => {
                if (e.target.classList.contains('chip')) {
                    filters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                    e.target.classList.add('active');
                    this.currentSort = e.target.getAttribute('data-sort') || 'latest';
                    this.fetchReports();
                }
            });
        }

        // Report Button
        const btnSubmit = document.getElementById('btn-submit-report');
        if (btnSubmit) {
            btnSubmit.addEventListener('click', () => {
                window.App.openModal('report-modal');
            });
        }

        // Form Submit
        const form = document.getElementById('report-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const text = document.getElementById('report-text').value;
                const ctx = document.getElementById('report-context').value;
                
                try {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Submitting...';

                    await window.api.submitReport(text, ctx);
                    window.App.toast('Report submitted successfully!', 'success');
                    window.App.closeModal('report-modal');
                    this.fetchReports();
                } catch (err) {
                    window.App.toast(err.message, 'error');
                } finally {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Submit Report';
                }
            });
        }
    },

    async fetchReports() {
        const list = document.getElementById('reports-list');
        if (!list) return;
        
        list.innerHTML = '<div class="loading-spinner">Loading reports...</div>';

        try {
            const data = await window.api.getReports(this.currentSort);
            this.renderList(data);
        } catch (err) {
            list.innerHTML = `<div class="loading-spinner" style="color:var(--danger)">Failed to load reports: ${err.message}</div>`;
        }
    },

    renderList(data) {
        const list = document.getElementById('reports-list');
        list.innerHTML = '';

        if (data.length === 0) {
            list.innerHTML = `
                <div style="text-align:center; padding: 3rem; color: var(--text-secondary)">
                    <div style="font-size: 3rem; margin-bottom:1rem">✨</div>
                    <p>No community reports found.</p>
                </div>
            `;
            return;
        }

        data.forEach(rep => {
            const card = document.createElement('div');
            card.className = `glass-card report-card`;
            card.style.marginBottom = '1rem';
            
            // Format status label
            let statusLabel = '';
            if (rep.status === 'under_review') statusLabel = '<span class="badge badge-info">Under Review</span>';
            else if (rep.status === 'community_flagged') statusLabel = '<span class="badge badge-danger">Community Flagged</span>';
            else if (rep.status === 'verified') statusLabel = '<span class="badge badge-success">Verified Legit</span>';

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; margin-bottom:1rem">
                    ${statusLabel}
                    <span style="font-size:0.85rem; color:var(--text-secondary)">Auto Score: <strong>${rep.auto_score}/100</strong></span>
                </div>
                <div style="font-style:italic; border-left:3px solid var(--border-glass); padding-left:1rem; margin-bottom:1rem; color:var(--text-primary)">
                    "${rep.text}"
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-glass); padding-top:1rem">
                    <div style="display:flex; gap:0.5rem">
                        <button class="btn btn-sm btn-ghost vote-btn" data-id="${rep.id}" data-vote="fake">
                            🔴 Fake (${rep.votes_fake})
                        </button>
                        <button class="btn btn-sm btn-ghost vote-btn" data-id="${rep.id}" data-vote="legit">
                            ✅ Legit (${rep.votes_legit})
                        </button>
                    </div>
                    <span style="font-size:0.8rem; color:var(--text-secondary)">
                        ${rep.context ? '📍 ' + rep.context : ''}
                    </span>
                </div>
            `;
            list.appendChild(card);
        });

        // Bind vote buttons
        list.querySelectorAll('.vote-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const vote = e.currentTarget.getAttribute('data-vote');
                try {
                    e.currentTarget.disabled = true;
                    await window.api.voteReport(id, vote);
                    window.App.toast('Vote recorded!', 'success');
                    this.fetchReports(); // Refresh
                } catch (err) {
                    window.App.toast(err.message, 'error');
                    e.currentTarget.disabled = false;
                }
            });
        });
    }
};

window.Community = Community;

document.addEventListener('DOMContentLoaded', () => {
    Community.init();
});
