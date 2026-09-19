import { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  Grid,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api, type Contact, type Installation } from './api';

export default function ContactsTab({ refreshStatus }: { refreshStatus: () => Promise<void> }) {
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [instCode, setInstCode] = useState('');
  const [instLabel, setInstLabel] = useState('');
  const [contactInst, setContactInst] = useState<string | null>(null);
  const [contactPhone, setContactPhone] = useState('');
  const [contactName, setContactName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editName, setEditName] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [insts, conts] = await Promise.all([api.installations(), api.contacts()]);
      setInstallations(insts);
      setContacts(conts);
      if (!contactInst && insts.length > 0) setContactInst(insts[0].code);
    } catch (e) {
      notifications.show({ color: 'red', title: 'Falha', message: String(e) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const fail = (err: unknown) =>
    notifications.show({ color: 'red', title: 'Falha', message: String(err) });

  const addInstallation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.addInstallation(instCode, instLabel || null);
      setInstCode('');
      setInstLabel('');
      refresh();
      refreshStatus();
    } catch (err) {
      fail(err);
    }
  };

  const addContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactInst) return;
    try {
      await api.addContact(contactInst, contactPhone, contactName || null);
      setContactPhone('');
      setContactName('');
      refresh();
      refreshStatus();
    } catch (err) {
      fail(err);
    }
  };

  const saveEdit = async (id: number) => {
    try {
      await api.updateContact(id, editPhone, editName || null);
      setEditingId(null);
      refresh();
      refreshStatus();
    } catch (err) {
      fail(err);
    }
  };

  return (
    <Grid>
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card withBorder padding="lg">
          <Text size="sm" fw={700} tt="uppercase" mb="md">
            Instalações
          </Text>
          <form onSubmit={addInstallation}>
            <Grid mb="sm">
              <Grid.Col span={6}>
                <TextInput
                  label="CÓDIGO (UC)"
                  placeholder="0200420281"
                  value={instCode}
                  onChange={(e) => setInstCode(e.target.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <TextInput
                  label="RÓTULO"
                  placeholder="Casa"
                  value={instLabel}
                  onChange={(e) => setInstLabel(e.target.value)}
                />
              </Grid.Col>
            </Grid>
            <Button type="submit">ADICIONAR</Button>
          </form>
          <Stack gap={0} mt="md">
            {installations.map((i) => (
              <Group key={i.code} justify="space-between" py="sm" style={{ borderTop: '1px solid #e9ecef' }}>
                <Box>
                  <Text size="sm" fw={600} ff="monospace">
                    {i.code}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {i.label || '—'} · {i.contacts} contato{i.contacts === 1 ? '' : 's'}
                  </Text>
                </Box>
                <Button
                  size="xs"
                  variant="outline"
                  color="red"
                  onClick={async () => {
                    if (!confirm(`Excluir instalação ${i.code} e seus contatos?`)) return;
                    try {
                      await api.deleteInstallation(i.code);
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
            ))}
          </Stack>
        </Card>
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card withBorder padding="lg">
          <Text size="sm" fw={700} tt="uppercase" mb="md">
            Contatos
          </Text>
          <form onSubmit={addContact}>
            <Grid mb="sm">
              <Grid.Col span={6}>
                <Select
                  label="INSTALAÇÃO"
                  value={contactInst}
                  onChange={setContactInst}
                  data={installations.map((i) => ({
                    value: i.code,
                    label: `${i.code}${i.label ? ` — ${i.label}` : ''}`,
                  }))}
                  required
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <TextInput
                  label="WHATSAPP"
                  placeholder="551199999999"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <TextInput
                  label="NOME"
                  placeholder="Bia"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                />
              </Grid.Col>
            </Grid>
            <Button type="submit">ADICIONAR</Button>
          </form>
          <Stack gap={0} mt="md">
            {contacts.map((c) =>
              editingId === c.id ? (
                <Box key={c.id} py="sm" style={{ borderTop: '1px solid #e9ecef' }}>
                  <Grid mb="xs">
                    <Grid.Col span={6}>
                      <TextInput label="WHATSAPP" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <TextInput label="NOME" value={editName} onChange={(e) => setEditName(e.target.value)} />
                    </Grid.Col>
                  </Grid>
                  <Group gap="xs">
                    <Button size="xs" onClick={() => saveEdit(c.id)}>
                      SALVAR
                    </Button>
                    <Button size="xs" variant="subtle" color="gray" onClick={() => setEditingId(null)}>
                      CANCELAR
                    </Button>
                  </Group>
                </Box>
              ) : (
                <Group key={c.id} justify="space-between" py="sm" style={{ borderTop: '1px solid #e9ecef' }}>
                  <Box>
                    <Text size="sm" fw={600}>
                      {c.name || '—'} · <span style={{ fontFamily: 'monospace' }}>{c.phone}</span>
                    </Text>
                    <Text size="xs" c="dimmed">
                      {c.installation}
                      {c.installation_label ? ` — ${c.installation_label}` : ''}
                    </Text>
                  </Box>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="outline"
                      color="gray"
                      onClick={() => {
                        setEditingId(c.id);
                        setEditPhone(c.phone);
                        setEditName(c.name || '');
                      }}
                    >
                      EDITAR
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      color="red"
                      onClick={async () => {
                        try {
                          await api.deleteContact(c.id);
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
              ),
            )}
            {contacts.length === 0 && (
              <Text size="sm" c="dimmed">
                Nenhum contato.
              </Text>
            )}
          </Stack>
        </Card>
      </Grid.Col>
    </Grid>
  );
}
