/**
 * TruthLens — Analytics Dashboard UI logic
 */

const Dashboard = {
    
    init() {
        // Will load when switched to
    },

    async load() {
        try {
            const data = await window.api.getStats();
            this.renderCounters(data);
            this.renderDonut(data.distribution);
            this.renderRecent(data.recent);
            this.renderModelInfo(data.model_info);
        } catch (err) {
            console.error('Failed to load stats', err);
            window.App.toast('Failed to load dashboard data', 'error');
        }
    },

    renderCounters(data) {
        window.Analyzer.animateCounter(document.getElementById('cnt-total'), data.total_analyzed, 1000);
        window.Analyzer.animateCounter(document.getElementById('cnt-fake'), data.fake_count, 1200);
        window.Analyzer.animateCounter(document.getElementById('cnt-real'), data.real_count, 1200);
        window.Analyzer.animateCounter(document.getElementById('cnt-reports'), data.reports_count, 1200);
    },

    renderDonut(dist) {
        const svg = document.getElementById('donut-svg');
        const legend = document.getElementById('donut-legend');
        if (!svg || !legend) return;

        svg.innerHTML = '';
        legend.innerHTML = '';

        const items = [
            { key: 'highly_credible', color: '#00d97e', label: 'Highly Credible' },
            { key: 'likely_safe', color: '#b8e986', label: 'Likely Safe' },
            { key: 'suspicious', color: '#f4a261', label: 'Suspicious' },
            { key: 'likely_fake', color: '#e63946', label: 'Likely Fake' },
            { key: 'almost_certainly_fake', color: '#b80f1e', label: 'Almost Certainly Fake' }
        ];

        // Total
        const total = Object.values(dist).reduce((a, b) => a + b, 0);
        if (total === 0) {
            svg.innerHTML = '<circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="30" />';
            return;
        }

        let currentAngle = 0;
        const radius = 80;
        const circumference = 2 * Math.PI * radius; // ~502

        items.forEach((item, index) => {
            const val = dist[item.key] || 0;
            if (val === 0) return;

            const percentage = val / total;
            const dashLength = percentage * circumference;
            const gapLength = circumference - dashLength;

            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", "100");
            circle.setAttribute("cy", "100");
            circle.setAttribute("r", radius.toString());
            circle.setAttribute("fill", "none");
            circle.setAttribute("stroke", item.color);
            circle.setAttribute("class", "donut-segment");
            
            // Set dasharray: length of segment, gap to fill rest of circle
            // Initially 0 length for animation
            circle.style.strokeDasharray = `0 ${circumference}`;
            
            // Offset to start at current angle
            circle.style.strokeDashoffset = -currentAngle;
            
            svg.appendChild(circle);

            // Animate
            setTimeout(() => {
                // Slight gap between segments by subtracting 2 from dashLength
                circle.style.strokeDasharray = `${Math.max(0, dashLength - 2)} ${circumference}`;
            }, 100);

            currentAngle += dashLength;

            // Legend
            legend.innerHTML += `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${item.color}"></div>
                    <span>${item.label}</span>
                    <span class="legend-val">${val}</span>
                </div>
            `;
        });
    },

    renderRecent(recent) {
        const list = document.getElementById('recent-list');
        if (!list) return;
        
        list.innerHTML = '';
        
        if (!recent || recent.length === 0) {
            list.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:1rem">No recent activity</div>';
            return;
        }

        recent.forEach(r => {
            let typeClass = 'type-sus';
            if (r.combined_score >= 61) typeClass = 'type-safe';
            else if (r.combined_score <= 40) typeClass = 'type-fake';

            // time ago
            const timeAgo = this.timeSince(new Date(r.created_at));

            list.innerHTML += `
                <div class="recent-item ${typeClass}">
                    <div class="ri-score">${r.combined_score}</div>
                    <div class="ri-content">
                        <div class="ri-meta">
                            <span>${r.verdict.replace(/_/g, ' ').toUpperCase()}</span>
                            <span>${timeAgo}</span>
                        </div>
                    </div>
                </div>
            `;
        });
    },

    renderModelInfo(info) {
        if (!info || info.status === 'not_trained') {
            document.getElementById('val-accuracy').textContent = 'N/A';
            document.getElementById('val-f1').textContent = 'N/A';
            document.getElementById('model-info-grid').innerHTML = `
                <div style="grid-column: 1 / -1; color: var(--warning); text-align: center; padding: 1rem;">
                    ⚠️ Model not trained. Run generate_dataset.py and train_model.py
                </div>
            `;
            return;
        }

        // Animate bars
        document.getElementById('val-accuracy').textContent = `${info.accuracy}%`;
        document.getElementById('val-f1').textContent = `${info.f1_score}%`;
        setTimeout(() => {
            document.getElementById('bar-accuracy').style.width = `${info.accuracy}%`;
            document.getElementById('bar-f1').style.width = `${info.f1_score}%`;
        }, 100);

        // Grid details
        const grid = document.getElementById('model-info-grid');
        grid.innerHTML = `
            <div class="mi-item">
                <span class="mi-label">Training Size</span>
                <span class="mi-val">${(info.total_samples || 0).toLocaleString()}</span>
            </div>
            <div class="mi-item">
                <span class="mi-label">Features</span>
                <span class="mi-val">${(info.features || 0).toLocaleString()}</span>
            </div>
            <div class="mi-item">
                <span class="mi-label">Ensemble</span>
                <span class="mi-val">PA + LR + RF</span>
            </div>
            <div class="mi-item">
                <span class="mi-label">Voting</span>
                <span class="mi-val" style="text-transform: capitalize">${info.voting || 'Soft'}</span>
            </div>
        `;
    },

    timeSince(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + "y ago";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + "mo ago";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + "d ago";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + "h ago";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + "m ago";
        return "Just now";
    }
};

window.Dashboard = Dashboard;

document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
});
