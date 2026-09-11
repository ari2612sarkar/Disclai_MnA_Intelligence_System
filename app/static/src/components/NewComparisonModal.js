import { api } from '@/api';
export class NewComparisonModal {
    constructor(app) {
        this.overlay = null;
        this.transactions = [];
        this.app = app;
    }
    async open() {
        this.transactions = await api.transactions.list();
        this.render();
        this.bindEvents();
    }
    getModalHtml() {
        const optionsHtml = this.transactions.map(t => `<option value="${t.id}">${t.name} (${t.company_a_name} vs ${t.company_b_name})</option>`).join('');
        return `
      <div class="modal" style="max-width: 600px;">
        <div class="modal-header">
          <h2 class="modal-title">Run New Comparison</h2>
          <button class="modal-close" id="close-modal" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="comparison-form">
            <div class="form-group">
              <label class="form-label" for="txn-select">Transaction</label>
              <select class="form-select" id="txn-select" name="transaction_id" required>
                <option value="">Select transaction</option>
                ${optionsHtml}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Company A Analysis Run</label>
              <select class="form-select" id="run-a-select" name="company_a_run_id" required disabled>
                <option value="">Select transaction first</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Company B Analysis Run</label>
              <select class="form-select" id="run-b-select" name="company_b_run_id" required disabled>
                <option value="">Select transaction first</option>
              </select>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
          <button class="btn btn-primary" id="submit-btn" type="submit" form="comparison-form" disabled>Run Comparison</button>
        </div>
      </div>
    `;
    }
    render() {
        const modalsContainer = this.app.root.querySelector('#modals');
        this.overlay = document.createElement('div');
        this.overlay.className = 'modal-overlay';
        this.overlay.innerHTML = this.getModalHtml();
        modalsContainer.appendChild(this.overlay);
    }
    bindEvents() {
        const closeBtn = this.overlay?.querySelector('#close-modal');
        const cancelBtn = this.overlay?.querySelector('#cancel-btn');
        const formEl = this.overlay?.querySelector('#comparison-form');
        const txnSelect = this.overlay?.querySelector('#txn-select');
        const runASelect = this.overlay?.querySelector('#run-a-select');
        const runBSelect = this.overlay?.querySelector('#run-b-select');
        const submitBtn = this.overlay?.querySelector('#submit-btn');
        const close = () => this.close();
        closeBtn?.addEventListener('click', close);
        cancelBtn?.addEventListener('click', close);
        this.overlay?.addEventListener('click', (e) => {
            if (e.target === this.overlay)
                close();
        });
        // Transaction selection -> load runs
        txnSelect?.addEventListener('change', async () => {
            const txnId = txnSelect.value;
            runASelect.innerHTML = '<option value="">Loading...</option>';
            runBSelect.innerHTML = '<option value="">Loading...</option>';
            runASelect.disabled = true;
            runBSelect.disabled = true;
            submitBtn.disabled = true;
            if (!txnId)
                return;
            try {
                const txn = await api.transactions.get(txnSelect.value);
                const companyAId = txn.company_a_id;
                const companyBId = txn.company_b_id;
                // Get runs for each company
                const runsA = await this.getCompanyRuns(companyAId);
                const runsB = await this.getCompanyRuns(companyBId);
                runASelect.innerHTML = '<option value="">Select Company A run</option>' +
                    runsA.map((r) => `<option value="${r.id}">${r.id.slice(0, 8)} - ${r.provisions_extracted} positions - ${new Date(r.started_at).toLocaleDateString()}</option>`).join('');
                runBSelect.innerHTML = '<option value="">Select Company B run</option>' +
                    runsB.map((r) => `<option value="${r.id}">${r.id.slice(0, 8)} - ${r.provisions_extracted} positions - ${new Date(r.started_at).toLocaleDateString()}</option>`).join('');
                runASelect.disabled = false;
                runBSelect.disabled = false;
                this.updateSubmitBtn(submitBtn, runASelect, runBSelect);
            }
            catch (err) {
                console.error('Failed to load runs:', err);
                runASelect.innerHTML = '<option value="">Error loading runs</option>';
                runBSelect.innerHTML = '<option value="">Error loading runs</option>';
            }
        });
        runASelect?.addEventListener('change', () => this.updateSubmitBtn(submitBtn, runASelect, runBSelect));
        runBSelect?.addEventListener('change', () => this.updateSubmitBtn(submitBtn, runASelect, runBSelect));
        formEl?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const txnSelect = this.overlay?.querySelector('#txn-select');
            const runASelect = this.overlay?.querySelector('#run-a-select');
            const runBSelect = this.overlay?.querySelector('#run-b-select');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Running...';
            try {
                const comp = await api.comparison.run({
                    transaction_id: txnSelect.value,
                    company_a_run_id: runASelect.value,
                    company_b_run_id: runBSelect.value,
                });
                this.close();
                await this.app.refreshComparisons();
                this.app.goToComparisonDetail(comp.id);
            }
            catch (err) {
                alert(err.message || 'Failed to run comparison');
            }
            finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Run Comparison';
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape')
                this.close();
        });
    }
    updateSubmitBtn(submitBtn, runASelect, runBSelect) {
        submitBtn.disabled = !runASelect.value || !runBSelect.value;
    }
    async getCompanyRuns(companyId) {
        // This would need a proper API endpoint; for now return empty
        return [];
    }
    close() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    }
}
