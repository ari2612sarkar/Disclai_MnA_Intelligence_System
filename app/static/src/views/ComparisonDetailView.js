import { api } from '@/api';
import { formatCurrency, getSeverityClass, truncate } from '@/utils/helpers';
export class ComparisonDetailView {
    constructor(container, app, comparisonId) {
        this.comparison = null;
        this.activeTab = 'findings';
        this.container = container;
        this.app = app;
        this.comparisonId = comparisonId;
    }
    async mount() {
        this.renderLoading();
        await this.loadData();
        this.render();
        this.bindEvents();
    }
    renderLoading() {
        this.container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
    }
    async loadData() {
        this.comparison = await api.comparison.get(this.comparisonId);
    }
    render() {
        if (!this.comparison)
            return;
        const { verdict, findings, matches, cross_document_risks, disclosure_issues } = this.comparison;
        const hasVerdict = !!verdict;
        this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1>Comparison Detail</h1>
          <p style="color: var(--color-text-secondary);">${this.comparison.transaction_name || 'Transaction'}</p>
        </div>
      </div>

      ${hasVerdict ? this.renderVerdictHeader(verdict) : ''}

      <div class="tabs" id="comparison-tabs">
        <button class="tab ${this.activeTab === 'findings' ? 'active' : ''}" data-tab="findings">Findings (${findings.length})</button>
        <button class="tab ${this.activeTab === 'matches' ? 'active' : ''}" data-tab="matches">Matches (${matches.length})</button>
        <button class="tab ${this.activeTab === 'risks' ? 'active' : ''}" data-tab="risks">Cross-Doc Risks (${cross_document_risks.length})</button>
        <button class="tab ${this.activeTab === 'disclosure' ? 'active' : ''}" data-tab="disclosure">Disclosure Issues (${disclosure_issues.length})</button>
        ${hasVerdict ? `<button class="tab ${this.activeTab === 'verdict' ? 'active' : ''}" data-tab="verdict">Deal Verdict</button>` : ''}
      </div>

      <div id="tab-content">
        ${this.renderTabContent()}
      </div>
    `;
    }
    renderVerdictHeader(verdict) {
        return `
      <div class="grid grid-4" style="margin-bottom: 16px;">
        <div class="card stat-card">
          <div class="stat-label">Overall Risk</div>
          <div class="stat-value stat-${verdict.overall_risk_level.toLowerCase()}">${verdict.overall_risk_level}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Deal Score</div>
          <div class="stat-value ${verdict.score < 30 ? 'stat-critical' : verdict.score < 50 ? 'stat-high' : verdict.score < 70 ? 'stat-medium' : 'stat-low'}">${verdict.score.toFixed(1)}/100</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Material Asymmetries</div>
          <div class="stat-value ${verdict.material_asymmetries > 0 ? 'stat-high' : 'stat-low'}">${verdict.material_asymmetries}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Confidence</div>
          <div class="stat-value stat-info">${Math.round(verdict.confidence * 100)}%</div>
        </div>
      </div>
    `;
    }
    renderTabContent() {
        switch (this.activeTab) {
            case 'findings': return this.renderFindingsTab();
            case 'matches': return this.renderMatchesTab();
            case 'risks': return this.renderRisksTab();
            case 'disclosure': return this.renderDisclosureTab();
            case 'verdict': return this.renderVerdictTab();
            default: return '';
        }
    }
    renderFindingsTab() {
        const { findings } = this.comparison;
        if (findings.length === 0) {
            return `<div class="empty-state" style="padding: 48px 24px;"><div class="empty-icon">✓</div><p>No findings</p></div>`;
        }
        return `
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Provision</th>
              <th>Category</th>
              <th>Classification</th>
              <th>Company A</th>
              <th>Company B</th>
              <th>Legal Impact</th>
            </tr>
          </thead>
          <tbody>
            ${findings.map((f, i) => `
              <tr>
                <td>${i + 1}</td>
                <td><strong>${f.provision}</strong></td>
                <td>${f.category}</td>
                <td><span class="badge ${getSeverityClass(f.classification)}">${f.classification.replace(/_/g, ' ')}</span></td>
                <td>${this.formatPosition(f.company_a_position)}</td>
                <td>${this.formatPosition(f.company_b_position)}</td>
                <td style="max-width: 300px;">${truncate(f.legal_impact, 150)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    }
    renderMatchesTab() {
        const { matches } = this.comparison;
        if (matches.length === 0) {
            return `<div class="empty-state" style="padding: 48px 24px;"><p>No matches</p></div>`;
        }
        return `
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Company A Provision</th>
              <th>Company B Provision</th>
              <th>Match Status</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            ${matches.map((m) => `
              <tr>
                <td>${m.company_a_provision || '—'}</td>
                <td>${m.company_b_provision || '—'}</td>
                <td><span class="badge ${getSeverityClass(m.match_status)}">${m.match_status}</span></td>
                <td>${(m.match_confidence * 100).toFixed(0)}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    }
    renderRisksTab() {
        const { cross_document_risks } = this.comparison;
        if (cross_document_risks.length === 0) {
            return `<div class="empty-state" style="padding: 48px 24px;"><p>No cross-document risks identified</p></div>`;
        }
        return cross_document_risks.map((r) => `
      <div class="card" style="margin-bottom: 16px;">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <strong>${r.risk_type}</strong>
              <span class="badge ${getSeverityClass(r.severity)}" style="margin-left: 8px;">${r.severity}</span>
            </div>
            <span class="text-muted text-sm">${r.confidence ? Math.round(r.confidence * 100) + '% confidence' : ''}</span>
          </div>
          <p style="color: var(--color-text-secondary); margin-bottom: 12px;">${r.description}</p>
          <p style="font-size: 13px; color: var(--color-text-muted);"><strong>Impact:</strong> ${r.impact}</p>
        </div>
      </div>
    `).join('');
    }
    renderDisclosureTab() {
        const { disclosure_issues } = this.comparison;
        if (disclosure_issues.length === 0) {
            return `<div class="empty-state" style="padding: 48px 24px;"><div class="empty-icon">📋</div><p>No disclosure issues identified</p></div>`;
        }
        return disclosure_issues.map((i) => `
      <div class="card" style="margin-bottom: 16px; border-left: 4px solid ${i.severity === 'critical' ? 'var(--color-critical)' : i.severity === 'high' ? 'var(--color-high)' : 'var(--color-medium)'};">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <strong>${i.issue_type}</strong>
              <span class="badge ${getSeverityClass(i.severity)}" style="margin-left: 8px;">${i.severity}</span>
            </div>
            <span class="text-muted text-sm">${i.confidence ? Math.round(i.confidence * 100) + '% confidence' : ''}</span>
          </div>
          <p style="color: var(--color-text-secondary); margin-bottom: 12px;">${i.description}</p>
          ${i.spa_requirement ? `<p style="font-size: 13px; margin-bottom: 8px;"><strong>SPA Requirement:</strong> ${i.spa_requirement}</p>` : ''}
          ${i.disclosure_schedule ? `<p style="font-size: 13px; margin-bottom: 8px;"><strong>Disclosure Schedule:</strong> ${i.disclosure_schedule}</p>` : ''}
          ${i.data_room_evidence ? `<p style="font-size: 13px;"><strong>Data Room Evidence:</strong> ${i.data_room_evidence}</p>` : ''}
        </div>
      </div>
    `).join('');
    }
    renderVerdictTab() {
        const { verdict } = this.comparison;
        if (!verdict)
            return '';
        return `
      <div style="display: flex; flex-direction: column; gap: 24px;">
        <div class="card">
          <div class="card-header"><div class="card-title">Executive Assessment</div></div>
          <div class="card-body">
            <p style="margin-bottom: 16px; font-size: 15px; line-height: 1.6;">${verdict.overall_assessment}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 16px;">
              <div><strong>Evidence-Backed Findings:</strong> ${verdict.evidence_backed_findings}</div>
              <div><strong>Key Asymmetries:</strong> ${verdict.key_asymmetries}</div>
              <div><strong>Critical Issues:</strong> ${verdict.critical_issues}</div>
              <div><strong>Confidence:</strong> ${Math.round(verdict.confidence * 100)}%</div>
            </div>
          </div>
        </div>

        <div class="grid grid-2">
          <div class="card">
            <div class="card-header"><div class="card-title">Company A Advantages</div></div>
            <div class="card-body">
              ${verdict.company_a_advantages.length > 0 ? `
                <ul style="margin-left: 16px;">${verdict.company_a_advantages.map((a) => `<li style="margin-bottom: 8px;">${a}</li>`).join('')}</ul>
              ` : '<p class="text-muted">No advantages identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company A Weaknesses</div></div>
            <div class="card-body">
              ${verdict.company_a_weaknesses.length > 0 ? `
                <ul style="margin-left: 16px;">${verdict.company_a_weaknesses.map((w) => `<li style="margin-bottom: 8px; color: var(--color-critical);">${w}</li>`).join('')}</ul>
              ` : '<p class="text-muted">No weaknesses identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company B Advantages</div></div>
            <div class="card-body">
              ${verdict.company_b_advantages.length > 0 ? `
                <ul style="margin-left: 16px;">${verdict.company_b_advantages.map((a) => `<li style="margin-bottom: 8px;">${a}</li>`).join('')}</ul>
              ` : '<p class="text-muted">No advantages identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company B Weaknesses</div></div>
            <div class="card-body">
              ${verdict.company_b_weaknesses.length > 0 ? `
                <ul style="margin-left: 16px;">${verdict.company_b_weaknesses.map((w) => `<li style="margin-bottom: 8px; color: var(--color-critical);">${w}</li>`).join('')}</ul>
              ` : '<p class="text-muted">No weaknesses identified</p>'}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Recommended Actions</div></div>
          <div class="card-body">
            ${verdict.recommended_actions.length > 0 ? `
              <ol style="margin-left: 16px;">${verdict.recommended_actions.map((a) => `<li style="margin-bottom: 8px;">${a}</li>`).join('')}</ol>
            ` : '<p class="text-muted">No specific actions recommended</p>'}
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Methodology</div></div>
          <div class="card-body">
            <p style="color: var(--color-text-secondary);">${verdict.score_methodology || 'Transparent scoring based on weighted asymmetry categories, cross-document dependencies, and disclosure completeness.'}</p>
          </div>
        </div>

        <div class="card" style="border-left: 4px solid var(--color-medium); background: var(--color-medium-light);">
          <div class="card-body">
            <strong style="color: var(--color-medium);">⚠ Legal Disclaimer</strong>
            <p style="margin-top: 8px; color: var(--color-text-secondary); font-size: 13px;">
              This analysis is legal decision support, not legal advice. Qualified counsel should review all findings before transaction decisions. DISCLAI identifies issues and traces them to evidence; it does not guarantee outcomes or replace legal judgment.
            </p>
          </div>
        </div>
    `;
    }
    formatPosition(pos) {
        if (!pos)
            return '—';
        if (pos.percentage !== undefined)
            return `${pos.percentage}%`;
        if (pos.amount !== undefined)
            return formatCurrency(pos.amount);
        if (pos.duration)
            return pos.duration;
        return '—';
    }
    bindEvents() {
        this.container.querySelectorAll('.tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.getAttribute('data-tab');
                if (tab) {
                    this.activeTab = tab;
                    this.render();
                    this.bindEvents();
                }
            });
        });
    }
}
