import { api } from '@/api';
import { getStatusClass } from '@/utils/helpers';
export class DocumentsView {
    constructor(container, app) {
        this.transactionId = null;
        this.companyADocs = [];
        this.companyBDocs = [];
        this.container = container;
        this.app = app;
    }
    async mount() {
        this.transactionId = this.app.getCurrentTransactionId();
        if (!this.transactionId) {
            this.renderNoTransaction();
            return;
        }
        this.renderLoading();
        await this.loadData();
        this.render();
        this.bindEvents();
    }
    renderNoTransaction() {
        this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px;">
        <h1>Data Room</h1>
        <p style="color: var(--color-text-secondary);">Select a transaction to view documents</p>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="empty-state">
            <div class="empty-icon">📁</div>
            <h3 class="empty-title">No Transaction Selected</h3>
            <p class="empty-desc">Navigate from a transaction to access its data room</p>
          </div>
        </div>
      </div>
    `;
    }
    renderLoading() {
        this.container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
    }
    async loadData() {
        if (!this.transactionId)
            return;
        try {
            const response = await api.documents.list(this.transactionId);
            // The API returns company_a_documents and company_b_documents
            this.companyADocs = response.company_a_documents || [];
            this.companyBDocs = response.company_b_documents || [];
        }
        catch (e) {
            console.warn('Failed to load documents:', e);
        }
    }
    render() {
        this.container.innerHTML = `
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>Data Room</h1>
          <p style="color: var(--color-text-secondary);">Upload and manage transaction documents</p>
        </div>
      </div>

      <div class="grid grid-2" style="margin-bottom: 24px;">
        <div class="card">
          <div class="card-header">
            <div class="card-title" style="color: var(--color-primary);">Company A Documents</div>
            <button class="btn btn-ghost btn-sm" id="upload-a-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              Upload
            </button>
          </div>
          <div class="card-body" style="padding: 0;">
            ${this.renderDocumentList(this.companyADocs, 'A')}
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title" style="color: var(--color-accent);">Company B Documents</div>
            <button class="btn btn-ghost btn-sm" id="upload-b-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              Upload
            </button>
          </div>
          <div class="card-body" style="padding: 0;">
            ${this.renderDocumentList(this.companyBDocs, 'B')}
          </div>
        </div>
      </div>
    `;
    }
    renderDocumentList(docs, company) {
        if (docs.length === 0) {
            return `
        <div class="empty-state" style="padding: 32px 24px;">
          <div class="empty-icon">📄</div>
          <p class="empty-desc">No documents uploaded</p>
        </div>
      `;
        }
        return `
      <div style="display: flex; flex-direction: column;">
        ${docs.map(doc => `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--color-border);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 40px; height: 40px; background: var(--color-primary-light); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; color: var(--color-primary);">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              <div>
                <div style="font-weight: 500;">${doc.filename}</div>
                <div style="font-size: 12px; color: var(--color-text-muted);">${doc.page_count} pages · ${doc.document_type}</div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge ${getStatusClass(doc.analysis_status)}">${doc.analysis_status}</span>
              ${doc.run_id ? `<button class="btn btn-ghost btn-sm" data-action="analyze" data-doc-id="${doc.id}" data-run-id="${doc.run_id}">Analyze</button>` : ''}
              <button class="btn btn-ghost btn-sm" data-action="view" data-doc-id="${doc.id}">View</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    }
    bindEvents() {
        this.container.querySelector('#upload-a-btn')?.addEventListener('click', () => {
            // TODO: Open upload modal for Company A
        });
        this.container.querySelector('#upload-b-btn')?.addEventListener('click', () => {
            // TODO: Open upload modal for Company B
        });
        this.container.querySelectorAll('[data-action="analyze"]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const docId = e.currentTarget.getAttribute('data-doc-id');
                if (docId) {
                    await api.analysis.run(docId);
                    this.loadData().then(() => this.render());
                }
            });
        });
        this.container.querySelectorAll('[data-action="view"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const docId = e.currentTarget.getAttribute('data-doc-id');
                if (docId)
                    window.open(`/api/documents/${docId}`, '_blank');
            });
        });
    }
}
