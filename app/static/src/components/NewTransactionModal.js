export class NewTransactionModal {
    constructor(app) {
        this.overlay = null;
        this.app = app;
    }
    open() {
        this.render();
        this.bindEvents();
    }
    render() {
        const modalsContainer = this.app.root.querySelector('#modals');
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.innerHTML = `
      <div class="modal" style="max-width: 560px;">
        <div class="modal-header">
          <h2 class="modal-title">Create Transaction</h2>
          <button class="modal-close" id="close-modal" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="transaction-form">
            <div class="form-group">
              <label class="form-label" for="txn-name">Transaction Name</label>
              <input type="text" class="form-input" id="txn-name" name="name" placeholder="e.g., Northstar-Vertex Acquisition" required>
            </div>
            <div class="form-group">
              <label class="form-label" for="txn-description">Description (optional)</label>
              <textarea class="form-textarea" id="txn-description" name="description" rows="3" placeholder="Brief description of the transaction"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label" for="txn-deal-value">Deal Value (USD)</label>
              <input type="number" class="form-input" id="txn-deal-value" name="deal_value" placeholder="50000000" step="1000000">
            </div>
            <hr style="margin: 16px 0; border-color: var(--color-border);">
            <h4 style="margin-bottom: 12px; font-size: 14px;">Company A (Party 1)</h4>
            <div class="form-group">
              <label class="form-label" for="ca-name">Company A Name</label>
              <input type="text" class="form-input" id="ca-name" name="company_a_name" placeholder="e.g., Northstar Technologies Pvt. Ltd." required>
            </div>
            <div class="form-group">
              <label class="form-label" for="ca-role">Company A Role</label>
              <select class="form-select" id="ca-role" name="company_a_role" required>
                <option value="">Select role</option>
                <option value="Seller">Seller</option>
                <option value="Buyer">Buyer</option>
                <option value="Target">Target</option>
                <option value="Acquirer">Acquirer</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="ca-desc">Company A Description (optional)</label>
              <input type="text" class="form-input" id="ca-desc" name="company_a_description" placeholder="Brief description">
            </div>
            <hr style="margin: 16px 0; border-color: var(--color-border);">
            <h4 style="margin-bottom: 12px; font-size: 14px;">Company B (Party 2)</h4>
            <div class="form-group">
              <label class="form-label" for="cb-name">Company B Name</label>
              <input type="text" class="form-input" id="cb-name" name="company_b_name" placeholder="e.g., Vertex Systems Pvt. Ltd." required>
            </div>
            <div class="form-group">
              <label class="form-label" for="cb-role">Company B Role</label>
              <select class="form-select" id="cb-role" name="company_b_role" required>
                <option value="">Select role</option>
                <option value="Seller">Seller</option>
                <option value="Buyer">Buyer</option>
                <option value="Target">Target</option>
                <option value="Acquirer">Acquirer</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="cb-desc">Company B Description (optional)</label>
              <input type="text" class="form-input" id="cb-desc" name="company_b_description" placeholder="Brief description">
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
          <button class="btn btn-primary" id="submit-btn" type="submit" form="transaction-form">Create Transaction</button>
        </div>
      </div>
    `;
        modalsContainer.appendChild(this.overlay);
        this.overlay.querySelector('#txn-name')?.focus();
    }
    bindEvents() {
        const closeBtn = this.overlay?.querySelector('#close-modal');
        const cancelBtn = this.overlay?.querySelector('#cancel-btn');
        const form = this.overlay?.querySelector('#transaction-form');
        const close = () => this.close();
        closeBtn?.addEventListener('click', close);
        cancelBtn?.addEventListener('click', close);
        this.overlay?.addEventListener('click', (e) => {
            if (e.target === this.overlay)
                close();
        });
        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = {
                name: formData.get('name'),
                description: formData.get('description') || '',
                deal_value: formData.get('deal_value') ? parseFloat(formData.get('deal_value')) : undefined,
                company_a_name: formData.get('company_a_name'),
                company_a_role: formData.get('company_a_role'),
                company_a_description: formData.get('company_a_description') || '',
                company_b_name: formData.get('company_b_name'),
                company_b_role: formData.get('company_b_role'),
                company_b_description: formData.get('company_b_description') || '',
            };
            const submitBtn = this.overlay?.querySelector('#submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating...';
            try {
                const txn = await this.app.api.transactions.create(data);
                this.close();
                await this.app.refreshTransactions();
                this.app.setCurrentTransactionId(txn.id);
                this.app.switchView('documents');
            }
            catch (err) {
                alert(err.message || 'Failed to create transaction');
            }
            finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Transaction';
            }
        });
        // Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape')
                this.close();
        };
        document.addEventListener('keydown', handleEscape);
        this.overlay?.setAttribute('data-escape-handler', 'true');
    }
    close() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
            document.removeEventListener('keydown', (e) => {
                if (e.key === 'Escape')
                    this.close();
            });
        }
    }
}
