import { useCallback, useEffect, useState } from 'react';
import { Box, Button, Card, Combobox, Grid, Group, Loader, Modal, PasswordInput, Select, Stack, Text, TextInput, useCombobox } from '@mantine/core';
import { api, type Contact, type Installation } from './api';
import { ConfirmDialog, EmptyState, failure, LoadError, success } from './ui';

// Mesma regra de normalize_phone, em domain.py, para comparar números com ou sem 55.
function phoneKey(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  return [10, 11].includes(digits.length) ? `55${digits}` : digits;
}

type Deletion = { kind: 'installation'; value: Installation } | { kind: 'contact'; value: Contact };

export default function ContactsTab({ refreshStatus }: { refreshStatus: () => Promise<void> }) {
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [selectedInstallation, setSelectedInstallation] = useState<string | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [instCode, setInstCode] = useState('');
  const [instLabel, setInstLabel] = useState('');
  const [instPassword, setInstPassword] = useState('');
  const [contactInst, setContactInst] = useState<string | null>(null);
  const [contactPhone, setContactPhone] = useState('');
  const [phoneSearch, setPhoneSearch] = useState('');
  const phoneSelect = useCombobox({ onDropdownClose: () => phoneSelect.resetSelectedOption() });
  const [contactName, setContactName] = useState('');
  const [editing, setEditing] = useState<Contact | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editName, setEditName] = useState('');
  const [modal, setModal] = useState<'installation' | 'installationEdit' | 'contact' | 'edit' | null>(null);
  const [deleting, setDeleting] = useState<Deletion | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const [insts, conts] = await Promise.all([api.installations(), api.contacts()]);
      setInstallations(insts); setContacts(conts);
      setSelectedInstallation(current => insts.some(i => i.code === current) ? current : insts[0]?.code ?? null);
      setContactInst(current => insts.some(i => i.code === current) ? current : insts[0]?.code ?? null);
      setError(false);
    } catch { setError(true); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const uniqueContacts = [...new Map(contacts.map(contact => [phoneKey(contact.phone), contact])).values()];
  const selectedContact = uniqueContacts.find(contact => phoneKey(contact.phone) === phoneKey(contactPhone));
  const searchDigits = phoneSearch.replace(/\D/g, '');
  const matchingContacts = uniqueContacts.filter(contact =>
    contact.name?.toLocaleLowerCase('pt-BR').includes(phoneSearch.trim().toLocaleLowerCase('pt-BR')) ||
    (searchDigits ? phoneKey(contact.phone).includes(searchDigits) : !phoneSearch.trim()));
  const canCreate = /^[+\d\s().-]+$/.test(phoneSearch) && searchDigits.length >= 10 &&
    !uniqueContacts.some(contact => phoneKey(contact.phone) === phoneKey(phoneSearch));
  const openContact = () => {
    setContactInst(selectedInstallation);
    setContactPhone(''); setContactName(''); setPhoneSearch(''); setModal('contact');
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (modal === 'installation' || modal === 'installationEdit') {
        await api.addInstallation(instCode, instLabel || null, instPassword || null);
        setInstCode(''); setInstLabel(''); setInstPassword('');
        success(modal === 'installationEdit' ? 'Instalação atualizada.' : 'Instalação adicionada.');
      } else if (modal === 'contact' && contactInst) {
        if (!contactPhone) return;
        await api.addContact(contactInst, selectedContact?.phone ?? contactPhone, selectedContact?.name ?? (contactName || null));
        setContactPhone(''); setContactName('');
        success('Contato adicionado.');
      } else if (modal === 'edit' && editing) {
        await api.updateContact(editing.id, editPhone, editName || null);
        success('Contato atualizado.');
      } else return;
      setModal(null);
      await Promise.all([refresh(), refreshStatus()]);
    } catch (err) { failure(err); }
    finally { setSaving(false); }
  };
  const deleteItem = async () => {
    if (!deleting) return;
    if (deleting.kind === 'installation') await api.deleteInstallation(deleting.value.code);
    else await api.deleteContact(deleting.value.id);
    success(deleting.kind === 'installation' ? 'Instalação e contatos vinculados excluídos.' : 'Contato excluído.');
    await Promise.all([refresh(), refreshStatus()]);
  };
  const openEdit = (contact: Contact) => {
    if (editing?.id !== contact.id) { setEditPhone(contact.phone); setEditName(contact.name || ''); }
    setEditing(contact); setModal('edit');
  };
  const openInstallation = () => {
    setInstCode(''); setInstLabel(''); setInstPassword(''); setModal('installation');
  };
  const editInstallation = (installation: Installation) => {
    setInstCode(installation.code); setInstLabel(installation.label || '');
    setInstPassword(installation.pdf_password || ''); setModal('installationEdit');
  };

  return <Box>
    {error && <LoadError retry={refresh} />}
    {loading ? <Group justify="center" py="xl"><Loader size="sm" /><Text size="sm" c="dimmed">Carregando cadastros…</Text></Group> : <Grid gutter="lg">
      <Grid.Col span={{ base: 12, md: 5 }}>
        <Card>
          <Group justify="space-between" className="section-heading"><div><h2>Instalações</h2><Text size="sm" c="dimmed" mt={5}>As unidades das suas faturas.</Text></div><Button size="sm" variant="light" onClick={openInstallation}>Adicionar instalação</Button></Group>
          {!error && installations.length === 0 && <EmptyState title="Cadastre sua primeira instalação" description="Use o código da unidade consumidora que aparece na fatura." />}
          {installations.map(i => <Group className="data-row" key={i.code} justify="space-between">
            <button type="button" className="installation-choice row-content" aria-pressed={selectedInstallation === i.code} onClick={() => setSelectedInstallation(i.code)}><span className="installation-name">{i.label || 'Sem nome'}</span><span className="installation-code">UC {i.code}</span><span className="installation-count">{i.contacts} contato{i.contacts === 1 ? '' : 's'}</span></button>
            <Group gap={4}><Button size="xs" variant="default" onClick={() => editInstallation(i)}>Editar</Button><Button size="xs" variant="subtle" color="red" onClick={() => setDeleting({ kind: 'installation', value: i })}>Excluir</Button></Group>
          </Group>)}
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 7 }}>
        <Card>
          <Group justify="space-between" className="section-heading"><div><h2>Contatos</h2><Text size="sm" c="dimmed" mt={5}>{installations.find(i => i.code === selectedInstallation)?.label || (selectedInstallation ? `UC ${selectedInstallation}` : 'Selecione uma instalação.')}</Text></div><Button size="sm" onClick={openContact} disabled={!installations.length || error}>Adicionar contato</Button></Group>
          {!error && contacts.filter(c => c.installation === selectedInstallation).length === 0 && <EmptyState title="Nenhum contato cadastrado" description={installations.length ? 'Vincule um contato a uma instalação para receber suas faturas.' : 'Cadastre uma instalação primeiro para vincular seus contatos.'} />}
          {contacts.filter(c => c.installation === selectedInstallation).map(c => <Group className="data-row" key={c.id} justify="space-between">
            <Box className="row-content"><Text size="sm" fw={600}>{c.name || 'Sem nome'}</Text><Text size="sm" c="dimmed" mt={3}>{c.phone}</Text><Text size="xs" c="dimmed" mt={5}>{c.installation_label || 'Instalação'} · {c.installation}</Text></Box>
            <Group gap={4}><Button size="xs" variant="default" onClick={() => openEdit(c)}>Editar</Button><Button size="xs" variant="subtle" color="red" onClick={() => setDeleting({ kind: 'contact', value: c })}>Excluir</Button></Group>
          </Group>)}
        </Card>
      </Grid.Col>
    </Grid>}
    <Modal opened={modal !== null} onClose={() => { if (!saving) setModal(null); }} title={modal === 'installation' ? 'Adicionar instalação' : modal === 'installationEdit' ? 'Editar instalação' : modal === 'edit' ? 'Editar contato' : 'Adicionar contato'} closeOnClickOutside={!saving} closeOnEscape={!saving} withCloseButton={!saving}>
      <form onSubmit={submit}><Stack gap="md">
        {modal === 'installation' || modal === 'installationEdit' ? <>
          <Text size="sm" c="dimmed">Você encontra o código da unidade consumidora na sua fatura.</Text>
          <TextInput label="Código da instalação (UC)" placeholder="Ex.: 0200420281" value={instCode} onChange={e => setInstCode(e.target.value)} required readOnly={modal === 'installationEdit'} data-autofocus />
          <TextInput label="Nome da instalação" placeholder="Ex.: Casa" value={instLabel} onChange={e => setInstLabel(e.target.value)} />
          <PasswordInput label="Senha para abrir o PDF" description="Opcional. Será enviada na mensagem da fatura. Deixe em branco para remover." value={instPassword} onChange={e => setInstPassword(e.target.value)} autoComplete="new-password" visibilityToggleButtonProps={{ 'aria-label': 'Mostrar ou ocultar senha do PDF' }} />
        </> : modal === 'contact' ? <>
          <Select label="Instalação" value={contactInst} onChange={setContactInst} data={installations.map(i => ({ value: i.code, label: `${i.label || 'Instalação'} · ${i.code}` }))} required searchable nothingFoundMessage="Nenhuma instalação encontrada" data-autofocus />
          <Combobox store={phoneSelect} onOptionSubmit={value => {
            const existing = uniqueContacts.find(contact => phoneKey(contact.phone) === value);
            const phone = existing?.phone ?? searchDigits;
            setContactPhone(phone); setContactName('');
            setPhoneSearch(existing ? `${existing.name || 'Sem nome'} · ${existing.phone}` : phone);
            phoneSelect.closeDropdown();
          }}>
            <Combobox.Target>
              <TextInput label="WhatsApp" description="Selecione um contato ou digite um novo número com DDD." placeholder="Buscar por nome ou número" value={phoneSearch}
                onChange={event => { setPhoneSearch(event.currentTarget.value); setContactPhone(''); setContactName(''); phoneSelect.openDropdown(); phoneSelect.updateSelectedOptionIndex(); }}
                onFocus={() => phoneSelect.openDropdown()} onClick={() => phoneSelect.openDropdown()} onBlur={() => phoneSelect.closeDropdown()}
                rightSection={<Combobox.Chevron />} rightSectionPointerEvents="none" required autoComplete="off" />
            </Combobox.Target>
            <Combobox.Dropdown>
              <Combobox.Options mah={220} style={{ overflowY: 'auto' }}>
                {matchingContacts.map(contact => <Combobox.Option value={phoneKey(contact.phone)} key={phoneKey(contact.phone)}>{contact.name || 'Sem nome'} · {contact.phone}</Combobox.Option>)}
                {canCreate && <Combobox.Option value={phoneKey(phoneSearch)}>Cadastrar novo número: {searchDigits}</Combobox.Option>}
                {!matchingContacts.length && !canCreate && <Combobox.Empty>Digite um número com DDD para cadastrar um novo contato.</Combobox.Empty>}
              </Combobox.Options>
            </Combobox.Dropdown>
          </Combobox>
          {contactPhone && !selectedContact && <TextInput label="Nome do contato" description="Opcional" placeholder="Ex.: Beatriz" value={contactName} onChange={event => setContactName(event.currentTarget.value)} />}
        </> : <>
          <TextInput label="WhatsApp" value={editPhone} onChange={e => setEditPhone(e.target.value)} required type="tel" data-autofocus />
          <TextInput label="Nome do contato" value={editName} onChange={e => setEditName(e.target.value)} />
        </>}
        <Group justify="flex-end" mt="sm"><Button variant="default" disabled={saving} onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" loading={saving} disabled={modal === 'contact' && !contactPhone}>{modal === 'edit' || modal === 'installationEdit' ? 'Salvar alterações' : 'Adicionar'}</Button></Group>
      </Stack></form>
    </Modal>
    {deleting && <ConfirmDialog title={deleting.kind === 'installation' ? 'Excluir instalação?' : 'Excluir contato?'} description={deleting.kind === 'installation' ? `A instalação ${deleting.value.code} e todos os seus contatos vinculados serão excluídos. Essa ação não pode ser desfeita.` : `O contato ${deleting.value.name || deleting.value.phone} será removido desta instalação. Essa ação não pode ser desfeita.`} onClose={() => setDeleting(null)} onConfirm={deleteItem} />}
  </Box>;
}
