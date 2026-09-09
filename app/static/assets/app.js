const E="";async function l(i,t={}){const e=`${E}${i}`,a=await fetch(e,{headers:{"Content-Type":"application/json",...t.headers},...t});if(!a.ok){const n=await a.json().catch(()=>({detail:"Request failed"}));throw new Error(n.detail||`HTTP ${a.status}`)}if(a.status!==204)return a.json()}const p={health:()=>l("/api/health"),companies:{list:()=>l("/api/companies"),create:i=>l("/api/companies",{method:"POST",body:JSON.stringify(i)}),get:i=>l(`/api/companies/${i}`)},transactions:{list:()=>l("/api/transactions"),create:i=>l("/api/transactions",{method:"POST",body:JSON.stringify(i)}),get:i=>l(`/api/transactions/${i}`)},comparisons:{list:()=>l("/api/comparisons")},documents:{upload:(i,t)=>{const e=new FormData;return e.append("file",i),Object.entries(t).forEach(([a,n])=>e.append(a,n)),l("/documents/upload",{method:"POST",headers:{},body:e})},list:i=>l(`/api/documents?transaction_id=${i}`),status:i=>l(`/analysis/status/${i}`)},analysis:{run:i=>l("/api/analysis/run",{method:"POST",body:JSON.stringify({document_id:i})}),get:i=>l(`/api/analysis/${i}`),findings:i=>l(`/api/findings/${i}`),runsForCompany:i=>l(`/api/analysis/runs/company/${i}`)},comparison:{run:i=>l("/api/comparison/run",{method:"POST",body:JSON.stringify(i)}),get:i=>l(`/api/comparison/${i}`),findings:i=>l(`/api/comparison/${i}/findings`),verdict:i=>l(`/api/comparison/${i}/verdict`),recommendations:i=>l(`/api/comparison/${i}/recommendations`),export:i=>fetch(`${E}/comparison/${i}/export`).then(t=>t.text())}};function k(i){return i==null?"—":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",minimumFractionDigits:0,maximumFractionDigits:0}).format(i)}function M(i){return i?new Date(i).toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"}):"—"}function _(i){return{critical:"badge-critical",high:"badge-high",medium:"badge-medium",low:"badge-low",info:"badge-info",potential_asymmetry:"badge-potential",material_asymmetry:"badge-material",presence_absence:"badge-presence",conflict:"badge-conflict",requires_review:"badge-review",no_material_difference:"badge-review",matched:"badge-matched",unmatched:"badge-unmatched",partial:"badge-partial"}[i==null?void 0:i.toLowerCase()]||"badge-info"}function L(i){return{healthy:"status-healthy",completed:"status-healthy",processing:"status-processing",running:"status-processing",failed:"status-failed",pending:"status-pending"}[i==null?void 0:i.toLowerCase()]||"status-pending"}function q(i,t=100){return i?i.length<=t?i:i.slice(0,t-1)+"…":"—"}class I{constructor(t,e){this.container=t,this.app=e}async mount(){this.renderLoading(),await this.loadData(),this.render()}renderLoading(){this.container.innerHTML='<div class="loading"><div class="spinner"></div></div>'}async loadData(){try{const[t,e]=await Promise.all([p.transactions.list().catch(()=>[]),p.comparisons.list().catch(()=>[])]);this.app.transactions=t,this.app.comparisons=e}catch(t){console.warn("Failed to load dashboard data:",t)}}render(){const t=this.app.transactions[0],e=this.app.comparisons[0];this.container.innerHTML=`
      <div class="page-header" style="margin-bottom: 24px;">
        <h1>Dashboard</h1>
        <p style="color: var(--color-text-secondary);">Overview of deal risk, asymmetries, and key findings</p>
      </div>

      ${t?this.renderDashboard(t,e):this.renderEmptyState()}
    `}renderEmptyState(){return`
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
    `}renderDashboard(t,e){const a=e==null?void 0:e.verdict,n=!!a;return`
      <div class="grid grid-4" style="margin-bottom: 24px;">
        <div class="card stat-card">
          <div class="stat-label">Overall Risk</div>
          <div class="stat-value ${n?`stat-${a.overall_risk_level.toLowerCase()}`:"stat-info"}">
            ${n?a.overall_risk_level:"—"}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Deal Score</div>
          <div class="stat-value ${n?a.score<30?"stat-critical":a.score<50?"stat-high":a.score<70?"stat-medium":"stat-low":"stat-info"}">
            ${n?`${a.score.toFixed(1)}/100`:"—"}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Material Asymmetries</div>
          <div class="stat-value ${n&&a.material_asymmetries>0?"stat-high":"stat-low"}">
            ${n?a.material_asymmetries:0}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Critical Issues</div>
          <div class="stat-value ${n&&a.critical_issues>0?"stat-critical":"stat-low"}">
            ${n?a.critical_issues:0}
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
                <h4 style="color: var(--color-primary); margin-bottom: 12px;">${t.company_a_name}</h4>
                <p><strong>Role:</strong> ${t.company_a_role}</p>
                <p><strong>Documents:</strong> ${t.company_a_doc_count||0}</p>
                <p><strong>Positions:</strong> ${t.company_a_positions||0}</p>
              </div>
              <div>
                <h4 style="color: var(--color-accent); margin-bottom: 12px;">${t.company_b_name}</h4>
                <p><strong>Role:</strong> ${t.company_b_role}</p>
                <p><strong>Documents:</strong> ${t.company_b_doc_count||0}</p>
                <p><strong>Positions:</strong> ${t.company_b_positions||0}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Deal Assessment</div>
          </div>
          <div class="card-body">
            <p style="margin-bottom: 16px;">${n?a.overall_assessment:"Run a comparison to see deal assessment"}</p>
            ${n?`
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div><strong>Evidence-Backed Findings:</strong> ${a.evidence_backed_findings}</div>
                <div><strong>Key Asymmetries:</strong> ${a.key_asymmetries}</div>
                <div><strong>Confidence:</strong> ${Math.round(a.confidence*100)}%</div>
              </div>
            `:""}
          </div>
        </div>
      </div>

      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">Top Issues</div>
        </div>
        <div class="card-body">
          ${n&&e.findings.length>0?this.renderFindingsTable(e.findings.slice(0,10)):`
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
            <div class="card-title">Party Strategy: ${t.company_a_name}</div>
          </div>
          <div class="card-body">
            ${n&&a.company_a_recommendations.length>0?`
              <div style="display: flex; flex-direction: column; gap: 10px;">
                ${a.company_a_recommendations.slice(0,5).map(s=>`
                  <div class="card" style="border-left: 4px solid var(--color-accent);">
                    <div class="card-body" style="padding: 12px 16px;">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                          <strong>${s.title}</strong>
                          <span class="badge ${_(s.priority)}" style="margin-left: 8px;">${s.priority}</span>
                        </div>
                      </div>
                      <p style="margin: 8px 0; font-size: 13px; color: var(--color-text-secondary);">${s.description}</p>
                      <p style="font-size: 12px; color: var(--color-text-muted);"><em>${s.proposed_adjustment}</em></p>
                    </div>
                  </div>
                `).join("")}
              </div>
            `:`
              <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No specific recommendations</p>
              </div>
            `}
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Party Strategy: ${t.company_b_name}</div>
          </div>
          <div class="card-body">
            ${n&&a.company_b_recommendations.length>0?`
              <div style="display: flex; flex-direction: column; gap: 10px;">
                ${a.company_b_recommendations.slice(0,5).map(s=>`
                  <div class="card" style="border-left: 4px solid var(--color-primary);">
                    <div class="card-body" style="padding: 12px 16px;">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                          <strong>${s.title}</strong>
                          <span class="badge ${_(s.priority)}" style="margin-left: 8px;">${s.priority}</span>
                        </div>
                      </div>
                      <p style="margin: 8px 0; font-size: 13px; color: var(--color-text-secondary);">${s.description}</p>
                      <p style="font-size: 12px; color: var(--color-text-muted);"><em>${s.proposed_adjustment}</em></p>
                    </div>
                  </div>
                `).join("")}
              </div>
            `:`
              <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No specific recommendations</p>
              </div>
            `}
          </div>
        </div>
      </div>

      ${n&&e.id?`
        <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn btn-secondary" id="view-full-analysis" data-comp-id="${e.id}">Full Analysis</button>
          <a class="btn btn-primary" href="/comparison/${e.id}/export" target="_blank">Export Report</a>
        </div>
      `:""}
    `}renderFindingsTable(t){return`
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
            ${t.map((e,a)=>`
              <tr>
                <td>${a+1}</td>
                <td><strong>${e.provision}</strong></td>
                <td>${e.category}</td>
                <td><span class="badge ${_(e.classification)}">${e.classification.replace(/_/g," ")}</span></td>
                <td>${this.formatPosition(e.company_a_position)}</td>
                <td>${this.formatPosition(e.company_b_position)}</td>
                <td style="max-width: 250px;">${q(e.legal_impact,100)}</td>
                <td>
                  <button class="btn btn-ghost btn-sm" data-finding-id="${e.id}" data-comp-id="${this.app.getCurrentComparisonId()}">View</button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `}formatPosition(t){return t?t.percentage!==void 0?`${t.percentage}%`:t.amount!==void 0?k(t.amount):t.duration?t.duration:"—":"—"}bindEvents(){var t,e;(t=this.container.querySelector("#create-first-txn"))==null||t.addEventListener("click",()=>{}),(e=this.container.querySelector("#view-full-analysis"))==null||e.addEventListener("click",a=>{const s=a.target.getAttribute("data-comp-id");s&&this.app.goToComparisonDetail(s)})}}class H{constructor(t,e){this.container=t,this.app=e}async mount(){this.renderLoading(),await this.loadData(),this.render(),this.bindEvents()}renderLoading(){this.container.innerHTML='<div class="loading"><div class="spinner"></div></div>'}async loadData(){this.app.transactions=await p.transactions.list()}render(){this.container.innerHTML=`
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>Transactions</h1>
          <p style="color: var(--color-text-secondary);">Manage M&A transactions and deal data</p>
        </div>
      </div>

      <div class="card">
        <div class="card-body" style="padding: 0;">
          ${this.app.transactions.length===0?`
            <div class="empty-state" style="padding: 64px 24px;">
              <div class="empty-icon">📋</div>
              <h3 class="empty-title">No Transactions</h3>
              <p class="empty-desc">Create your first transaction to begin</p>
            </div>
          `:`
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
                  ${this.app.transactions.map(t=>`
                    <tr>
                      <td>
                        <strong>${t.name}</strong>
                      </td>
                      <td>
                        <div>${t.company_a_name} <span style="color: var(--color-text-muted); font-size: 12px;">(${t.company_a_role})</span></div>
                        <div style="color: var(--color-text-secondary); font-size: 13px;">${t.company_b_name} <span style="color: var(--color-text-muted); font-size: 12px;">(${t.company_b_role})</span></div>
                      </td>
                      <td>${k(t.deal_value)}</td>
                      <td><span class="badge ${L(t.status)}">${t.status}</span></td>
                      <td>${M(t.created_at)}</td>
                      <td>
                        <div style="display: flex; gap: 8px;">
                          <button class="btn btn-ghost btn-sm" data-action="view" data-id="${t.id}">View</button>
                          <button class="btn btn-ghost btn-sm" data-action="documents" data-id="${t.id}">Data Room</button>
                          <button class="btn btn-ghost btn-sm" data-action="compare" data-id="${t.id}">Compare</button>
                        </div>
                      </td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    `}bindEvents(){this.container.querySelectorAll('[data-action="view"]').forEach(t=>{t.addEventListener("click",e=>{const a=e.currentTarget.getAttribute("data-id");a&&(window.location.hash=`#/transactions/${a}`)})}),this.container.querySelectorAll('[data-action="documents"]').forEach(t=>{t.addEventListener("click",e=>{const a=e.currentTarget.getAttribute("data-id");a&&this.app.goToDocuments(a)})}),this.container.querySelectorAll('[data-action="compare"]').forEach(t=>{t.addEventListener("click",e=>{const a=e.currentTarget.getAttribute("data-id");a&&(window.location.hash=`#/transactions/${a}/compare`)})})}}class B{constructor(t,e){this.container=t,this.app=e}async mount(){this.renderLoading(),await this.loadData(),this.render(),this.bindEvents()}renderLoading(){this.container.innerHTML='<div class="loading"><div class="spinner"></div></div>'}async loadData(){this.app.comparisons=await p.comparisons.list()}render(){this.container.innerHTML=`
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h1>Comparisons</h1>
          <p style="color: var(--color-text-secondary);">View and manage A vs B legal comparisons</p>
        </div>
      </div>

      <div class="card">
        <div class="card-body" style="padding: 0;">
          ${this.app.comparisons.length===0?`
            <div class="empty-state" style="padding: 64px 24px;">
              <div class="empty-icon">⚖️</div>
              <h3 class="empty-title">No Comparisons</h3>
              <p class="empty-desc">Run a comparison between two parties to see analysis</p>
            </div>
          `:`
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
                  ${this.app.comparisons.map(t=>`
                    <tr>
                      <td>
                        <strong>${t.transaction_name}</strong>
                      </td>
                      <td>
                        <div>${t.company_a_name} vs ${t.company_b_name}</div>
                      </td>
                      <td>${t.matched_provisions}</td>
                      <td>${t.findings_count}</td>
                      <td><span class="badge ${_("material")}" style="background: ${t.material_asymmetries_count>0?"var(--color-high-light)":"var(--color-low-light)"}; color: ${t.material_asymmetries_count>0?"var(--color-high)":"var(--color-low)"};">
                        ${t.material_asymmetries_count}
                      </span></td>
                      <td>${t.cross_document_risks_count}</td>
                      <td>${t.disclosure_issues_count}</td>
                      <td><span class="badge ${L(t.status)}">${t.status}</span></td>
                      <td>
                        <button class="btn btn-ghost btn-sm" data-action="view" data-id="${t.id}">View Detail</button>
                      </td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    `}bindEvents(){this.container.querySelectorAll('[data-action="view"]').forEach(t=>{t.addEventListener("click",e=>{const a=e.currentTarget.getAttribute("data-id");a&&this.app.goToComparisonDetail(a)})})}}class P{constructor(t,e){this.transactionId=null,this.companyADocs=[],this.companyBDocs=[],this.companyAId="",this.companyBId="",this.container=t,this.app=e}async mount(){if(this.transactionId=this.app.getCurrentTransactionId(),!this.transactionId){this.renderNoTransaction();return}this.renderLoading(),await this.loadData(),this.render(),this.bindEvents()}renderNoTransaction(){this.container.innerHTML=`
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
    `}renderLoading(){this.container.innerHTML='<div class="loading"><div class="spinner"></div></div>'}async loadData(){if(this.transactionId)try{const[t,e]=await Promise.all([p.documents.list(this.transactionId),p.transactions.get(this.transactionId)]);this.companyADocs=t.company_a_documents||[],this.companyBDocs=t.company_b_documents||[],this.companyAId=e.company_a_id||"",this.companyBId=e.company_b_id||""}catch(t){console.warn("Failed to load documents:",t)}}render(){this.container.innerHTML=`
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
            ${this.renderDocumentList(this.companyADocs,"A")}
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
            ${this.renderDocumentList(this.companyBDocs,"B")}
          </div>
        </div>
      </div>
    `}renderDocumentList(t,e){return t.length===0?`
        <div class="empty-state" style="padding: 32px 24px;">
          <div class="empty-icon">📄</div>
          <p class="empty-desc">No documents uploaded</p>
        </div>
      `:`
      <div style="display: flex; flex-direction: column;">
        ${t.map(a=>`
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--color-border);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 40px; height: 40px; background: var(--color-primary-light); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; color: var(--color-primary);">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              <div>
                <div style="font-weight: 500;">${a.filename}</div>
                <div style="font-size: 12px; color: var(--color-text-muted);">${a.page_count} pages · ${a.document_type}</div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge ${L(a.analysis_status)}">${a.analysis_status}</span>
              ${a.run_id?`<button class="btn btn-ghost btn-sm" data-action="analyze" data-doc-id="${a.id}" data-run-id="${a.run_id}">Analyze</button>`:""}
              <button class="btn btn-ghost btn-sm" data-action="view" data-doc-id="${a.id}">View</button>
            </div>
          </div>
        `).join("")}
      </div>
    `}bindEvents(){var t,e;(t=this.container.querySelector("#upload-a-btn"))==null||t.addEventListener("click",()=>new j(this.app,{transactionId:this.transactionId,companyId:this.companyAId}).open()),(e=this.container.querySelector("#upload-b-btn"))==null||e.addEventListener("click",()=>new j(this.app,{transactionId:this.transactionId,companyId:this.companyBId}).open()),this.container.querySelectorAll('[data-action="analyze"]').forEach(a=>{a.addEventListener("click",async n=>{const s=n.currentTarget.getAttribute("data-doc-id");s&&(await p.analysis.run(s),this.loadData().then(()=>this.render()))})}),this.container.querySelectorAll('[data-action="view"]').forEach(a=>{a.addEventListener("click",n=>{const s=n.currentTarget.getAttribute("data-doc-id");s&&window.open(`/api/documents/${s}`,"_blank")})})}}class N{constructor(t,e,a){this.comparison=null,this.activeTab="findings",this.container=t,this.app=e,this.comparisonId=a}async mount(){this.renderLoading(),await this.loadData(),this.render(),this.bindEvents()}renderLoading(){this.container.innerHTML='<div class="loading"><div class="spinner"></div></div>'}async loadData(){this.comparison=await p.comparison.get(this.comparisonId)}render(){if(!this.comparison)return;const{verdict:t,findings:e,matches:a,cross_document_risks:n,disclosure_issues:s}=this.comparison,o=!!t;this.container.innerHTML=`
      <div class="page-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1>Comparison Detail</h1>
          <p style="color: var(--color-text-secondary);">${this.comparison.transaction_name||"Transaction"}</p>
        </div>
      </div>

      ${o?this.renderVerdictHeader(t):""}

      <div class="tabs" id="comparison-tabs">
        <button class="tab ${this.activeTab==="findings"?"active":""}" data-tab="findings">Findings (${e.length})</button>
        <button class="tab ${this.activeTab==="matches"?"active":""}" data-tab="matches">Matches (${a.length})</button>
        <button class="tab ${this.activeTab==="risks"?"active":""}" data-tab="risks">Cross-Doc Risks (${n.length})</button>
        <button class="tab ${this.activeTab==="disclosure"?"active":""}" data-tab="disclosure">Disclosure Issues (${s.length})</button>
        ${o?`<button class="tab ${this.activeTab==="verdict"?"active":""}" data-tab="verdict">Deal Verdict</button>`:""}
      </div>

      <div id="tab-content">
        ${this.renderTabContent()}
      </div>
    `}renderVerdictHeader(t){return`
      <div class="grid grid-4" style="margin-bottom: 16px;">
        <div class="card stat-card">
          <div class="stat-label">Overall Risk</div>
          <div class="stat-value stat-${t.overall_risk_level.toLowerCase()}">${t.overall_risk_level}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Deal Score</div>
          <div class="stat-value ${t.score<30?"stat-critical":t.score<50?"stat-high":t.score<70?"stat-medium":"stat-low"}">${t.score.toFixed(1)}/100</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Material Asymmetries</div>
          <div class="stat-value ${t.material_asymmetries>0?"stat-high":"stat-low"}">${t.material_asymmetries}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">Confidence</div>
          <div class="stat-value stat-info">${Math.round(t.confidence*100)}%</div>
        </div>
      </div>
    `}renderTabContent(){switch(this.activeTab){case"findings":return this.renderFindingsTab();case"matches":return this.renderMatchesTab();case"risks":return this.renderRisksTab();case"disclosure":return this.renderDisclosureTab();case"verdict":return this.renderVerdictTab();default:return""}}renderFindingsTab(){const{findings:t}=this.comparison;return t.length===0?'<div class="empty-state" style="padding: 48px 24px;"><div class="empty-icon">✓</div><p>No findings</p></div>':`
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
            ${t.map((e,a)=>`
              <tr>
                <td>${a+1}</td>
                <td><strong>${e.provision}</strong></td>
                <td>${e.category}</td>
                <td><span class="badge ${_(e.classification)}">${e.classification.replace(/_/g," ")}</span></td>
                <td>${this.formatPosition(e.company_a_position)}</td>
                <td>${this.formatPosition(e.company_b_position)}</td>
                <td style="max-width: 300px;">${q(e.legal_impact,150)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `}renderMatchesTab(){const{matches:t}=this.comparison;return t.length===0?'<div class="empty-state" style="padding: 48px 24px;"><p>No matches</p></div>':`
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
            ${t.map(e=>`
              <tr>
                <td>${e.company_a_provision||"—"}</td>
                <td>${e.company_b_provision||"—"}</td>
                <td><span class="badge ${_(e.match_status)}">${e.match_status}</span></td>
                <td>${(e.match_confidence*100).toFixed(0)}%</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `}renderRisksTab(){const{cross_document_risks:t}=this.comparison;return t.length===0?'<div class="empty-state" style="padding: 48px 24px;"><p>No cross-document risks identified</p></div>':t.map(e=>`
      <div class="card" style="margin-bottom: 16px;">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <strong>${e.risk_type}</strong>
              <span class="badge ${_(e.severity)}" style="margin-left: 8px;">${e.severity}</span>
            </div>
            <span class="text-muted text-sm">${e.confidence?Math.round(e.confidence*100)+"% confidence":""}</span>
          </div>
          <p style="color: var(--color-text-secondary); margin-bottom: 12px;">${e.description}</p>
          <p style="font-size: 13px; color: var(--color-text-muted);"><strong>Impact:</strong> ${e.impact}</p>
        </div>
      </div>
    `).join("")}renderDisclosureTab(){const{disclosure_issues:t}=this.comparison;return t.length===0?'<div class="empty-state" style="padding: 48px 24px;"><div class="empty-icon">📋</div><p>No disclosure issues identified</p></div>':t.map(e=>`
      <div class="card" style="margin-bottom: 16px; border-left: 4px solid ${e.severity==="critical"?"var(--color-critical)":e.severity==="high"?"var(--color-high)":"var(--color-medium)"};">
        <div class="card-body">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
              <strong>${e.issue_type}</strong>
              <span class="badge ${_(e.severity)}" style="margin-left: 8px;">${e.severity}</span>
            </div>
            <span class="text-muted text-sm">${e.confidence?Math.round(e.confidence*100)+"% confidence":""}</span>
          </div>
          <p style="color: var(--color-text-secondary); margin-bottom: 12px;">${e.description}</p>
          ${e.spa_requirement?`<p style="font-size: 13px; margin-bottom: 8px;"><strong>SPA Requirement:</strong> ${e.spa_requirement}</p>`:""}
          ${e.disclosure_schedule?`<p style="font-size: 13px; margin-bottom: 8px;"><strong>Disclosure Schedule:</strong> ${e.disclosure_schedule}</p>`:""}
          ${e.data_room_evidence?`<p style="font-size: 13px;"><strong>Data Room Evidence:</strong> ${e.data_room_evidence}</p>`:""}
        </div>
      </div>
    `).join("")}renderVerdictTab(){const{verdict:t}=this.comparison;return t?`
      <div style="display: flex; flex-direction: column; gap: 24px;">
        <div class="card">
          <div class="card-header"><div class="card-title">Executive Assessment</div></div>
          <div class="card-body">
            <p style="margin-bottom: 16px; font-size: 15px; line-height: 1.6;">${t.overall_assessment}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 16px;">
              <div><strong>Evidence-Backed Findings:</strong> ${t.evidence_backed_findings}</div>
              <div><strong>Key Asymmetries:</strong> ${t.key_asymmetries}</div>
              <div><strong>Critical Issues:</strong> ${t.critical_issues}</div>
              <div><strong>Confidence:</strong> ${Math.round(t.confidence*100)}%</div>
            </div>
          </div>
        </div>

        <div class="grid grid-2">
          <div class="card">
            <div class="card-header"><div class="card-title">Company A Advantages</div></div>
            <div class="card-body">
              ${t.company_a_advantages.length>0?`
                <ul style="margin-left: 16px;">${t.company_a_advantages.map(e=>`<li style="margin-bottom: 8px;">${e}</li>`).join("")}</ul>
              `:'<p class="text-muted">No advantages identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company A Weaknesses</div></div>
            <div class="card-body">
              ${t.company_a_weaknesses.length>0?`
                <ul style="margin-left: 16px;">${t.company_a_weaknesses.map(e=>`<li style="margin-bottom: 8px; color: var(--color-critical);">${e}</li>`).join("")}</ul>
              `:'<p class="text-muted">No weaknesses identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company B Advantages</div></div>
            <div class="card-body">
              ${t.company_b_advantages.length>0?`
                <ul style="margin-left: 16px;">${t.company_b_advantages.map(e=>`<li style="margin-bottom: 8px;">${e}</li>`).join("")}</ul>
              `:'<p class="text-muted">No advantages identified</p>'}
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title">Company B Weaknesses</div></div>
            <div class="card-body">
              ${t.company_b_weaknesses.length>0?`
                <ul style="margin-left: 16px;">${t.company_b_weaknesses.map(e=>`<li style="margin-bottom: 8px; color: var(--color-critical);">${e}</li>`).join("")}</ul>
              `:'<p class="text-muted">No weaknesses identified</p>'}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Recommended Actions</div></div>
          <div class="card-body">
            ${t.recommended_actions.length>0?`
              <ol style="margin-left: 16px;">${t.recommended_actions.map(e=>`<li style="margin-bottom: 8px;">${e}</li>`).join("")}</ol>
            `:'<p class="text-muted">No specific actions recommended</p>'}
          </div>
        </div>

        <div class="card">
          <div class="card-header"><div class="card-title">Methodology</div></div>
          <div class="card-body">
            <p style="color: var(--color-text-secondary);">${t.score_methodology||"Transparent scoring based on weighted asymmetry categories, cross-document dependencies, and disclosure completeness."}</p>
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
    `:""}formatPosition(t){return t?t.percentage!==void 0?`${t.percentage}%`:t.amount!==void 0?k(t.amount):t.duration?t.duration:"—":"—"}bindEvents(){this.container.querySelectorAll(".tab").forEach(t=>{t.addEventListener("click",e=>{const a=e.currentTarget.getAttribute("data-tab");a&&(this.activeTab=a,this.render(),this.bindEvents())})})}}class V{constructor(t){this.overlay=null,this.app=t}open(){this.render(),this.bindEvents()}render(){var e;const t=this.app.root.querySelector("#modals");this.overlay=document.createElement("div"),this.overlay.className="modal-overlay",this.overlay.innerHTML=`
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
    `,t.appendChild(this.overlay),(e=this.overlay.querySelector("#txn-name"))==null||e.focus()}bindEvents(){var o,r,h,g,f;const t=(o=this.overlay)==null?void 0:o.querySelector("#close-modal"),e=(r=this.overlay)==null?void 0:r.querySelector("#cancel-btn"),a=(h=this.overlay)==null?void 0:h.querySelector("#transaction-form"),n=()=>this.close();t==null||t.addEventListener("click",n),e==null||e.addEventListener("click",n),(g=this.overlay)==null||g.addEventListener("click",u=>{u.target===this.overlay&&n()}),a==null||a.addEventListener("submit",async u=>{var x;u.preventDefault();const c=new FormData(a),w={name:c.get("name"),description:c.get("description")||"",deal_value:c.get("deal_value")?parseFloat(c.get("deal_value")):void 0,company_a_name:c.get("company_a_name"),company_a_role:c.get("company_a_role"),company_a_description:c.get("company_a_description")||"",company_b_name:c.get("company_b_name"),company_b_role:c.get("company_b_role"),company_b_description:c.get("company_b_description")||""},y=(x=this.overlay)==null?void 0:x.querySelector("#submit-btn");y.disabled=!0,y.textContent="Creating...";try{const b=await this.app.api.transactions.create(w);this.close(),await this.app.refreshTransactions(),this.app.setCurrentTransactionId(b.id),this.app.switchView("documents")}catch(b){alert(b.message||"Failed to create transaction")}finally{y.disabled=!1,y.textContent="Create Transaction"}});const s=u=>{u.key==="Escape"&&this.close()};document.addEventListener("keydown",s),(f=this.overlay)==null||f.setAttribute("data-escape-handler","true")}close(){this.overlay&&(this.overlay.remove(),this.overlay=null,document.removeEventListener("keydown",t=>{t.key==="Escape"&&this.close()}))}}class R{constructor(t){this.overlay=null,this.transactions=[],this.app=t}async open(){this.transactions=await p.transactions.list(),this.render(),this.bindEvents()}getModalHtml(){return`
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
                ${this.transactions.map(e=>`<option value="${e.id}">${e.name} (${e.company_a_name} vs ${e.company_b_name})</option>`).join("")}
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
    `}render(){const t=this.app.root.querySelector("#modals");this.overlay=document.createElement("div"),this.overlay.className="modal-overlay",this.overlay.innerHTML=this.getModalHtml(),t.appendChild(this.overlay)}bindEvents(){var g,f,u,c,w,y,x,b;const t=(g=this.overlay)==null?void 0:g.querySelector("#close-modal"),e=(f=this.overlay)==null?void 0:f.querySelector("#cancel-btn"),a=(u=this.overlay)==null?void 0:u.querySelector("#comparison-form"),n=(c=this.overlay)==null?void 0:c.querySelector("#txn-select"),s=(w=this.overlay)==null?void 0:w.querySelector("#run-a-select"),o=(y=this.overlay)==null?void 0:y.querySelector("#run-b-select"),r=(x=this.overlay)==null?void 0:x.querySelector("#submit-btn"),h=()=>this.close();t==null||t.addEventListener("click",h),e==null||e.addEventListener("click",h),(b=this.overlay)==null||b.addEventListener("click",d=>{d.target===this.overlay&&h()}),n==null||n.addEventListener("change",async()=>{const d=n.value;if(s.innerHTML='<option value="">Loading...</option>',o.innerHTML='<option value="">Loading...</option>',s.disabled=!0,o.disabled=!0,r.disabled=!0,!!d)try{const v=await p.transactions.get(n.value),S=v.company_a_id,D=v.company_b_id,$=await this.getCompanyRuns(S),C=await this.getCompanyRuns(D);s.innerHTML='<option value="">Select Company A run</option>'+$.map(m=>`<option value="${m.id}">${m.id.slice(0,8)} - ${m.provisions_extracted} positions - ${new Date(m.started_at).toLocaleDateString()}</option>`).join(""),o.innerHTML='<option value="">Select Company B run</option>'+C.map(m=>`<option value="${m.id}">${m.id.slice(0,8)} - ${m.provisions_extracted} positions - ${new Date(m.started_at).toLocaleDateString()}</option>`).join(""),s.disabled=!1,o.disabled=!1,this.updateSubmitBtn(r,s,o)}catch(v){console.error("Failed to load runs:",v),s.innerHTML='<option value="">Error loading runs</option>',o.innerHTML='<option value="">Error loading runs</option>'}}),s==null||s.addEventListener("change",()=>this.updateSubmitBtn(r,s,o)),o==null||o.addEventListener("change",()=>this.updateSubmitBtn(r,s,o)),a==null||a.addEventListener("submit",async d=>{var $,C,m;d.preventDefault();const v=($=this.overlay)==null?void 0:$.querySelector("#txn-select"),S=(C=this.overlay)==null?void 0:C.querySelector("#run-a-select"),D=(m=this.overlay)==null?void 0:m.querySelector("#run-b-select");r.disabled=!0,r.textContent="Running...";try{const T=await p.comparison.run({transaction_id:v.value,company_a_run_id:S.value,company_b_run_id:D.value});this.close(),await this.app.refreshComparisons(),this.app.goToComparisonDetail(T.id)}catch(T){alert(T.message||"Failed to run comparison")}finally{r.disabled=!1,r.textContent="Run Comparison"}}),document.addEventListener("keydown",d=>{d.key==="Escape"&&this.close()})}updateSubmitBtn(t,e,a){t.disabled=!e.value||!a.value}async getCompanyRuns(t){return await p.analysis.runsForCompany(t)}close(){this.overlay&&(this.overlay.remove(),this.overlay=null)}}class j{constructor(t,e){this.overlay=null,this.app=t,this.transactionId=(e==null?void 0:e.transactionId)||this.app.getCurrentTransactionId()||"",this.companyId=(e==null?void 0:e.companyId)||"",this.role=(e==null?void 0:e.role)||""}async open(){if(!this.transactionId){alert("Please select a transaction first");return}if(!this.companyId){alert("Please select a company");return}this.render(),this.bindEvents()}render(){const t=`
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
    `,e=this.app.root.querySelector("#modals");this.overlay=document.createElement("div"),this.overlay.className="modal-overlay",this.overlay.innerHTML=t,e.appendChild(this.overlay)}bindEvents(){var g,f,u,c,w,y,x,b;const t=(g=this.overlay)==null?void 0:g.querySelector("#close-modal"),e=(f=this.overlay)==null?void 0:f.querySelector("#cancel-btn"),a=(u=this.overlay)==null?void 0:u.querySelector("#upload-form"),n=(c=this.overlay)==null?void 0:c.querySelector("#file-input"),s=(w=this.overlay)==null?void 0:w.querySelector("#upload-zone"),o=(y=this.overlay)==null?void 0:y.querySelector("#file-name"),r=(x=this.overlay)==null?void 0:x.querySelector("#submit-btn"),h=()=>this.close();t==null||t.addEventListener("click",h),e==null||e.addEventListener("click",h),(b=this.overlay)==null||b.addEventListener("click",d=>{d.target===this.overlay&&h()}),s==null||s.addEventListener("dragover",d=>{d.preventDefault(),s.classList.add("drag-active")}),s==null||s.addEventListener("dragleave",()=>{s.classList.remove("drag-active")}),s==null||s.addEventListener("drop",d=>{var v;d.preventDefault(),s.classList.remove("drag-active"),(v=d.dataTransfer)!=null&&v.files.length&&(n.files=d.dataTransfer.files,this.updateFileName(n,o,r))}),s==null||s.addEventListener("click",()=>n.click()),n==null||n.addEventListener("change",()=>this.updateFileName(n,o,r)),a==null||a.addEventListener("submit",async d=>{var S,D,$,C,m;if(d.preventDefault(),!((S=n.files)!=null&&S.length))return;r.disabled=!0,r.textContent="Uploading...";const v=new FormData;v.append("file",n.files[0]),v.append("transaction_id",this.transactionId),v.append("company_id",this.companyId),v.append("role_in_document",((D=this.overlay)==null?void 0:D.querySelector("#role-select")).value),v.append("document_type",(($=this.overlay)==null?void 0:$.querySelector("#doc-type-select")).value);try{const T=await p.documents.upload(n.files[0],{transaction_id:this.transactionId,company_id:this.companyId,role_in_document:((C=this.overlay)==null?void 0:C.querySelector("#role-select")).value,document_type:((m=this.overlay)==null?void 0:m.querySelector("#doc-type-select")).value});r.textContent="Running analysis...",await p.analysis.run(T.document_id),this.close(),this.app.currentView==="documents"&&this.app.renderView("documents")}catch(T){alert(T.message||"Upload failed")}finally{r.disabled=!1,r.textContent="Upload & Analyze"}}),document.addEventListener("keydown",d=>{d.key==="Escape"&&this.close()})}updateFileName(t,e,a){var n;if((n=t.files)!=null&&n.length){const s=t.files[0];e.textContent=`${s.name} (${(s.size/1024/1024).toFixed(1)} MB)`,a.disabled=!1}else e.textContent="",a.disabled=!0}close(){this.overlay&&(this.overlay.remove(),this.overlay=null)}}class F{constructor(t){this.currentView="dashboard",this.currentTransactionId=null,this.currentComparisonId=null,this.transactions=[],this.comparisons=[],this.sidebarOpen=!0,this.root=t}async mount(){this.render(),this.bindEvents(),await this.loadInitialData()}render(){this.root.innerHTML=`
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
    `}bindEvents(){this.root.querySelectorAll(".nav-item").forEach(a=>{a.addEventListener("click",()=>{const n=a.getAttribute("data-view");this.switchView(n)})});const e=this.root.querySelector("#sidebar-toggle");e==null||e.addEventListener("click",()=>this.toggleSidebar())}toggleSidebar(){this.sidebarOpen=!this.sidebarOpen;const t=this.root.querySelector("#sidebar");t.style.transform=this.sidebarOpen?"translateX(0)":"translateX(-100%)"}switchView(t){this.currentView=t,this.currentComparisonId=null,this.root.querySelectorAll(".nav-item").forEach(n=>{n.classList.toggle("active",n.getAttribute("data-view")===t)});const e={dashboard:"Dashboard",transactions:"Transactions",comparisons:"Comparisons",documents:"Data Room","comparison-detail":"Comparison Detail"},a=this.root.querySelector("#page-title");a&&(a.textContent=e[t]),this.renderView(t)}async renderView(t){var n,s,o;const e=this.root.querySelector("#content"),a=this.root.querySelector("#header-actions");switch(t){case"dashboard":a.innerHTML="",e.innerHTML='<div id="dashboard-view"></div>',new I(e.querySelector("#dashboard-view"),this).mount();break;case"transactions":a.innerHTML=`
          <button class="btn btn-primary" id="new-transaction-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Transaction
          </button>
        `,e.innerHTML='<div id="transactions-view"></div>',new H(e.querySelector("#transactions-view"),this).mount(),(n=this.root.querySelector("#new-transaction-btn"))==null||n.addEventListener("click",()=>new V(this).open());break;case"comparisons":a.innerHTML=`
          <button class="btn btn-primary" id="new-comparison-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Comparison
          </button>
        `,e.innerHTML='<div id="comparisons-view"></div>',new B(e.querySelector("#comparisons-view"),this).mount(),(s=this.root.querySelector("#new-comparison-btn"))==null||s.addEventListener("click",()=>new R(this).open());break;case"documents":a.innerHTML=`
          <button class="btn btn-primary" id="upload-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload
          </button>
        `,e.innerHTML='<div id="documents-view"></div>',new P(e.querySelector("#documents-view"),this).mount(),(o=this.root.querySelector("#upload-btn"))==null||o.addEventListener("click",()=>new j(this).open());break;case"comparison-detail":a.innerHTML=`
          <a class="btn btn-secondary" id="export-btn" target="_blank" href="/comparison/${this.currentComparisonId}/export">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export Report
          </a>
        `,e.innerHTML='<div id="comparison-detail-view"></div>',this.currentComparisonId&&new N(e.querySelector("#comparison-detail-view"),this,this.currentComparisonId).mount();break}}async loadInitialData(){try{const[t,e]=await Promise.all([p.transactions.list().catch(()=>[]),p.comparisons.list().catch(()=>[])]);this.transactions=t,this.comparisons=e}catch(t){console.warn("Failed to load initial data:",t)}}getTransactions(){return this.transactions}getComparisons(){return this.comparisons}getCurrentTransactionId(){return this.currentTransactionId}setCurrentTransactionId(t){this.currentTransactionId=t}getCurrentComparisonId(){return this.currentComparisonId}setCurrentComparisonId(t){this.currentComparisonId=t}goToComparisonDetail(t){this.currentComparisonId=t,this.switchView("comparison-detail")}goToDocuments(t){this.currentTransactionId=t,this.switchView("documents")}async refreshTransactions(){this.transactions=await p.transactions.list(),this.currentView==="transactions"&&this.renderView("transactions")}async refreshComparisons(){this.comparisons=await p.comparisons.list(),this.currentView==="comparisons"&&this.renderView("comparisons")}}const A=document.getElementById("app");if(!A)throw new Error("Root element not found");const z=new F(A);z.mount();
