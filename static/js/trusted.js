/**
 * TruthLens — Trusted Board UI logic
 */

const TrustedBoard = {
    
    currentCategory: '',
    searchQuery: '',

    init() {
        this.bindEvents();
    },

    load() {
        this.fetchAnnouncements();
    },

    bindEvents() {
        // Search
        const searchInput = document.getElementById('ann-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.searchQuery = e.target.value.trim();
                    this.fetchAnnouncements();
                }, 300);
            });
        }

        // Filters
        const filters = document.getElementById('ann-filters');
        if (filters) {
            filters.addEventListener('click', (e) => {
                if (e.target.classList.contains('chip')) {
                    // Update active state
                    filters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                    e.target.classList.add('active');
                    
                    // Fetch
                    this.currentCategory = e.target.getAttribute('data-cat') || '';
                    this.fetchAnnouncements();
                }
            });
        }

        // Add Button
        const btnAdd = document.getElementById('btn-add-ann');
        if (btnAdd) {
            btnAdd.addEventListener('click', () => {
                window.App.openModal('ann-modal');
            });
        }

        // Form Submit
        const form = document.getElementById('ann-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    title: document.getElementById('ann-title').value,
                    body: document.getElementById('ann-body').value,
                    category: document.getElementById('ann-category').value,
                    source: document.getElementById('ann-source').value,
                    password: document.getElementById('ann-password').value,
                    pinned: document.getElementById('ann-pinned').checked,
                };
                
                const expires = document.getElementById('ann-expires').value;
                if (expires) payload.expires_at = expires;

                try {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Posting...';

                    await window.api.addAnnouncement(payload);
                    window.App.toast('Announcement posted successfully!', 'success');
                    window.App.closeModal('ann-modal');
                    this.fetchAnnouncements();
                } catch (err) {
                    window.App.toast(err.message, 'error');
                } finally {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Post Announcement';
                }
            });
        }
    },

    async fetchAnnouncements() {
        const list = document.getElementById('announcements-list');
        if (!list) return;
        
        list.innerHTML = '<div class="loading-spinner">Loading announcements...</div>';

        try {
            const data = await window.api.getAnnouncements(this.currentCategory, this.searchQuery);
            this.renderList(data);
        } catch (err) {
            list.innerHTML = `<div class="loading-spinner" style="color:var(--danger)">Failed to load announcements: ${err.message}</div>`;
        }
    },

    renderList(data) {
        const list = document.getElementById('announcements-list');
        list.innerHTML = '';

        if (data.length === 0) {
            list.innerHTML = `
                <div style="text-align:center; padding: 3rem; color: var(--text-secondary)">
                    <div style="font-size: 3rem; margin-bottom:1rem">📭</div>
                    <p>No verified announcements found.</p>
                </div>
            `;
            return;
        }

        data.forEach(ann => {
            // Check expiry
            let isExpired = false;
            if (ann.expires_at) {
                isExpired = new Date(ann.expires_at) < new Date();
            }

            const card = document.createElement('div');
            card.className = `glass-card announcement-card ${isExpired ? 'expired' : ''}`;
            if (isExpired) card.style.opacity = '0.6';
            card.style.marginBottom = '1rem';
            
            // Format date
            const date = new Date(ann.created_at).toLocaleDateString(undefined, {
                year: 'numeric', month: 'short', day: 'numeric'
            });

            // Tags
            let tags = `<span class="badge badge-success">✅ Verified</span>`;
            if (ann.pinned && !isExpired) tags += ` <span class="badge badge-info">📌 Pinned</span>`;
            if (isExpired) tags += ` <span class="badge badge-warning">⏳ Expired</span>`;

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem">
                    <h3 style="margin:0; font-size:1.3rem">${ann.title}</h3>
                    <div style="display:flex; gap:0.5rem">${tags}</div>
                </div>
                <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:1rem">
                    <span>📅 ${date}</span> • 
                    <span>👤 ${ann.source}</span> • 
                    <span style="text-transform:capitalize">🏷️ ${ann.category}</span>
                </div>
                <div style="white-space: pre-wrap; font-size:1rem; line-height:1.6">${ann.body}</div>
            `;
            list.appendChild(card);
        });
    }
};

window.TrustedBoard = TrustedBoard;

document.addEventListener('DOMContentLoaded', () => {
    TrustedBoard.init();
});
