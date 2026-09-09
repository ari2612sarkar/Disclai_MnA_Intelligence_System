import { api } from '@/api';
export class UploadModal {
    constructor(app, options) {
        this.overlay = null;
        this.app = app;
        this.transactionId = options?.transactionId || this.app.getCurrentTransactionId() || '';
        this.companyId = options?.companyId || '';
        this.role = options?.role || '';
    }
    async open() {
        if (!this.transactionId) {
            alert('Please select a transaction first');
            return;
        }
        if (!this.companyId) {
            alert('Please select a company');
            return;
        }
        this.render();
        this.bindEvents();
    }
    render() {
        const html = `
      <div class="modal" style="max-width: 560px;">
        <div class="modal-header">
          <h2 class="modal-title">Upload Document</h2>
          <button class="modal-close" id="close-modal" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="upload-form">
            <div class="form-group">
              <label class="form-label">Transaction</label>
              <input type="text" class="form-input" value="${this.transactionId}" disabled style="color: var(--color-text-muted);">
            </div>
            <div class="form-group">
              <label class="form-label">Company</label>
              <input type="text" class="form-input" value="${this.companyId}" disabled style="color: var(--color-text-muted);">
            </div>
            <div class="form-group">
              <label class="form-label" for="role-select">Role in Document</label>
              <select class="form-select" id="role-select" name="role_in_document" required>
                <option value="">Select role</option>
                <option value="Seller">Seller</option>
                <option value="Buyer">Buyer</option>
                <option value="Target">Target</option>
                <option value="Company">Company</option>
                <option value="Parent">Parent</option>
                <option value="Unknown">Unknown</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="doc-type-select">Document Type</label>
              <select class="form-select" id="doc-type-select" name="document_type" required>
                <option value="">Select type</option>
                <option value="SPA">Share Purchase Agreement (SPA)</option>
                <option value="Merger Agreement">Merger Agreement</option>
                <option value="Disclosure Schedule">Disclosure Schedule</option>
                <option value="Commercial Contract">Commercial Contract</option>
                <option value="Litigation Document">Litigation Document</option>
                <option value="Employment Document">Employment Document</option>
                <option value="IP Document">IP Document</option>
                <option value="Financing Document">Financing Document</option>
                <option value="Regulatory Document">Regulatory Document</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">PDF File</label>
              <div class="upload-zone" id="upload-zone">
                <input type="file" id="file-input" name="file" accept=".pdf" hidden required>
                <div class="upload-icon">📄</div>
                <div class="upload-text">Drag & drop a PDF or click to browse</div>
                <div class="upload-hint">Maximum file size: 50MB · PDF only</div>
                <div id="file-name" style="margin-top: 12px; font-size: 13px; color: var(--color-text-secondary);"></div>
              </div>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
          <button class="btn btn-primary" id="submit-btn" type="submit" form="upload-form" disabled>Upload & Analyze</button>
        </div>
      </div>
    `;
        const modalsContainer = this.app.root.querySelector('#modals');
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.innerHTML = html;
        modalsContainer.appendChild(this.overlay);
    }
    bindEvents() {
        const closeBtn = this.overlay?.querySelector('#close-modal');
        const cancelBtn = this.overlay?.querySelector('#cancel-btn');
        const formEl = this.overlay?.querySelector('#upload-form');
        const fileInput = this.overlay?.querySelector('#file-input');
        const uploadZone = this.overlay?.querySelector('#upload-zone');
        const fileNameEl = this.overlay?.querySelector('#file-name');
        const submitBtn = this.overlay?.querySelector('#submit-btn');
        const close = () => this.close();
        closeBtn?.addEventListener('click', close);
        cancelBtn?.addEventListener('click', close);
        this.overlay?.addEventListener('click', (e) => {
            if (e.target === this.overlay)
                close();
        });
        // Drag & drop
        uploadZone?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-active');
        });
        uploadZone?.addEventListener('dragleave', () => {
            uploadZone.classList.remove('drag-active');
        });
        uploadZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-active');
            if (e.dataTransfer?.files.length) {
                fileInput.files = e.dataTransfer.files;
                this.updateFileName(fileInput, fileNameEl, submitBtn);
            }
        });
        uploadZone?.addEventListener('click', () => fileInput.click());
        fileInput?.addEventListener('change', () => this.updateFileName(fileInput, fileNameEl, submitBtn));
        formEl?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files?.length)
                return;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Uploading...';
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('transaction_id', this.transactionId);
            formData.append('company_id', this.companyId);
            formData.append('role_in_document', (this.overlay?.querySelector('#role-select')).value);
            formData.append('document_type', (this.overlay?.querySelector('#doc-type-select')).value);
            try {
                const result = await api.documents.upload(fileInput.files[0], {
                    transaction_id: this.transactionId,
                    company_id: this.companyId,
                    role_in_document: (this.overlay?.querySelector('#role-select')).value,
                    document_type: (this.overlay?.querySelector('#doc-type-select')).value,
                });
                // Auto-run analysis
                submitBtn.textContent = 'Running analysis...';
                await api.analysis.run(result.document_id);
                this.close();
                // Refresh documents view
                if (this.app.currentView === 'documents') {
                    this.app.renderView('documents');
                }
            }
            catch (err) {
                alert(err.message || 'Upload failed');
            }
            finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Upload & Analyze';
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape')
                this.close();
        });
    }
    updateFileName(fileInput, fileNameEl, submitBtn) {
        if (fileInput.files?.length) {
            const file = fileInput.files[0];
            fileNameEl.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
            submitBtn.disabled = false;
        }
        else {
            fileNameEl.textContent = '';
            submitBtn.disabled = true;
        }
    }
    close() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    }
}
