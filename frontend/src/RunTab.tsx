import { useCallback, useEffect, useState } from 'react';
import {
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  api,
  formatDateTime,
  kindLabel,
  statusLabel,
  type RunDetail,
  type RunSummary,
  type Status,
} from './api';
import ConsolePanel, { PreviewPanel } from './ConsolePanel';

function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function monthOptions(): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [];
  const now = new Date();
  const currentLabel = now.toLocaleDateString('pt-BR', { month: '2-digit', year: 'numeric' });
  options.push({ value: 'atual', label: `Atual (${currentLabel})` });
  for (let i = 1; i <= 11; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
    options.push({ value, label });
  }
  return options;
}

function statusColor(status: string): string {
  if (status === 'done') return 'green';
  if (status === 'error') return 'red';
  return 'blue';
}

function formatCountdown(targetMs: number, nowMs: number): string {
  const total = Math.max(0, Math.floor((targetMs - nowMs) / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

export default function RunTab({
  status,
  refreshStatus,
}: {
  status: Status | null;
  refreshStatus: () => Promise<void>;
}) {
  const [mode, setMode] = useState<string>('month');
  const [date, setDate] = useState('');
  const [month, setMonth] = useState('atual');
  const [dryRun, setDryRun] = useState(false);
  const [barcodeOnly, setBarcodeOnly] = useState(false);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const refreshRuns = useCallback(async () => {
    try {
      setRuns(await api.runs());
    } catch (e) {
      notifications.show({ color: 'red', title: 'Falha', message: String(e) });
    }
  }, []);

  const refreshDetail = useCallback(async (id: number) => {
    try {
      return await api.run(id);
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  useEffect(() => {
    if (selectedId == null) {
      setDetail(null);
      return;
    }
    let stop = false;
    const load = async () => {
      const d = await refreshDetail(selectedId);
      if (!stop && d) {
        setDetail(d);
        if (d.status !== 'running') {
          refreshRuns();
          refreshStatus();
        }
      }
    };
    load();
    const t = setInterval(async () => {
      const d = await refreshDetail(selectedId);
      if (stop || !d) return;
      setDetail(d);
      if (d.status !== 'running') {
        clearInterval(t);
        refreshRuns();
        refreshStatus();
      }
    }, 2000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [selectedId, refreshDetail, refreshRuns, refreshStatus]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const body: Record<string, unknown> = { mode, dry_run: dryRun, barcode_only: barcodeOnly };
    if (mode === 'date') body.date = date;
    if (mode === 'month') body.month = month === 'atual' ? currentYearMonth() : month;
    setBusy(true);
    try {
      const run = await api.startRun(body);
      setSelectedId(run.id);
      refreshRuns();
      notifications.show({ color: 'green', title: 'Execução iniciada', message: `#${run.id}` });
    } catch (err) {
      notifications.show({ color: 'red', title: 'Falha ao iniciar', message: String(err) });
    } finally {
      setBusy(false);
    }
  };

  const clearAll = async () => {
    if (!confirm('Apagar todo o histórico de execuções?')) return;
    for (const r of runs) {
      try {
        await api.deleteRun(r.id);
      } catch {
        /* segue */
      }
    }
    setSelectedId(null);
    refreshRuns();
    refreshStatus();
  };

  const last = status?.last_run;
  const minutes = status ? Math.round(status.poll_interval_seconds / 60) : 60;
  const nextIn = (() => {
    if (!status?.last_run) return null;
    const base = status.last_run.finished_at || status.last_run.created_at;
    return new Date(base).getTime() + status.poll_interval_seconds * 1000;
  })();

  return (
    <Box>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }} mb="md">
        <Card withBorder padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Contas ativas
          </Text>
          <Text size="xl" fw={700}>
            {status?.email_accounts_enabled ?? '—'}
          </Text>
        </Card>
        <Card withBorder padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Instalações
          </Text>
          <Text size="xl" fw={700}>
            {status?.installations ?? '—'}
          </Text>
        </Card>
        <Card withBorder padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Contatos
          </Text>
          <Text size="xl" fw={700}>
            {status?.contacts ?? '—'}
          </Text>
        </Card>
        <Card withBorder padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Última execução
          </Text>
          <Text size="xl" fw={700} c={last ? 'indigo' : undefined}>
            {last ? `#${last.id} ${last.status === 'done' ? 'CONCLUÍDA' : last.status.toUpperCase()}` : '—'}
          </Text>
        </Card>
        <Card withBorder padding="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
            Próximo disparo
          </Text>
          <Text size="xl" fw={700} c={nextIn ? 'green' : undefined}>
            {nextIn ? formatCountdown(nextIn, nowMs) : '—'}
          </Text>
        </Card>
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder padding="lg" mb="md">
            <Text size="sm" fw={700} tt="uppercase" mb="md">
              Executar agora
            </Text>
            <form onSubmit={submit}>
              <Stack gap="sm">
                <Select
                  label="MODO DE OPERAÇÃO"
                  value={mode}
                  onChange={(v) => setMode(v || 'today')}
                  data={[
                    { value: 'today', label: 'Hoje' },
                    { value: 'date', label: 'Data específica' },
                    { value: 'month', label: 'Mês inteiro' },
                  ]}
                />
                {mode === 'date' && (
                  <TextInput
                    label="DATA DE REFERÊNCIA"
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                  />
                )}
                {mode === 'month' && (
                  <Select
                    label="MÊS DE REFERÊNCIA"
                    value={month}
                    onChange={(v) => setMonth(v || 'atual')}
                    data={monthOptions()}
                  />
                )}
                <Checkbox
                  label="Modo dry-run (só prever, sem enviar)"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                />
                <Checkbox
                  label="Somente código de barras (reenvio p/ quem já recebeu no período)"
                  checked={barcodeOnly}
                  onChange={(e) => setBarcodeOnly(e.target.checked)}
                />
                <Button type="submit" fullWidth loading={busy}>
                  EXECUTAR AUTOMAÇÃO
                </Button>
                <Text size="xs" c="dimmed">
                  Agendamento automático ativo: a cada {minutes} minutos (POLL_INTERVAL_SECONDS).
                </Text>
              </Stack>
            </form>
          </Card>

          <Card withBorder padding="lg">
            <Group justify="space-between" mb="sm">
              <Text size="sm" fw={700} tt="uppercase">
                Execuções recentes
              </Text>
              <Anchor size="xs" tt="uppercase" onClick={clearAll} style={{ cursor: 'pointer' }}>
                Limpar
              </Anchor>
            </Group>
            <Stack gap={0}>
              {runs.map((r) => (
                <Box
                  key={r.id}
                  py="sm"
                  onClick={() => setSelectedId(r.id)}
                  style={{
                    cursor: 'pointer',
                    borderTop: '1px solid #e9ecef',
                    background: r.id === selectedId ? '#f1f3f5' : undefined,
                  }}
                >
                  <Group justify="space-between">
                    <Box>
                      <Text size="sm" fw={600}>
                        #{r.id} {kindLabel(r)}
                        {r.dry_run ? ' (dry-run)' : ''}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {formatDateTime(r.created_at)}
                      </Text>
                    </Box>
                    <Badge color={statusColor(r.status)} variant="light">
                      {statusLabel(r.status)}
                    </Badge>
                  </Group>
                </Box>
              ))}
              {runs.length === 0 && (
                <Text size="sm" c="dimmed">
                  Nenhuma execução ainda.
                </Text>
              )}
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 7 }}>
          <ConsolePanel run={detail} />
          <PreviewPanel run={detail} />
        </Grid.Col>
      </Grid>
    </Box>
  );
}
