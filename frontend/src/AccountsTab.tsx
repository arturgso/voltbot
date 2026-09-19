import { useCallback, useEffect, useState } from 'react';
import { Badge, Box, Button, Card, Grid, Group, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api, type EmailAccount } from './api';

export default function AccountsTab({ refreshStatus }: { refreshStatus: () => Promise<void> }) {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [label, setLabel] = useState('');
  const [host, setHost] = useState('imap.gmail.com');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const refresh = useCallback(async () => {
    try {
      setAccounts(await api.accounts());
    } catch (e) {
      notifications.show({ color: 'red', title: 'Falha', message: String(e) });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const fail = (err: unknown) =>
    notifications.show({ color: 'red', title: 'Falha', message: String(err) });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.addAccount(label, host || 'imap.gmail.com', username, password);
      setLabel('');
      setHost('imap.gmail.com');
      setUsername('');
      setPassword('');
      refresh();
      refreshStatus();
    } catch (err) {
      fail(err);
    }
  };

  return (
    <Card withBorder padding="lg">
      <Text size="sm" fw={700} tt="uppercase" mb="md">
        Contas de e-mail (origem das faturas)
      </Text>
      <form onSubmit={submit}>
        <Grid mb="sm">
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput label="RÓTULO" placeholder="Principal" value={label} onChange={(e) => setLabel(e.target.value)} required />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput label="IMAP HOST" value={host} onChange={(e) => setHost(e.target.value)} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput label="USUÁRIO" placeholder="email@gmail.com" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput label="SENHA DE APP" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Grid.Col>
        </Grid>
        <Button type="submit">ADICIONAR CONTA</Button>
      </form>
      <Stack gap={0} mt="md">
        {accounts.map((a) => (
          <Group key={a.id} justify="space-between" py="sm" style={{ borderTop: '1px solid #e9ecef' }}>
            <Box>
              <Text size="sm" fw={600}>
                {a.label} · {a.username}
              </Text>
              <Text size="xs" c="dimmed" ff="monospace">
                {a.host}
              </Text>
            </Box>
            <Group gap="xs">
              <Badge color={a.enabled ? 'green' : 'gray'} variant="light">
                {a.enabled ? 'ATIVA' : 'PAUSADA'}
              </Badge>
              <Button
                size="xs"
                variant="outline"
                color="gray"
                onClick={async () => {
                  try {
                    await api.toggleAccount(a.id, !a.enabled);
                    refresh();
                    refreshStatus();
                  } catch (err) {
                    fail(err);
                  }
                }}
              >
                {a.enabled ? 'PAUSAR' : 'ATIVAR'}
              </Button>
              <Button
                size="xs"
                variant="outline"
                color="red"
                onClick={async () => {
                  if (!confirm('Excluir esta conta de e-mail?')) return;
                  try {
                    await api.deleteAccount(a.id);
                    refresh();
                    refreshStatus();
                  } catch (err) {
                    fail(err);
                  }
                }}
              >
                EXCLUIR
              </Button>
            </Group>
          </Group>
        ))}
        {accounts.length === 0 && (
          <Text size="sm" c="dimmed">
            Nenhuma conta.
          </Text>
        )}
      </Stack>
    </Card>
  );
}
