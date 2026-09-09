export function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercentage(value: number | undefined): string {
  if (value === undefined || value === null) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatDuration(months: number | undefined): string {
  if (months === undefined || months === null) return '—';
  if (months % 12 === 0) return `${months / 12} year${months > 12 ? 's' : ''}`;
  return `${months} month${months > 1 ? 's' : ''}`;
}

export function formatDate(iso: string | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(iso: string | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getSeverityClass(severity: string): string {
  const map: Record<string, string> = {
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

export function getStatusClass(status: string): string {
  const map: Record<string, string> = {
    healthy: 'status-healthy',
    completed: 'status-healthy',
    processing: 'status-processing',
    running: 'status-processing',
    failed: 'status-failed',
    pending: 'status-pending',
  };
  return map[status?.toLowerCase()] || 'status-pending';
}

export function truncate(text: string | undefined, max = 100): string {
  if (!text) return '—';
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}

export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

export function classNames(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}