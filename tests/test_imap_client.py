from datetime import date

import pytest
from imap_tools.errors import MailboxLoginError

from voltbot import imap_client


@pytest.mark.parametrize('monthly', [False, True])
def test_login_failure_identifies_account_without_credentials(monkeypatch, capsys, monthly):
    monkeypatch.setattr(imap_client, '_iter_account_credentials', lambda: [
        ('Principal', 'imap.example.test', 'private@example.test', 'secret-password'),
    ])

    def fail(*args):
        raise MailboxLoginError(command_result=('NO', [b'private@example.test secret-password']), expected='OK')

    monkeypatch.setattr(imap_client, '_fetch_from_account', fail)
    with pytest.raises(imap_client.EmailAccountError) as error:
        if monthly:
            imap_client.find_range_emails(date(2026, 10, 1), date(2026, 11, 1))
        else:
            imap_client.find_day_emails(date(2026, 10, 29))
    output = capsys.readouterr().out + str(error.value)
    assert 'Principal' in output
    assert 'Login recusado' in output
    assert 'senha de aplicativo' in output
    assert 'private@example.test' not in output
    assert 'secret-password' not in output


def test_network_failure_stops_before_next_account(monkeypatch):
    monkeypatch.setattr(imap_client, '_iter_account_credentials', lambda: [
        ('Principal', 'host', 'user', 'password'), ('Outra', 'host', 'user', 'password'),
    ])
    calls = []

    def fail(*args):
        calls.append(args)
        raise TimeoutError('private server response')

    monkeypatch.setattr(imap_client, '_fetch_from_account', fail)
    with pytest.raises(imap_client.EmailAccountError, match='conexão de rede') as error:
        imap_client.find_day_emails(date(2026, 10, 29))
    assert len(calls) == 1
    assert 'private server response' not in str(error.value)


def test_success_logs_count_and_preserves_messages(monkeypatch, capsys):
    messages = [object(), object()]
    monkeypatch.setattr(imap_client, '_iter_account_credentials', lambda: [('Principal', 'host', 'user', 'password')])
    monkeypatch.setattr(imap_client, '_fetch_from_account', lambda *args: messages)
    assert imap_client.find_day_emails(date(2026, 10, 29)) == messages
    assert '2 e-mail(s)' in capsys.readouterr().out
