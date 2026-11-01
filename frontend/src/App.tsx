import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Group, Tabs, Text } from '@mantine/core';
import { api, type Status } from './api';
import RunTab from './RunTab';
import ContactsTab from './ContactsTab';
import AccountsTab from './AccountsTab';

export default function App() {
  const [activeTab, setActiveTab] = useState<string | null>('run');
  const sections = [{ value: 'run', label: 'Execuções' }, { value: 'contacts', label: 'Instalações e contatos' }, { value: 'accounts', label: 'E-mails' }];
  const [status, setStatus] = useState<Status | null>(null);
  const [statusError, setStatusError] = useState(false);
  const refreshStatus = useCallback(async () => {
    try { setStatus(await api.status()); setStatusError(false); }
    catch { setStatusError(true); }
  }, []);
  useEffect(() => {
    refreshStatus();
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  }, [refreshStatus]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
      <Tabs value={activeTab} onChange={setActiveTab} keepMounted>
        <Tabs.List className="main-tabs" aria-label="Navegação principal">
          {sections.map(section => <Tabs.Tab key={section.value} value={section.value}>{section.label}</Tabs.Tab>)}
        </Tabs.List>
        <main id="conteudo" className="app-main" tabIndex={-1}>
        {statusError && <Alert color="red" mb="md" title="Não foi possível atualizar o status">
          <Group justify="space-between"><Text size="sm">{status ? 'Os indicadores mostram a última consulta disponível.' : 'Confira a disponibilidade do serviço.'}</Text><Button variant="light" color="red" size="xs" onClick={refreshStatus}>Tentar novamente</Button></Group>
        </Alert>}
          <Tabs.Panel value="run"><RunTab status={status} refreshStatus={refreshStatus} /></Tabs.Panel>
          <Tabs.Panel value="contacts"><ContactsTab refreshStatus={refreshStatus} /></Tabs.Panel>
          <Tabs.Panel value="accounts"><AccountsTab refreshStatus={refreshStatus} /></Tabs.Panel>
        </main>
      </Tabs>
    </div>
  );
}
