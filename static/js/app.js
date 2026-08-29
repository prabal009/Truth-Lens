/**
 * TruthLens — Global App Controller
 * Handles navigation, toasts, and initialization
 */

const App = {
    init() {
        this.setupNavigation();
        this.setupModals();
        this.checkModelStatus();
        
        // Load initial section based on hash or default to analyzer
        const hash = window.location.hash.replace('#', '');
        if (hash && document.getElementById(`nav-${hash}`)) {
            this.switchSection(hash);
        } else {
            this.switchSection('analyzer');
        }
    },

    // ── Navigation ────────────────────────────────────────────────
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionId = item.getAttribute('data-section');
                this.switchSection(sectionId);
                
                // On mobile, close sidebar after click
                if(window.innerWidth <= 768 && document.querySelector('.sidebar').style.transform === 'translateX(0px)') {
                    document.querySelector('.sidebar').style.transform = 'translateX(-100%)';
                }
            });
        });

        // Mobile menu toggle
        const menuBtn = document.getElementById('menu-toggle');
        if (menuBtn) {
            menuBtn.addEventListener('click', () => {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar.style.transform === 'translateX(0px)') {
                    sidebar.style.transform = 'translateX(-100%)';
                } else {
                    sidebar.style.transform = 'translateX(0px)';
                }
            });
        }
    },

    switchSection(sectionId) {
        // Update nav UI
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        const navItem = document.getElementById(`nav-${sectionId}`);
        if(navItem) navItem.classList.add('active');

        // Update Title
        const titleEl = document.getElementById('topbar-title');
        if (titleEl && navItem) {
            titleEl.innerHTML = navItem.innerHTML;
        }

        // Hide all, show target
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        const section = document.getElementById(`section-${sectionId}`);
        if (section) section.classList.add('active');

        // Update URL hash without jumping
        history.pushState(null, null, `#${sectionId}`);

        // Trigger section specific initializers
        this.triggerSectionInit(sectionId);
    },

    triggerSectionInit(sectionId) {
        switch(sectionId) {
            case 'trusted':
                if(window.TrustedBoard) window.TrustedBoard.load();
                break;
            case 'community':
                if(window.Community) window.Community.load();
                break;
            case 'dashboard':
                if(window.Dashboard) window.Dashboard.load();
                break;
        }
    },

    // ── Modals ────────────────────────────────────────────────────
    setupModals() {
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            // Click outside to close
            overlay.addEventListener('click', (e) => {
                if(e.target === overlay) this.closeModal(overlay.id);
            });
            
            // Close buttons
            const closeBtn = overlay.querySelector('.modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeModal(overlay.id));
            }
            
            // Cancel buttons
            const cancelBtn = overlay.querySelector('.btn-ghost');
            if (cancelBtn && cancelBtn.id.includes('cancel')) {
                cancelBtn.addEventListener('click', () => this.closeModal(overlay.id));
            }
        });
    },

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if(modal) modal.classList.remove('hidden');
    },

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if(modal) {
            modal.classList.add('hidden');
            const form = modal.querySelector('form');
            if(form) form.reset();
        }
    },

    // ── Toasts ────────────────────────────────────────────────────
    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '❌';

        toast.innerHTML = `
            <span style="margin-right: 10px">${icon}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Remove after 4s
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    // ── System Status ─────────────────────────────────────────────
    async checkModelStatus() {
        const badge = document.getElementById('model-badge');
        if(!badge) return;
        
        try {
            const info = await window.api.getModelInfo();
            if(info.status === 'ready') {
                badge.className = 'model-badge ready';
                badge.textContent = `✅ ML Active (${info.accuracy}% acc)`;
            } else {
                badge.className = 'model-badge error';
                badge.textContent = `⚠️ Heuristics Only`;
            }
        } catch(err) {
            badge.className = 'model-badge error';
            badge.textContent = `❌ API Offline`;
        }
    }
};

window.App = App;

// Boot
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
