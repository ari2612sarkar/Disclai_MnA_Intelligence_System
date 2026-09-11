export const API_BASE = '';

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export interface Transaction {
  id: string;
  name: string;
  company_a_name: string;
  company_b_name: string;
  deal_value?: number;
  status: string;
  created_at: string;
}

export interface Comparison {
  id: string;
  transaction_name: string;
  company_a_name: string;
  company_b_name: string;
  matched_provisions: number;
  findings_count: number;
  material_asymmetries_count: number;
  cross_document_risks_count: number;
  disclosure_issues_count: number;
  status: string;
}

export const api = {
  health: () => apiRequest<{ status: string; service: string }>('/api/health'),

  companies: {
    list: () => apiRequest<Array<{ id: string; name: string; role: string }>>('/api/companies'),
    create: (data: { name: string; role: string; description?: string }) =>
      apiRequest<{ id: string; name: string; role: string }>('/api/companies', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => apiRequest<{ id: string; name: string; role: string }>(`/api/companies/${id}`),
  },

  transactions: {
    list: () => apiRequest<Transaction[]>('/api/transactions'),
    create: (data: {
      name: string;
      company_a_id: string;
      company_b_id: string;
      company_a_role: string;
      company_b_role: string;
      deal_value?: number;
    }) => apiRequest<{ id: string }>('/api/transactions', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => apiRequest<any>(`/api/transactions/${id}`),
  },

  comparisons: {
    list: () => apiRequest<Comparison[]>('/api/comparisons'),
  },

  documents: {
    upload: (file: File, data: { transaction_id: string; company_id: string; role_in_document: string; document_type: string }) => {
      const form = new FormData();
      form.append('file', file);
      Object.entries(data).forEach(([k, v]) => form.append(k, v));
      return apiRequest<{ document_id: string; filename: string }>('/documents/upload', {
        method: 'POST',
        headers: {},
        body: form,
      });
    },
    list: (transactionId: string) => apiRequest<any>(`/api/documents?transaction_id=${transactionId}`),
    status: (id: string) => apiRequest<{ status: string; run_id?: string; positions_extracted?: number }>(`/analysis/status/${id}`),
  },

  analysis: {
    run: (documentId: string) => apiRequest<{ run_id: string }>('/api/analysis/run', {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    }),
    get: (runId: string) => apiRequest<any>(`/analysis/${runId}`),
    findings: (runId: string) => apiRequest<any>(`/api/findings/${runId}`),
    runsForCompany: (companyId: string) => apiRequest<any[]>(`/api/analysis/runs/company/${companyId}`),
  },

  comparison: {
    run: (data: { transaction_id: string; company_a_run_id: string; company_b_run_id: string }) =>
      apiRequest<{ id: string }>('/api/comparison/run', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => apiRequest<any>(`/api/comparison/${id}`),
    findings: (id: string) => apiRequest<any>(`/api/comparison/${id}/findings`),
    verdict: (id: string) => apiRequest<any>(`/api/comparison/${id}/verdict`),
    export: (id: string) => fetch(`${API_BASE}/comparison/${id}/export`).then(r => r.text()),
  },
};