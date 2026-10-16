import { useState } from 'react';
import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import type { ReactNode } from 'react';

export function PageHeading({ title, description }: { title: string; description: string }) {
  return <div className="page-heading"><h1>{title}</h1><Text c="dimmed" size="sm">{description}</Text></div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><Text fw={600} c="var(--ink)" mb={6}>{title}</Text><Text size="sm" mb={action ? 'md' : 0}>{description}</Text>{action}</div>;
}

export function LoadError({ retry }: { retry: () => void }) {
  return <Alert color="red" title="Não foi possível carregar os dados" mb="md"><Text size="sm" mb="xs">Tente novamente para atualizar esta seção.</Text><Button color="red" variant="light" size="xs" onClick={retry}>Tentar novamente</Button></Alert>;
}

export function ConfirmDialog({ title, description, onConfirm, onClose }: { title: string; description: string; onConfirm: () => Promise<void>; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    setBusy(true);
    try { await onConfirm(); onClose(); }
    catch (error) { notifications.show({ color: 'red', title: 'Não foi possível concluir', message: String(error) }); }
    finally { setBusy(false); }
  };
  return <Modal opened onClose={() => { if (!busy) onClose(); }} title={title} closeOnEscape={!busy} closeOnClickOutside={!busy} withCloseButton={!busy}>
    <Stack><Text size="sm" c="dimmed">{description}</Text><Group justify="flex-end"><Button variant="default" onClick={onClose} disabled={busy}>Cancelar</Button><Button color="red" onClick={confirm} loading={busy}>Confirmar exclusão</Button></Group></Stack>
  </Modal>;
}

export function success(message: string) { notifications.show({ title: 'Tudo certo', message }); }
export function failure(error: unknown) { notifications.show({ color: 'red', title: 'Não foi possível salvar', message: String(error) }); }
