/**
 * TruthLens — Analyzer UI logic
 * Handles message input, gauge animation, and evidence rendering
 */

const Analyzer = {
    
    // DOM Elements
    elements: {
        input: document.getElementById('analyzer-input'),
        charCount: document.getElementById('char-count'),
        btnAnalyze: document.getElementById('btn-analyze'),
        btnClear: document.getElementById('btn-clear'),
        gaugeCard: document.getElementById('gauge-card'),
        placeholder: document.getElementById('gauge-placeholder'),
        resultWrap: document.getElementById('gauge-result'),
        gaugeArc: document.getElementById('gauge-arc'),
        scoreText: document.getElementById('gauge-score-text'),
        verdictBadge: document.getElementById('verdict-badge'),
        evidenceSection: document.getElementById('evidence-section'),
        evidenceGrid: document.getElementById('evidence-grid'),
        dupAlert: document.getElementById('duplicate-alert'),
        dupContent: document.getElementById('duplicate-content'),
        chips: document.querySelectorAll('.sample-chips .chip')
    },

    init() {
        this.bindEvents();
    },

    bindEvents() {
        // Input character count
        this.elements.input.addEventListener('input', () => {
            const len = this.elements.input.value.length;
            this.elements.charCount.textContent = `${len} / 5000`;
            this.elements.btnAnalyze.disabled = len < 10;
        });

        // Buttons
        this.elements.btnAnalyze.addEventListener('click', () => this.analyze());
        
        this.elements.btnClear.addEventListener('click', () => {
            this.elements.input.value = '';
            this.elements.input.dispatchEvent(new Event('input'));
            this.resetUI();
        });

        // Sample chips
        this.elements.chips.forEach(chip => {
            chip.addEventListener('click', () => {
                const sampleKey = chip.getAttribute('data-sample');
                if (window.SAMPLES && window.SAMPLES[sampleKey]) {
                    this.elements.input.value = window.SAMPLES[sampleKey];
                    this.elements.input.dispatchEvent(new Event('input'));
                    // Flash effect
                    this.elements.input.style.backgroundColor = 'rgba(102,126,234,0.1)';
                    setTimeout(() => {
                        this.elements.input.style.backgroundColor = 'rgba(0,0,0,0.2)';
                    }, 300);
                }
            });
        });
    },

    resetUI() {
        this.elements.placeholder.classList.remove('hidden');
        this.elements.resultWrap.classList.add('hidden');
        this.elements.evidenceSection.classList.add('hidden');
        this.elements.dupAlert.classList.add('hidden');
        
        // Reset gauge
        this.elements.gaugeArc.style.strokeDashoffset = 283;
        this.elements.scoreText.textContent = '0';
        
        // Reset bars
        document.getElementById('ml-bar').style.width = '0%';
        document.getElementById('heuristic-bar').style.width = '0%';
    },

    async analyze() {
        const text = this.elements.input.value.trim();
        if (text.length < 10) return;

        try {
            // UI Loading state
            this.elements.btnAnalyze.disabled = true;
            this.elements.btnAnalyze.innerHTML = '<span class="spinner">⏳</span> Analyzing...';
            this.resetUI();

            // API Call
            const result = await window.api.analyze(text);
            
            // Render results
            this.renderGauge(result);
            this.renderEvidence(result.evidence);
            this.renderDuplicate(result.similar_matches);

        } catch (err) {
            window.App.toast(err.message || 'Analysis failed', 'error');
        } finally {
            this.elements.btnAnalyze.disabled = false;
            this.elements.btnAnalyze.innerHTML = '<span class="btn-icon">🔍</span> Analyze';
        }
    },

    renderGauge(result) {
        this.elements.placeholder.classList.add('hidden');
        this.elements.resultWrap.classList.remove('hidden');

        // Animate Score Counter (0 to target)
        const targetScore = result.combined_score;
        this.animateCounter(this.elements.scoreText, targetScore, 1500);

        // Animate SVG Arc
        // Dash array is ~283. Offset 283 = 0%, 0 = 100%
        // Because arc is 180 deg (half circle), 100% fill = half dash array?
        // Wait, the path is an arc M 20 120 A 90 90 0 0 1 200 120
        // Length = pi * r = 3.14 * 90 ≈ 282.7
        // To fill X%, offset = 283 - (283 * X / 100)
        setTimeout(() => {
            const offset = 283 - (283 * (targetScore / 100));
            this.elements.gaugeArc.style.strokeDashoffset = offset;
        }, 50);

        // Verdict Badge
        const badge = this.elements.verdictBadge;
        badge.textContent = result.verdict_label.split(' ').slice(1).join(' '); // Remove emoji
        
        // Clear classes
        badge.className = 'verdict-badge';
        
        // Add color class
        if (targetScore >= 81) badge.classList.add('verdict-safe');
        else if (targetScore >= 61) badge.classList.add('verdict-okay');
        else if (targetScore >= 41) badge.classList.add('verdict-sus');
        else badge.classList.add('verdict-fake');

        // Mini Bars
        if (result.ml_score !== null) {
            document.getElementById('ml-val').textContent = result.ml_score;
            setTimeout(() => document.getElementById('ml-bar').style.width = `${result.ml_score}%`, 500);
        } else {
            document.getElementById('ml-val').textContent = 'N/A';
        }
        
        document.getElementById('heuristic-val').textContent = result.heuristic_score;
        setTimeout(() => document.getElementById('heuristic-bar').style.width = `${result.heuristic_score}%`, 500);
    },

    renderEvidence(evidenceList) {
        if (!evidenceList || evidenceList.length === 0) return;
        
        this.elements.evidenceSection.classList.remove('hidden');
        this.elements.evidenceGrid.innerHTML = '';

        evidenceList.forEach((ev, index) => {
            let icon = '🔹';
            if (ev.severity === 'high') icon = '⚠️';
            else if (ev.severity === 'medium') icon = '🔸';

            let impactHtml = '';
            if (ev.score_impact < 0) {
                impactHtml = `<span class="ev-impact negative">${ev.score_impact}</span>`;
            } else if (ev.score_impact > 0) {
                impactHtml = `<span class="ev-impact positive">+${ev.score_impact}</span>`;
            }

            const card = document.createElement('div');
            card.className = 'evidence-card';
            card.style.animationDelay = `${index * 80}ms`; // staggered animation
            
            card.innerHTML = `
                <div class="ev-icon">${icon}</div>
                <div class="ev-content">
                    <div class="ev-layer">
                        <span>${ev.layer}</span>
                        ${impactHtml}
                    </div>
                    <div class="ev-msg">${ev.message}</div>
                </div>
            `;
            this.elements.evidenceGrid.appendChild(card);
        });
    },

    renderDuplicate(matches) {
        if (!matches || matches.length === 0) return;
        
        // Find highest match
        const topMatch = matches[0];
        // Only show if >= 60%
        if (topMatch.similarity < 60) return;

        this.elements.dupAlert.classList.remove('hidden');
        
        let typeLabel = topMatch.match_type === 'duplicate' ? 'Near Duplicate' : 'Similar';
        
        this.elements.dupContent.innerHTML = `
            <div class="dup-meta">
                <span>Match Type: <strong>${typeLabel}</strong></span>
                <span class="dup-sim">${topMatch.similarity}% Match</span>
            </div>
            <div class="dup-text">"${topMatch.original_text}"</div>
            <div style="margin-top: 0.8rem; font-size: 0.85rem">
                Original verdict: <strong>${topMatch.original_verdict.replace(/_/g, ' ').toUpperCase()}</strong> 
                (Score: ${topMatch.original_score})
            </div>
        `;
    },

    animateCounter(element, target, duration) {
        let start = null;
        const step = (timestamp) => {
            if (!start) start = timestamp;
            const progress = Math.min((timestamp - start) / duration, 1);
            
            // easeOutQuart
            const ease = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(ease * target);
            
            element.textContent = current;
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                element.textContent = target; // Ensure exact final value
            }
        };
        window.requestAnimationFrame(step);
    }
};

// Auto-init
document.addEventListener('DOMContentLoaded', () => {
    Analyzer.init();
});
