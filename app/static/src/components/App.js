import { api } from '@/api';
import { DashboardView } from '@/views/DashboardView';
import { TransactionsView } from '@/views/TransactionsView';
import { ComparisonsView } from '@/views/ComparisonsView';
import { DocumentsView } from '@/views/DocumentsView';
import { ComparisonDetailView } from '@/views/ComparisonDetailView';
import { NewTransactionModal } from '@/components/NewTransactionModal';
import { NewComparisonModal } from '@/components/NewComparisonModal';
import { UploadModal } from '@/components/UploadModal';
export class App {
    constructor(root) {
        this.currentView = 'dashboard';
        this.currentTransactionId = null;
        this.currentComparisonId = null;
        this.transactions = [];
        this.comparisons = [];
        this.sidebarOpen = true;
        this.root = root;
    }
    async mount() {
        this.render();
        this.bindEvents();
        await this.loadInitialData();
    }
    render() {
        this.root.innerHTML = `
      <div class="layout">
        <aside class="sidebar" id="sidebar">
          <div class="brand">
            <div class="brand-icon">D</div>
            <div class="brand-text">
              <span class="brand-name">DISCLAI</span>
              <span class="brand-tagline">Transaction Intelligence</span>
            </div>
          </div>
          <nav class="nav" id="nav">
            <div class="nav-section">
              <div class="nav-section-title">Main</div>
              <button class="nav-item active" data-view="dashboard">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
                </svg>
                Dashboard
              </button>
              <button class="nav-item" data-view="transactions">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 12V7H5V7M3 18H18M3 12H18M3 6H18"/>
                </svg>
                Transactions
              </button>
            </div>
            <div class="nav-section">
              <div class="nav-section-title">Analysis</div>
              <button class="nav-item" data-view="comparisons">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h8M13 12h8M13 18h8M6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                </svg>
                Comparisons
              </button>
              <button class="nav-item" data-view="documents">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
                </svg>
                Data Room
              </button>
            </div>
          </nav>
        </aside>
        <div class="main-content">
          <header class="header" id="header">
            <div class="header-left">
              <button class="btn btn-ghost btn-icon" id="sidebar-toggle" aria-label="Toggle sidebar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
              </button>
              <nav class="breadcrumb" id="breadcrumb">
                <span class="page-title" id="page-title">Dashboard</span>
              </nav>
            </div>
            <div class="header-right">
              <div id="header-actions"></div>
            </div>
          </header>
          <main class="content" id="content">
            <!-- View content rendered here -->
          </main>
        </div>
      </div>
      <div id="modals"></div>
    `;
    }
    bindEvents() {
        // Sidebar navigation
        const navItems = this.root.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const view = item.getAttribute('data-view');
                this.switchView(view);
            });
        });
        // Sidebar toggle
        const sidebarToggle = this.root.querySelector('#sidebar-toggle');
        sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
        // Header actions will be bound per view
    }
    toggleSidebar() {
        this.sidebarOpen = !this.sidebarOpen;
        const sidebar = this.root.querySelector('#sidebar');
        sidebar.style.transform = this.sidebarOpen ? 'translateX(0)' : 'translateX(-100%)';
    }
    switchView(view) {
        this.currentView = view;
        this.currentComparisonId = null;
        // Update nav active state
        this.root.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-view') === view);
        });
        // Update page title
        const titles = {
            dashboard: 'Dashboard',
            transactions: 'Transactions',
            comparisons: 'Comparisons',
            documents: 'Data Room',
            'comparison-detail': 'Comparison Detail',
        };
        const titleEl = this.root.querySelector('#page-title');
        if (titleEl)
            titleEl.textContent = titles[view];
        // Render view
        this.renderView(view);
    }
    async renderView(view) {
        const content = this.root.querySelector('#content');
        const headerActions = this.root.querySelector('#header-actions');
        switch (view) {
            case 'dashboard':
                headerActions.innerHTML = '';
                content.innerHTML = '<div id="dashboard-view"></div>';
                new DashboardView(content.querySelector('#dashboard-view'), this).mount();
                break;
            case 'transactions':
                headerActions.innerHTML = `
          <button class="btn btn-primary" id="new-transaction-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Transaction
          </button>
        `;
                content.innerHTML = '<div id="transactions-view"></div>';
                new TransactionsView(content.querySelector('#transactions-view'), this).mount();
                this.root.querySelector('#new-transaction-btn')?.addEventListener('click', () => new NewTransactionModal(this).open());
                break;
            case 'comparisons':
                headerActions.innerHTML = `
          <button class="btn btn-primary" id="new-comparison-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Comparison
          </button>
        `;
                content.innerHTML = '<div id="comparisons-view"></div>';
                new ComparisonsView(content.querySelector('#comparisons-view'), this).mount();
                this.root.querySelector('#new-comparison-btn')?.addEventListener('click', () => new NewComparisonModal(this).open());
                break;
            case 'documents':
                headerActions.innerHTML = `
          <button class="btn btn-primary" id="upload-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload
          </button>
        `;
                content.innerHTML = '<div id="documents-view"></div>';
                new DocumentsView(content.querySelector('#documents-view'), this).mount();
                this.root.querySelector('#upload-btn')?.addEventListener('click', () => new UploadModal(this).open());
                break;
            case 'comparison-detail':
                headerActions.innerHTML = `
          <a class="btn btn-secondary" id="export-btn" target="_blank" href="/comparison/${this.currentComparisonId}/export">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export Report
          </a>
        `;
                content.innerHTML = '<div id="comparison-detail-view"></div>';
                if (this.currentComparisonId) {
                    new ComparisonDetailView(content.querySelector('#comparison-detail-view'), this, this.currentComparisonId).mount();
                }
                break;
        }
    }
    async loadInitialData() {
        try {
            const [txns, comps] = await Promise.all([
                api.transactions.list().catch(() => []),
                api.comparisons.list().catch(() => []),
            ]);
            this.transactions = txns;
            this.comparisons = comps;
        }
        catch (e) {
            console.warn('Failed to load initial data:', e);
        }
    }
    // Getters for views
    getTransactions() { return this.transactions; }
    getComparisons() { return this.comparisons; }
    getCurrentTransactionId() { return this.currentTransactionId; }
    setCurrentTransactionId(id) { this.currentTransactionId = id; }
    getCurrentComparisonId() { return this.currentComparisonId; }
    setCurrentComparisonId(id) { this.currentComparisonId = id; }
    // Navigation helpers
    goToComparisonDetail(comparisonId) {
        this.currentComparisonId = comparisonId;
        this.switchView('comparison-detail');
    }
    goToDocuments(transactionId) {
        this.currentTransactionId = transactionId;
        this.switchView('documents');
    }
    async refreshTransactions() {
        this.transactions = await api.transactions.list();
        if (this.currentView === 'transactions') {
            this.renderView('transactions');
        }
    }
    async refreshComparisons() {
        this.comparisons = await api.comparisons.list();
        if (this.currentView === 'comparisons') {
            this.renderView('comparisons');
        }
    }
}
