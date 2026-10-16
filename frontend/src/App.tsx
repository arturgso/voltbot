import { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Container, Group, Tabs, Text } from '@mantine/core';
import { api, type Status } from './api';
import RunTab from './RunTab';
import ContactsTab from './ContactsTab';
import AccountsTab from './AccountsTab';

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [statusError, setStatusError] = useState(false);
  const refreshStatus = useCallback(async () => {
    try { setStatus(await api.status()); setStatusError(false); }
    catch { setStatusError(true); }
  }, []);
  useEffect(() => { refreshStatus(); }, [refreshStatus]);

  return (
    <Box>
      <Container size="lg" className="app-main">
        {statusError && <Alert color="red" mb="md" title="Não foi possível atualizar o status">
          <Group justify="space-between"><Text size="sm">{status ? 'Os indicadores mostram a última consulta disponível.' : 'Confira a disponibilidade do serviço.'}</Text><Button variant="light" color="red" size="xs" onClick={refreshStatus}>Tentar novamente</Button></Group>
        </Alert>}
        <Tabs defaultValue="run" keepMounted>
          <Tabs.List className="main-tabs" aria-label="Navegação principal">
            <Tabs.Tab value="run">Executar</Tabs.Tab>
            <Tabs.Tab value="contacts">Instalações e contatos</Tabs.Tab>
            <Tabs.Tab value="accounts">Contas de e-mail</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="run"><RunTab status={status} refreshStatus={refreshStatus} /></Tabs.Panel>
          <Tabs.Panel value="contacts"><ContactsTab refreshStatus={refreshStatus} /></Tabs.Panel>
          <Tabs.Panel value="accounts"><AccountsTab refreshStatus={refreshStatus} /></Tabs.Panel>
        </Tabs>
      </Container>
    </Box>
  );
}
