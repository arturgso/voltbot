import { useEffect, useRef } from 'react';
import { Badge, Box, Button, Card, Divider, Group, Text } from '@mantine/core';
import { formatDuration, type PreviewItem, type RunDetail } from './api';

export default function ConsolePanel({ run }: { run: RunDetail | null }) {
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [run?.logs.length, run?.id]);

  const copyLog = async () => {
    if (!run) return;
    const text = run.logs.map((l) => `[${l.ts}] ${l.message}`).join('\n');
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  };

  const summary = (run?.summary || {}) as {
    deliveries?: number;
    messages?: number;
  };

  return (
    <Box
      style={{
        background: '#0d1117',
        color: '#e6edf3',
        borderRadius: 4,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 420,
      }}
    >
      <Group justify="space-between" px="md" py="xs">
        <Group gap="xs">
          <Box
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: run?.status === 'error' ? '#fa5252' : '#40c057',
            }}
          />
          <Text size="xs" ff="monospace" c="dimmed" tt="uppercase">
            Console logs{run ? ` — #${run.id} ${run.kind}` : ''}
          </Text>
        </Group>
        <Button size="xs" variant="outline" color="gray" onClick={copyLog} disabled={!run}>
          COPIAR LOG
        </Button>
      </Group>
      <Divider color="#21262d" />
      <Box
        ref={bodyRef}
        px="md"
        py="sm"
        ff="monospace"
        fz="xs"
        style={{ flex: 1, overflowY: 'auto', maxHeight: 420, whiteSpace: 'pre-wrap' }}
      >
        {!run && <Text c="dimmed">Selecione uma execução.</Text>}
        {run?.logs.map((l, i) => (
          <div key={i} style={{ color: l.level === 'ERROR' ? '#ff8787' : '#c9d1d9' }}>
            [{l.ts}] {l.message}
          </div>
        ))}
      </Box>
      <Divider color="#21262d" />
      <Group gap="xl" px="md" py="sm">
        <Box>
          <Text size="xs" c="dimmed" tt="uppercase">
            Contas
          </Text>
          <Text size="sm" fw={600}>
            {run ? String(summary.deliveries ?? '—') : '—'}
          </Text>
        </Box>
        <Box>
          <Text size="xs" c="dimmed" tt="uppercase">
            Mensagens
          </Text>
          <Text size="sm" fw={600}>
            {run ? String(summary.messages ?? '—') : '—'}
          </Text>
        </Box>
        <Box>
          <Text size="xs" c="dimmed" tt="uppercase">
            Tempo
          </Text>
          <Text size="sm" fw={600}>
            {run ? formatDuration(run.created_at, run.finished_at) : '—'}
          </Text>
        </Box>
        {run?.dry_run && (
          <Badge color="yellow" variant="light">
            DRY-RUN
          </Badge>
        )}
      </Group>
    </Box>
  );
}

export function PreviewPanel({ run }: { run: RunDetail | null }) {
  const summary = (run?.summary || {}) as { preview?: PreviewItem[] };
  const preview = summary.preview || [];
  if (!run || preview.length === 0) return null;

  const copyBarcode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  };

  return (
    <Box mt="md">
      {preview.map((item, i) => (
        <Card key={i} withBorder padding="md" mb="sm">
          <Group justify="space-between" mb="xs">
            <Text size="sm" fw={700}>
              {item.name || item.phone} — {item.phone}
            </Text>
            {item.intro && (
              <Badge color="blue" variant="light">
                INTRO
              </Badge>
            )}
          </Group>
          <Text size="xs" ff="monospace" style={{ whiteSpace: 'pre-wrap' }} mb="sm">
            {item.text}
          </Text>
          {item.bills.map((bill, j) => (
            <Box
              key={j}
              py="xs"
              style={{ borderTop: '1px solid #e9ecef' }}
            >
              <Text size="xs" c="dimmed">
                Instalação {bill.installation}
                {bill.installation_label ? ` (${bill.installation_label})` : ''} — {bill.bill_date} —{' '}
                {bill.pdf_name}
              </Text>
              {bill.barcode ? (
                <Group gap="xs" mt={4}>
                  <Text size="xs" ff="monospace" style={{ wordBreak: 'break-all' }}>
                    {bill.barcode}
                  </Text>
                  <Button size="xs" variant="light" onClick={() => copyBarcode(bill.barcode!)}>
                    COPIAR CÓDIGO
                  </Button>
                </Group>
              ) : (
                <Text size="xs" c="red">
                  Código de barras não encontrado no e-mail
                </Text>
              )}
            </Box>
          ))}
        </Card>
      ))}
    </Box>
  );
}
