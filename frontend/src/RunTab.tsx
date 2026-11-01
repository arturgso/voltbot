import { useCallback, useEffect, useState } from 'react';
import { Accordion, Badge, Box, Button, Card, Checkbox, Grid, Group, Loader, SegmentedControl, Select, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api, formatDateTime, kindLabel, statusLabel, type RunDetail, type RunSummary, type Status } from './api';
import ConsolePanel, { PreviewPanel } from './ConsolePanel';
import { ConfirmDialog, EmptyState, LoadError } from './ui';

function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}
function monthOptions() {
  const now = new Date();
  return Array.from({ length: 12 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    return {
      value: i === 0 ? 'atual' : `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`,
      label: i === 0 ? 'Mês atual' : d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }),
    };
  });
}
export function runColor(status: string): string {
  return status === 'done' ? 'forest' : status === 'error' ? 'red' : 'blue';
}

function ScheduleCountdown({ status }: { status: Status | null }) {
  const [remaining, setRemaining] = useState<number | null>(null);
  const schedule = status?.schedule;
  useEffect(() => {
    if (!schedule) { setRemaining(null); return; }
    const initial = new Date(schedule.next_run_at).getTime() - new Date(schedule.server_time).getTime();
    const started = performance.now();
    const tick = () => setRemaining(Math.max(0, Math.ceil((initial - (performance.now() - started)) / 1000)));
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [schedule]);
  const days = Math.floor((remaining ?? 0) / 86400);
  const clock = [Math.floor((remaining ?? 0) % 86400 / 3600), Math.floor((remaining ?? 0) % 3600 / 60), (remaining ?? 0) % 60].map(n => String(n).padStart(2, '0')).join(':');
  return <div className="schedule-countdown">
    <Group justify="space-between" gap="xs"><Text size="xs" fw={600}>Agendamento semanal</Text><Badge color={schedule?.active ? 'blue' : 'gray'} size="sm">{schedule ? schedule.active ? 'Ativo' : 'Inativo' : 'Consultando'}</Badge></Group>
    <div className="countdown-value" aria-label="Tempo até a próxima execução">{remaining == null ? '—' : !schedule?.active ? 'Indisponível' : remaining === 0 ? 'Aguardando execução' : `${days}d ${clock}`}</div>
    <Text size="xs" c="dimmed">{schedule ? `Próxima: ${formatDateTime(schedule.next_run_at)}` : 'Aguardando informações do servidor.'}</Text>
    <Text size="xs" c="dimmed" mt={6}>Busca a semana anterior e o dia atual. Executar manualmente não altera o agendamento.</Text>
  </div>;
}

export default function RunTab({ status, refreshStatus }: { status: Status | null; refreshStatus: () => Promise<void> }) {
  const [mode, setMode] = useState('month');
  const [date, setDate] = useState('');
  const [month, setMonth] = useState('atual');
  const [dryRun, setDryRun] = useState(false);
  const [barcodeOnly, setBarcodeOnly] = useState(false);
  const [barcodeAll, setBarcodeAll] = useState(false);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [detailError, setDetailError] = useState(false);
  const [retryDetail, setRetryDetail] = useState(0);
  const [busy, setBusy] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const refreshRuns = useCallback(async () => {
    try {
      const next = await api.runs();
      setRuns(next);
      setSelectedId(current => current ?? next[0]?.id ?? null);
      setRunsError(false);
    }
    catch { setRunsError(true); }
    finally { setRunsLoading(false); }
  }, []);
  useEffect(() => { refreshRuns(); }, [refreshRuns, status?.last_run?.id]);

  useEffect(() => {
    setDetail(null);
    setDetailError(false);
    if (selectedId == null) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const next = await api.run(selectedId);
        if (stopped) return;
        setDetail(next);
        setDetailError(false);
        if (next.status === 'running') timer = setTimeout(load, 2000);
        else { refreshRuns(); refreshStatus(); }
      } catch {
        if (!stopped) { setDetailError(true); timer = setTimeout(load, 4000); }
      }
    };
    load();
    return () => { stopped = true; clearTimeout(timer); };
  }, [selectedId, retryDetail, refreshRuns, refreshStatus]);

  // Keep the history current even when another execution is selected.
  useEffect(() => {
    if (!runs.some(run => run.status === 'running')) return;
    const timer = setInterval(refreshRuns, 4000);
    return () => clearInterval(timer);
  }, [runs, refreshRuns]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const body: Record<string, unknown> = { mode, dry_run: dryRun, barcode_only: barcodeOnly, barcode_all: barcodeOnly && barcodeAll };
    if (mode === 'date') body.date = date;
    if (mode === 'month') body.month = month === 'atual' ? currentYearMonth() : month;
    setBusy(true);
    try {
      const run = await api.startRun(body);
      setSelectedId(run.id);
      refreshRuns();
      notifications.show({ title: dryRun ? 'Simulação iniciada' : 'Execução iniciada', message: `Acompanhe a execução #${run.id} ao lado.` });
    } catch (err) { notifications.show({ color: 'red', title: 'Falha ao iniciar', message: String(err) }); }
    finally { setBusy(false); }
  };
  const clearHistory = async () => {
    // The endpoint returns at most 20 recent runs. Only delete the displayed snapshot.
    const results = await Promise.allSettled(runs.map(run => api.deleteRun(run.id)));
    const deletedSelected = runs.some((run, i) => run.id === selectedId && results[i].status === 'fulfilled');
    if (deletedSelected) { setSelectedId(null); setDetail(null); }
    await Promise.all([refreshRuns(), refreshStatus()]);
    if (results.some(result => result.status === 'rejected')) throw new Error('Algumas execuções não puderam ser excluídas. Confira o histórico atualizado e tente novamente.');
  };

  return (
    <Box>
      <Grid gutter="xl" align="flex-start">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card className="execution-panel">
            <div className="section-heading"><h2>Nova execução</h2><Text size="sm" c="dimmed" mt={5}>Buscar faturas e enviar aos contatos.</Text></div>
            <form onSubmit={submit}>
              <Stack gap="lg">
                <Box><Text size="sm" fw={550} mb={8}>Período</Text><SegmentedControl className="segmented-period" fullWidth value={mode} onChange={setMode} aria-label="Período da execução" data={[{ value: 'today', label: 'Hoje' }, { value: 'date', label: 'Uma data' }, { value: 'month', label: 'Mês inteiro' }]} /></Box>
                {mode === 'date' && <TextInput label="Data de referência" type="date" value={date} onChange={e => setDate(e.target.value)} required />}
                {mode === 'month' && <Select label="Mês de referência" value={month} onChange={v => setMonth(v || 'atual')} data={monthOptions()} allowDeselect={false} />}
                <Box className="soft-panel"><Checkbox label="Simular envio" description="Consulta os e-mails e mostra uma prévia, sem enviar mensagens. PDFs podem ser salvos." checked={dryRun} onChange={e => setDryRun(e.target.checked)} /></Box>
                <Accordion variant="default">
                  <Accordion.Item value="advanced"><Accordion.Control>Opções avançadas</Accordion.Control><Accordion.Panel><Stack gap="md">
                    <Checkbox label="Somente código de barras" description="Reenvia o código para quem já recebeu a fatura no período." checked={barcodeOnly} onChange={e => { setBarcodeOnly(e.target.checked); if (!e.target.checked) setBarcodeAll(false); }} />
                    {barcodeOnly && <Checkbox label="Incluir faturas ainda não enviadas" checked={barcodeAll} onChange={e => setBarcodeAll(e.target.checked)} />}
                  </Stack></Accordion.Panel></Accordion.Item>
                </Accordion>
                <Button type="submit" fullWidth size="md" loading={busy}>{dryRun ? 'Simular' : 'Executar'}</Button>
                <ScheduleCountdown status={status} />
              </Stack>
            </form>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card className="result-panel">
            <div className="section-heading"><h2>Acompanhamento</h2><Text size="sm" c="dimmed" mt={5}>Consulte o resultado e confira as mensagens.</Text></div>
            {detailError && <LoadError retry={() => setRetryDetail(v => v + 1)} />}
            {selectedId == null ? <EmptyState title="Nenhuma execução selecionada" description="Inicie uma execução ou selecione um item do histórico para acompanhar os resultados." /> : !detail ? !detailError && <Group justify="center" py="xl"><Loader size="sm" /><Text size="sm" c="dimmed">Carregando execução…</Text></Group> : <>
              <Group justify="space-between"><Box><Text fw={650}>Execução #{detail.id}</Text><Text size="xs" c="dimmed">{kindLabel(detail)} · {formatDateTime(detail.created_at)}</Text></Box><Group gap="xs"><Badge color={runColor(detail.status)}>{statusLabel(detail.status)}</Badge>{detail.dry_run && <Badge color="gray">Simulação</Badge>}</Group></Group>
              <ConsolePanel run={detail} />
              <PreviewPanel key={detail.id} run={detail} />
            </>}
          </Card>
        </Grid.Col>
      </Grid>
      <Card mt="xl" className="history-panel">
        <Group justify="space-between" className="section-heading"><div><h2>Execuções recentes</h2><Text size="sm" c="dimmed" mt={5}>Selecione uma execução para ver os detalhes.</Text></div><Button variant="subtle" color="gray" size="xs" disabled={!runs.length || runsLoading || runsError || runs.some(r => r.status === 'running')} onClick={() => setConfirmClear(true)}>Limpar recentes</Button></Group>
        {runsError && <LoadError retry={refreshRuns} />}
        {runsLoading ? <Group justify="center" py="lg"><Loader size="sm" /><Text size="sm" c="dimmed">Carregando histórico…</Text></Group> : !runsError && runs.length === 0 ? <EmptyState title="Nenhuma execução registrada" description="As execuções e simulações aparecerão nesta lista." /> : runs.map(r => <button type="button" className="run-row" key={r.id} aria-pressed={r.id === selectedId} onClick={() => setSelectedId(r.id)}><span className="row-content"><Text component="span" size="sm" fw={600}>#{r.id} · {kindLabel(r)}</Text><Text component="span" display="block" size="xs" c="dimmed" mt={4}>{formatDateTime(r.created_at)}</Text></span><Group gap="xs" component="span">{r.dry_run && <Badge color="gray">Simulação</Badge>}<Badge color={runColor(r.status)}>{statusLabel(r.status)}</Badge><span aria-hidden="true">↗</span></Group></button>)}
      </Card>
      {confirmClear && <ConfirmDialog title="Limpar execuções recentes?" description={`Isso exclui as ${runs.length} execuções exibidas e seus logs. Execuções mais antigas podem aparecer depois da limpeza. O controle de faturas já enviadas será preservado.`} onClose={() => setConfirmClear(false)} onConfirm={clearHistory} />}
    </Box>
  );
}
