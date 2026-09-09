import { api } from '@/api';
import { formatDate, getSeverityClass, getStatusClass } from '@/utils/helpers';

export class ComparisonsView {
  private container: HTMLElement;
  private app: any;

  constructor(container: HTMLElement, app: any) {
    this.container = container;
    this.app = app;
  }

  async mount() {
    this.renderLoading();
    await this.loadData();
    this.render();
    this.bindEvents();
  }

  private renderLoading() {
    this.container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
  }

  private async loadData() {
    this.app.comparisons = await api.comparisons.list();
  }

  private render() {
    this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>Comparisons</h1>
          <p style="color: var(--color-text-secondary);">View and manage A vs B legal comparisons</p>
        </div>
      </div>

      <div class="card">
        <div class="card-body" style="padding: 0;">
          ${this.app.comparisons.length === 0 ? `
            <div class="empty-state" style="padding: 64px 24px;">
              <div class="empty-icon">⚖️</div>
              <h3 class="empty-title">No Comparisons</h3>
              <p class="empty-desc">Run a comparison between two parties to see analysis</p>
            </div>
          ` : `
            <div class="table-container" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Parties</th>
                    <th>Matched</th>
                    <th>Findings</th>
                    <th>Material</th>
                    <th>Cross-Doc Risks</th>
                    <th>Disclosure</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.app.comparisons.map((comp: any) => `
                    <tr>
                      <td>
                        <strong>${comp.transaction_name}</strong>
                      </td>
                      <td>
                        <div>${comp.company_a_name} vs ${comp.company_b_name}</div>
                      </td>
                      <td>${comp.matched_provisions}</td>
                      <td>${comp.findings_count}</td>
                      <td><span class="badge ${getSeverityClass('material')}" style="background: ${comp.material_asymmetries_count > 0 ? 'var(--color-high-light)' : 'var(--color-low-light)'}; color: ${comp.material_asymmetries_count > 0 ? 'var(--color-high)' : 'var(--color-low)'};">
                        ${comp.material_asymmetries_count}
                      </span></td>
                      <td>${comp.cross_document_risks_count}</td>
                      <td>${comp.disclosure_issues_count}</td>
                      <td><span class="badge ${getStatusClass(comp.status)}">${comp.status}</span></td>
                      <td>
                        <button class="btn btn-ghost btn-sm" data-action="view" data-id="${comp.id}">View Detail</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    `;
  }

  private bindEvents() {
    this.container.querySelectorAll('[data-action="view"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id) this.app.goToComparisonDetail(id);
      });
    });
  }
}