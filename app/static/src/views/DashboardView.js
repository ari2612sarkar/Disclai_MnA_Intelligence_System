import { api } from '@/api';
import { formatCurrency, getSeverityClass, truncate } from '@/utils/helpers';
export class DashboardView {
    constructor(container, app) {
        this.container = container;
        this.app = app;
    }
    async mount() {
        this.renderLoading();
        await this.loadData();
        this.render();
    }
    renderLoading() {
        this.container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
    }
    async loadData() {
        try {
            const [txns, comps] = await Promise.all([
                api.transactions.list().catch(() => []),
                api.comparisons.list().catch(() => []),
            ]);
            this.app.transactions = txns;
            this.app.comparisons = comps;
        }
        catch (e) {
            console.warn('Failed to load dashboard data:', e);
        }
    }
    render() {
        const latestTxn = this.app.transactions[0];
        const latestComp = this.app.comparisons[0];
        this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px;">
        <h1>Dashboard</h1>
        <p style="color: var(--color-text-secondary);">Overview of deal risk, asymmetries, and key findings</p>
      </div>

      ${!latestTxn ? this.renderEmptyState() : this.renderDashboard(latestTxn, latestComp)}
    `;
    }
    renderEmptyState() {
        return `
      <div class="card" style="max-width: 600px; margin: 0 auto;">
        <div class="card-body">
          <div class="empty-state">
            <div class="empty-icon">📋</div>
            <h3 class="empty-title">No Active Transaction</h3>
            <p class="empty-desc">Create a transaction to begin analysis</p>
            <button class="btn btn-primary" style="margin-top: 16px;" id="create-first-txn">
              Create Transaction
            </button>
          </div>
        </div>
      </div>
    `;
    }
    renderDashboard(txn, comp) {
        const verdict = comp?.verdict;
        const hasVerdict = !!verdict;
        return `
      <div class="grid grid-4" style="margin-bottom: 24px;">
        <div class="card stat-card">
          <div class="stat-label">Overall Risk</div>
          <div class="stat-value ${hasVerdict ? `stat-${verdict.overall_risk_level.toLowerCase()}` : 'stat-info'}">
            ${hasVerdict ? verdict.overall_risk_level : '—'}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Deal Score</div>
          <div class="stat-value ${hasVerdict ? (verdict.score < 30 ? 'stat-critical' : verdict.score < 50 ? 'stat-high' : verdict.score < 70 ? 'stat-medium' : 'stat-low') : 'stat-info'}">
            ${hasVerdict ? `${verdict.score.toFixed(1)}/100` : '—'}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Material Asymmetries</div>
          <div class="stat-value ${hasVerdict && verdict.material_asymmetries > 0 ? 'stat-high' : 'stat-low'}">
            ${hasVerdict ? verdict.material_asymmetries : 0}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Critical Issues</div>
          <div class="stat-value ${hasVerdict && verdict.critical_issues > 0 ? 'stat-critical' : 'stat-low'}">
            ${hasVerdict ? verdict.critical_issues : 0}
          </div>
        </div>
      </div>

      <div class="grid grid-2" style="margin-bottom: 24px;">
        <div class="card">
          <div class="card-header">
            <div class="card-title">Company Overview</div>
          </div>
          <div class="card-body">
            <div class="grid grid-2">
              <div>
                <h4 style="color: var(--color-primary); margin-bottom: 12px;">${txn.company_a_name}</h4>
                <p><strong>Role:</strong> ${txn.company_a_role}</p>
                <p><strong>Documents:</strong> ${txn.company_a_doc_count || 0}</p>
                <p><strong>Positions:</strong> ${txn.company_a_positions || 0}</p>
              </div>
              <div>
                <h4 style="color: var(--color-accent); margin-bottom: 12px;">${txn.company_b_name}</h4>
                <p><strong>Role:</strong> ${txn.company_b_role}</p>
                <p><strong>Documents:</strong> ${txn.company_b_doc_count || 0}</p>
                <p><strong>Positions:</strong> ${txn.company_b_positions || 0}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Deal Assessment</div>
          </div>
          <div class="card-body">
            <p style="margin-bottom: 16px;">${hasVerdict ? verdict.overall_assessment : 'Run a comparison to see deal assessment'}</p>
            ${hasVerdict ? `
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div><strong>Evidence-Backed Findings:</strong> ${verdict.evidence_backed_findings}</div>
                <div><strong>Key Asymmetries:</strong> ${verdict.key_asymmetries}</div>
                <div><strong>Confidence:</strong> ${Math.round(verdict.confidence * 100)}%</div>
              </div>
            ` : ''}
          </div>
        </div>
      </div>

      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">Top Issues</div>
        </div>
        <div class="card-body">
          ${hasVerdict && comp.findings.length > 0 ? this.renderFindingsTable(comp.findings.slice(0, 10)) : `
            <div class="empty-state">
              <div class="empty-icon">✓</div>
              <p>No material findings detected</p>
            </div>
          `}
        </div>
      </div>

      <div class="grid grid-2">
        <div class="card">
          <div class="card-header">
            <div class="card-title">Party Strategy: ${txn.company_a_name}</div>
          </div>
          <div class="card-body">
            ${hasVerdict && verdict.company_a_recommendations.length > 0 ? `
              <div style="display: flex; flex-direction: column; gap: 10px;">
                ${verdict.company_a_recommendations.slice(0, 5).map((rec) => `
                  <div class="card" style="border-left: 4px solid var(--color-accent);">
                    <div class="card-body" style="padding: 12px 16px;">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                          <strong>${rec.title}</strong>
                          <span class="badge ${getSeverityClass(rec.priority)}" style="margin-left: 8px;">${rec.priority}</span>
                        </div>
                      </div>
                      <p style="margin: 8px 0; font-size: 13px; color: var(--color-text-secondary);">${rec.description}</p>
                      <p style="font-size: 12px; color: var(--color-text-muted);"><em>${rec.proposed_adjustment}</em></p>
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : `
              <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No specific recommendations</p>
              </div>
            `}
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Party Strategy: ${txn.company_b_name}</div>
          </div>
          <div class="card-body">
            ${hasVerdict && verdict.company_b_recommendations.length > 0 ? `
              <div style="display: flex; flex-direction: column; gap: 10px;">
                ${verdict.company_b_recommendations.slice(0, 5).map((rec) => `
                  <div class="card" style="border-left: 4px solid var(--color-primary);">
                    <div class="card-body" style="padding: 12px 16px;">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                          <strong>${rec.title}</strong>
                          <span class="badge ${getSeverityClass(rec.priority)}" style="margin-left: 8px;">${rec.priority}</span>
                        </div>
                      </div>
                      <p style="margin: 8px 0; font-size: 13px; color: var(--color-text-secondary);">${rec.description}</p>
                      <p style="font-size: 12px; color: var(--color-text-muted);"><em>${rec.proposed_adjustment}</em></p>
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : `
              <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No specific recommendations</p>
              </div>
            `}
          </div>
        </div>
      </div>

      ${hasVerdict && comp.id ? `
        <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn btn-secondary" id="view-full-analysis" data-comp-id="${comp.id}">Full Analysis</button>
          <a class="btn btn-primary" href="/comparison/${comp.id}/export" target="_blank">Export Report</a>
        </div>
      ` : ''}
    `;
    }
    renderFindingsTable(findings) {
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
              <th>Impact</th>
              <th>Actions</th>
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
                <td style="max-width: 250px;">${truncate(f.legal_impact, 100)}</td>
                <td>
                  <button class="btn btn-ghost btn-sm" data-finding-id="${f.id}" data-comp-id="${this.app.getCurrentComparisonId()}">View</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
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
        this.container.querySelector('#create-first-txn')?.addEventListener('click', () => {
            // Open new transaction modal
        });
        this.container.querySelector('#view-full-analysis')?.addEventListener('click', (e) => {
            const btn = e.target;
            const compId = btn.getAttribute('data-comp-id');
            if (compId)
                this.app.goToComparisonDetail(compId);
        });
    }
}
