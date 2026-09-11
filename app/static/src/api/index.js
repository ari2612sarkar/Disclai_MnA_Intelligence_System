export const API_BASE = '';
export async function apiRequest(endpoint, options = {}) {
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
    if (response.status === 204)
        return undefined;
    return response.json();
}
export const api = {
    health: () => apiRequest('/api/health'),
    companies: {
        list: () => apiRequest('/api/companies'),
        create: (data) => apiRequest('/api/companies', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
        get: (id) => apiRequest(`/api/companies/${id}`),
    },
    transactions: {
        list: () => apiRequest('/api/transactions'),
        create: (data) => apiRequest('/api/transactions', { method: 'POST', body: JSON.stringify(data) }),
        get: (id) => apiRequest(`/api/transactions/${id}`),
    },
    comparisons: {
        list: () => apiRequest('/api/comparisons'),
    },
    documents: {
        upload: (file, data) => {
            const form = new FormData();
            form.append('file', file);
            Object.entries(data).forEach(([k, v]) => form.append(k, v));
            return apiRequest('/documents/upload', {
                method: 'POST',
                headers: {},
                body: form,
            });
        },
        list: (transactionId) => apiRequest(`/documents?transaction_id=${transactionId}`),
        status: (id) => apiRequest(`/analysis/status/${id}`),
    },
    analysis: {
        run: (documentId) => apiRequest('/api/analysis/run', {
            method: 'POST',
            body: JSON.stringify({ document_id: documentId }),
        }),
        get: (runId) => apiRequest(`/api/analysis/${runId}`),
        findings: (runId) => apiRequest(`/api/findings/${runId}`),
    },
    comparison: {
        run: (data) => apiRequest('/api/comparison/run', { method: 'POST', body: JSON.stringify(data) }),
        get: (id) => apiRequest(`/api/comparison/${id}`),
        findings: (id) => apiRequest(`/api/comparison/${id}/findings`),
        verdict: (id) => apiRequest(`/api/comparison/${id}/verdict`),
        export: (id) => fetch(`${API_BASE}/comparison/${id}/export`).then(r => r.text()),
    },
};
