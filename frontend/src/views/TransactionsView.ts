import { api } from '@/api';
import { formatCurrency, formatDate, getStatusClass } from '@/utils/helpers';

export class TransactionsView {
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
    this.app.transactions = await api.transactions.list();
  }

  private render() {
    this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>Transactions</h1>
          <p style="color: var(--color-text-secondary);">Manage M&A transactions and deal data</p>
        </div>
      </div>

      <div class="card">
        <div class="card-body" style="padding: 0;">
          ${this.app.transactions.length === 0 ? `
            <div class="empty-state" style="padding: 64px 24px;">
              <div class="empty-icon">📋</div>
              <h3 class="empty-title">No Transactions</h3>
              <p class="empty-desc">Create your first transaction to begin</p>
            </div>
          ` : `
            <div class="table-container" style="border: none; border-radius: 0;">
              <table class="table">
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Parties</th>
                    <th>Deal Value</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.app.transactions.map((txn: any) => `
                    <tr>
                      <td>
                        <strong>${txn.name}</strong>
                      </td>
                      <td>
                        <div>${txn.company_a_name} <span style="color: var(--color-text-muted); font-size: 12px;">(${txn.company_a_role})</span></div>
                        <div style="color: var(--color-text-secondary); font-size: 13px;">${txn.company_b_name} <span style="color: var(--color-text-muted); font-size: 12px;">(${txn.company_b_role})</span></div>
                      </td>
                      <td>${formatCurrency(txn.deal_value)}</td>
                      <td><span class="badge ${getStatusClass(txn.status)}">${txn.status}</span></td>
                      <td>${formatDate(txn.created_at)}</td>
                      <td>
                        <div style="display: flex; gap: 8px;">
                          <button class="btn btn-ghost btn-sm" data-action="view" data-id="${txn.id}">View</button>
                          <button class="btn btn-ghost btn-sm" data-action="documents" data-id="${txn.id}">Data Room</button>
                          <button class="btn btn-ghost btn-sm" data-action="compare" data-id="${txn.id}">Compare</button>
                        </div>
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
        if (id) window.location.hash = `#/transactions/${id}`;
      });
    });

    this.container.querySelectorAll('[data-action="documents"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id) this.app.goToDocuments(id);
      });
    });

    this.container.querySelectorAll('[data-action="compare"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id) window.location.hash = `#/transactions/${id}/compare`;
      });
    });
  }
}