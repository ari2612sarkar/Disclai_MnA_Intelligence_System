export function formatCurrency(value) {
    if (value === undefined || value === null)
        return '—';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
}
export function formatPercentage(value) {
    if (value === undefined || value === null)
        return '—';
    return `${value.toFixed(1)}%`;
}
export function formatDuration(months) {
    if (months === undefined || months === null)
        return '—';
    if (months % 12 === 0)
        return `${months / 12} year${months > 12 ? 's' : ''}`;
    return `${months} month${months > 1 ? 's' : ''}`;
}
export function formatDate(iso) {
    if (!iso)
        return '—';
    return new Date(iso).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}
export function formatDateTime(iso) {
    if (!iso)
        return '—';
    return new Date(iso).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
export function getSeverityClass(severity) {
    const map = {
        critical: 'badge-critical',
        high: 'badge-high',
        medium: 'badge-medium',
        low: 'badge-low',
        info: 'badge-info',
        potential_asymmetry: 'badge-potential',
        material_asymmetry: 'badge-material',
        presence_absence: 'badge-presence',
        conflict: 'badge-conflict',
        requires_review: 'badge-review',
        no_material_difference: 'badge-review',
        matched: 'badge-matched',
        unmatched: 'badge-unmatched',
        partial: 'badge-partial',
    };
    return map[severity?.toLowerCase()] || 'badge-info';
}
export function getStatusClass(status) {
    const map = {
        healthy: 'status-healthy',
        completed: 'status-healthy',
        processing: 'status-processing',
        running: 'status-processing',
        failed: 'status-failed',
        pending: 'status-pending',
    };
    return map[status?.toLowerCase()] || 'status-pending';
}
export function truncate(text, max = 100) {
    if (!text)
        return '—';
    if (text.length <= max)
        return text;
    return text.slice(0, max - 1) + '…';
}
export function debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
}
export function classNames(...classes) {
    return classes.filter(Boolean).join(' ');
}
