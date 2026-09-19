import { useCallback, useEffect, useState } from 'react';
import { Avatar, Badge, Box, Container, Tabs, Text } from '@mantine/core';
import { api, type Status } from './api';
import RunTab from './RunTab';
import ContactsTab from './ContactsTab';
import AccountsTab from './AccountsTab';

function HeaderBadges({ status }: { status: Status | null }) {
  if (!status) return null;
  const evo = status.evolution_configured;
  return (
    <>
      <Badge
        variant="outline"
        color={evo ? 'green' : 'orange'}
        style={{ borderColor: evo ? '#2f9e44' : undefined }}
      >
        {evo ? `EVOLUTION • ${status.evolution_instance}`.toUpperCase() : 'EVOLUTION DESCONECTADO'}
      </Badge>
      <Badge variant="outline" color="gray">
        {status.email_accounts_enabled} E-MAILS ATIVOS
      </Badge>
      <Badge variant="outline" color="gray">
        {status.installations} INSTALAÇÕES
      </Badge>
      <Badge variant="outline" color="gray">
        {status.contacts} CONTATOS
      </Badge>
    </>
  );
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.status());
    } catch {
      /* backend fora do ar; mantém último estado */
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  return (
    <Box style={{ background: '#f1f3f5', minHeight: '100vh' }}>
      <Box style={{ background: '#101418', color: '#fff' }}>
        <Container size="xl" py="sm" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Text fw={800} size="lg">
            VoltBot <span style={{ color: '#ffd43b' }}>⚡</span>
          </Text>
          <Box style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <HeaderBadges status={status} />
          </Box>
          <Box style={{ marginLeft: 'auto' }}>
            <Avatar color="indigo" radius="xs">
              VB
            </Avatar>
          </Box>
        </Container>
      </Box>

      <Container size="xl">
        <Tabs defaultValue="run" mt="xs">
          <Tabs.List>
            <Tabs.Tab value="run">Executar</Tabs.Tab>
            <Tabs.Tab value="contacts">Instalações &amp; Contatos</Tabs.Tab>
            <Tabs.Tab value="accounts">Contas de e-mail</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="run" pt="md">
            <RunTab status={status} refreshStatus={refreshStatus} />
          </Tabs.Panel>
          <Tabs.Panel value="contacts" pt="md">
            <ContactsTab refreshStatus={refreshStatus} />
          </Tabs.Panel>
          <Tabs.Panel value="accounts" pt="md">
            <AccountsTab refreshStatus={refreshStatus} />
          </Tabs.Panel>
        </Tabs>
      </Container>
    </Box>
  );
}
