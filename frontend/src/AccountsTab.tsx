import { useCallback, useEffect, useState } from 'react';
import { Badge, Box, Button, Card, Group, Loader, Modal, PasswordInput, Stack, Text, TextInput } from '@mantine/core';
import { api, type EmailAccount } from './api';
import { ConfirmDialog, EmptyState, failure, LoadError, success } from './ui';

export default function AccountsTab({ refreshStatus }: { refreshStatus: () => Promise<void> }) {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [label, setLabel] = useState('');
  const [host, setHost] = useState('imap.gmail.com');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [opened, setOpened] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<EmailAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const refresh = useCallback(async () => {
    try { setAccounts(await api.accounts()); setError(false); }
    catch { setError(true); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.addAccount(label, host || 'imap.gmail.com', username, password);
      setLabel(''); setHost('imap.gmail.com'); setUsername(''); setPassword('');
      setOpened(false);
      success('Conta de e-mail adicionada.');
      await Promise.all([refresh(), refreshStatus()]);
    } catch (err) { failure(err); }
    finally { setSaving(false); }
  };
  const toggle = async (account: EmailAccount) => {
    setPending(account.id);
    try { await api.toggleAccount(account.id, !account.enabled); success(account.enabled ? 'Conta pausada.' : 'Conta ativada.'); await Promise.all([refresh(), refreshStatus()]); }
    catch (err) { failure(err); }
    finally { setPending(null); }
  };

  return <Box>
    <Card>
      <Group justify="space-between" className="section-heading"><div><h2>Contas de e-mail</h2><Text size="sm" c="dimmed" mt={5}>Ative apenas as contas que deseja consultar.</Text></div><Button onClick={() => setOpened(true)}>Adicionar conta</Button></Group>
      {error && <LoadError retry={refresh} />}
      {loading ? <Group justify="center" py="xl"><Loader size="sm" /><Text size="sm" c="dimmed">Carregando contas…</Text></Group> : !error && accounts.length === 0 ? <EmptyState title="Conecte seu primeiro e-mail" description="Adicione a conta que recebe suas faturas da Enel." action={<Button variant="light" onClick={() => setOpened(true)}>Adicionar conta</Button>} /> : accounts.map(a => <Group className="data-row" key={a.id} justify="space-between">
        <Box className="row-content"><Text size="sm" fw={600}>{a.label}</Text><Text size="sm" c="dimmed" mt={3}>{a.username}</Text><Text size="xs" c="dimmed" mt={4}>{a.host}</Text></Box>
        <Group gap="xs"><Badge color={a.enabled ? 'forest' : 'gray'}>{a.enabled ? 'Ativa' : 'Pausada'}</Badge><Button size="xs" variant="default" loading={pending === a.id} disabled={pending !== null && pending !== a.id} onClick={() => toggle(a)}>{a.enabled ? 'Pausar' : 'Ativar'}</Button><Button size="xs" variant="subtle" color="red" disabled={pending !== null} onClick={() => setDeleting(a)}>Excluir</Button></Group>
      </Group>)}
    </Card>
    <Modal opened={opened} onClose={() => { if (!saving) setOpened(false); }} title="Adicionar conta de e-mail" closeOnClickOutside={!saving} closeOnEscape={!saving} withCloseButton={!saving}>
      <form onSubmit={submit}><Stack gap="md">
        <Text size="sm" c="dimmed">Use os dados IMAP e a senha de app do seu provedor de e-mail.</Text>
        <TextInput label="Nome da conta" placeholder="Ex.: Principal" value={label} onChange={e => setLabel(e.target.value)} required data-autofocus />
        <TextInput label="Servidor IMAP" value={host} onChange={e => setHost(e.target.value)} placeholder="imap.gmail.com" />
        <TextInput label="Usuário / e-mail" placeholder="voce@exemplo.com" value={username} onChange={e => setUsername(e.target.value)} required autoComplete="off" />
        <PasswordInput label="Senha de app" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="new-password" visibilityToggleButtonProps={{ 'aria-label': 'Mostrar ou ocultar senha' }} />
        <Group justify="flex-end" mt="sm"><Button variant="default" onClick={() => setOpened(false)} disabled={saving}>Cancelar</Button><Button type="submit" loading={saving}>Adicionar conta</Button></Group>
      </Stack></form>
    </Modal>
    {deleting && <ConfirmDialog title="Excluir conta de e-mail?" description={`A conta “${deleting.label}” deixará de ser consultada. As faturas já processadas serão preservadas.`} onClose={() => setDeleting(null)} onConfirm={async () => { await api.deleteAccount(deleting.id); success('Conta excluída.'); await Promise.all([refresh(), refreshStatus()]); }} />}
  </Box>;
}
