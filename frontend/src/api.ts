export interface RunSummary {
  id: number;
  kind: string;
  params: Record<string, unknown>;
  dry_run: boolean;
  status: string;
  created_at: string;
  finished_at: string | null;
  summary: Record<string, unknown>;
}

export interface RunLog {
  ts: string;
  level: string;
  message: string;
}

export interface RunDetail extends RunSummary {
  logs: RunLog[];
}

export interface Status {
  evolution_configured: boolean;
  evolution_instance: string;
  poll_interval_seconds: number;
  email_accounts: number;
  email_accounts_enabled: number;
  installations: number;
  contacts: number;
  last_run: RunSummary | null;
}

export interface PreviewBill {
  installation: string;
  installation_label: string | null;
  bill_date: string;
  pdf_name: string;
  barcode: string | null;
  amount: string | null;
}

export interface PreviewItem {
  phone: string;
  name: string | null;
  intro: boolean;
  text: string;
  barcode_messages: string[];
  bills: PreviewBill[];
}

export interface Installation {
  code: string;
  label: string | null;
  contacts: number;
}

export interface Contact {
  id: number;
  installation: string;
  phone: string;
  name: string | null;
  installation_label: string | null;
}

export interface EmailAccount {
  id: number;
  label: string;
  host: string;
  username: string;
  enabled: boolean;
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null as T;
  return (await res.json()) as T;
}

export const api = {
  status: () => request<Status>('/api/status'),
  runs: (limit = 20) => request<RunSummary[]>(`/api/runs?limit=${limit}`),
  run: (id: number) => request<RunDetail>(`/api/runs/${id}`),
  startRun: (body: Record<string, unknown>) =>
    request<{ id: number }>('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
  deleteRun: (id: number) => request<null>(`/api/runs/${id}`, { method: 'DELETE' }),

  installations: () => request<Installation[]>('/api/installations'),
  addInstallation: (code: string, label: string | null) =>
    request<unknown>('/api/installations', {
      method: 'POST',
      body: JSON.stringify({ code, label }),
    }),
  deleteInstallation: (code: string) =>
    request<null>(`/api/installations/${code}`, { method: 'DELETE' }),

  contacts: () => request<Contact[]>('/api/contacts'),
  addContact: (installation: string, phone: string, name: string | null) =>
    request<unknown>('/api/contacts', {
      method: 'POST',
      body: JSON.stringify({ installation, phone, name }),
    }),
  updateContact: (id: number, phone: string, name: string | null) =>
    request<Contact>(`/api/contacts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ phone, name }),
    }),
  deleteContact: (id: number) => request<null>(`/api/contacts/${id}`, { method: 'DELETE' }),

  accounts: () => request<EmailAccount[]>('/api/accounts'),
  addAccount: (label: string, host: string, username: string, password: string) =>
    request<unknown>('/api/accounts', {
      method: 'POST',
      body: JSON.stringify({ label, host, username, password }),
    }),
  toggleAccount: (id: number, enabled: boolean) =>
    request<unknown>(`/api/accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    }),
  deleteAccount: (id: number) => request<null>(`/api/accounts/${id}`, { method: 'DELETE' }),
};

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDuration(startIso: string, endIso: string | null): string {
  if (!endIso) return '—';
  const s = Math.max(0, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000));
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

export function kindLabel(run: { kind: string; params: Record<string, unknown> }): string {
  if (run.kind === 'month') return 'Mês inteiro';
  if (run.kind === 'date') return `Data ${String(run.params.date || '')}`;
  return 'Hoje';
}

export function statusLabel(status: string): string {
  if (status === 'done') return 'DONE';
  if (status === 'error') return 'ERROR';
  return 'RUNNING';
}
