import { useEffect, useRef, useState } from 'react';
import { Accordion, Badge, Box, Button, Card, Group, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { formatDuration, type PreviewItem, type RunDetail } from './api';

async function copyText(text: string) {
  try {
    if (navigator.clipboard) await navigator.clipboard.writeText(text);
    else {
      const input = document.createElement('textarea');
      input.value = text;
      input.style.position = 'fixed';
      input.style.opacity = '0';
      document.body.appendChild(input);
      try { input.select(); if (!document.execCommand('copy')) throw new Error('Falha ao copiar'); }
      finally { input.remove(); }
    }
    notifications.show({ message: 'Copiado para a área de transferência.' });
  } catch { notifications.show({ color: 'red', title: 'Não foi possível copiar', message: 'Selecione o texto e copie manualmente.' }); }
}

export default function ConsolePanel({ run }: { run: RunDetail }) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  useEffect(() => {
    const el = bodyRef.current;
    if (el && expanded) el.scrollTop = el.scrollHeight;
  }, [run.logs.length, run.id, expanded]);
  const summary = run.summary as { deliveries?: number; messages?: number };
  return <>
    <div className="run-stats" aria-live="polite">
      {[['Faturas', summary.deliveries ?? '—'], [run.dry_run ? 'Mensagens previstas' : 'Mensagens', summary.messages ?? '—'], ['Duração', formatDuration(run.created_at, run.finished_at)]].map(([label, value]) => <div className="run-stat" key={label}><Text size="xs" c="dimmed">{label}</Text><Text fw={650} size="xl" mt={6}>{value}</Text></div>)}
    </div>
    <Text size="sm" c="dimmed" mb="lg">{run.status === 'running' ? 'Buscando faturas e processando os resultados. Esta seção se atualiza automaticamente.' : run.status === 'error' ? 'A execução encontrou um problema. Consulte os logs para entender o que aconteceu.' : run.dry_run ? 'Simulação concluída. Nenhuma mensagem foi enviada.' : 'Execução concluída. Confira os detalhes nos logs.'}</Text>
    <Accordion variant="default" value={expanded} onChange={setExpanded}>
      <Accordion.Item value="logs"><Accordion.Control>Logs da execução <Text component="span" size="xs" c="dimmed">· {run.logs.length} registros</Text></Accordion.Control><Accordion.Panel>
        <Group justify="space-between" mb="sm"><Text size="xs" c="dimmed">Detalhes do processamento</Text><Button size="xs" variant="light" disabled={!run.logs.length} onClick={() => copyText(run.logs.map(l => `[${l.ts}] ${l.message}`).join('\n'))}>Copiar logs</Button></Group>
        <Box className="log-body" ref={bodyRef} tabIndex={0} aria-label="Registros da execução">
          {run.logs.length === 0 && 'Aguardando registros…'}
          {run.logs.map((l, i) => <div key={i} style={{ color: l.level === 'ERROR' ? '#a12e2e' : undefined }}>[{l.ts}] {l.message}</div>)}
        </Box>
      </Accordion.Panel></Accordion.Item>
    </Accordion>
  </>;
}

export function PreviewPanel({ run }: { run: RunDetail | null }) {
  const preview = (run?.summary as { preview?: PreviewItem[] } | undefined)?.preview || [];
  if (!run || !preview.length) return null;
  return <Box mt="lg">
    <Text component="h3" size="sm" fw={650} mb="md">Prévia por destinatário</Text>
    {preview.map((item, i) => <Card key={i} padding="md" mb="sm">
      <Group justify="space-between" mb="md"><Box className="row-content"><Text size="sm" fw={600}>{item.name || 'Destinatário'}</Text><Text size="xs" c="dimmed">{item.phone}</Text></Box>{item.intro && <Badge>Com apresentação</Badge>}</Group>
      {item.text && <div className="preview-text">{item.text}</div>}
      {(item.barcode_messages || []).map((code, k) => <Box className="soft-panel" key={k} mt="md"><Text size="xs" c="dimmed" mb={8}>Código de barras · mensagem separada</Text><Text size="xs" ff="monospace" style={{ overflowWrap: 'anywhere' }}>{code}</Text><Button size="xs" variant="light" mt="xs" onClick={() => copyText(code)}>Copiar código</Button></Box>)}
      {item.bills.map((bill, j) => <Box key={j} className="data-row" mt="sm">
        <Text size="sm" fw={550}>{bill.installation_label || 'Instalação'} · {bill.installation}</Text>
        <Text size="xs" c="dimmed" style={{ overflowWrap: 'anywhere' }}>{bill.bill_date} · {bill.pdf_name}{bill.amount ? ` · R$ ${bill.amount}` : ''}</Text>
        {!bill.barcode && <Text size="xs" c="orange" mt={4}>Código de barras não encontrado no e-mail</Text>}
      </Box>)}
    </Card>)}
  </Box>;
}
