const api = async (path, opts = {}) => {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
};

const $ = (id) => document.getElementById(id);
let selectedRun = null;
let pollTimer = null;

// tabs
document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  });
});

async function refreshStatus() {
  const s = await api("/api/status");
  $("badges").innerHTML =
    `<span class="${s.evolution_configured ? "ok" : "warn"}">Evolution: ${s.evolution_configured ? s.evolution_instance + " ✓" : "sem API key"}</span>` +
    `<span>Contas e-mail ativas: ${s.email_accounts_enabled}/${s.email_accounts}</span>` +
    `<span>Instalações: ${s.installations}</span>` +
    `<span>Contatos: ${s.contacts}</span>`;
  $("status-cards").innerHTML = [
    [s.email_accounts_enabled, "contas ativas"],
    [s.installations, "instalações"],
    [s.contacts, "contatos"],
    [s.last_run ? `#${s.last_run.id} ${s.last_run.status}` : "—", "última execução"],
  ].map(([n, l]) => `<div class="card"><div class="num">${n}</div><div class="lbl">${l}</div></div>`).join("");
}

async function refreshRuns() {
  const runs = await api("/api/runs?limit=20");
  $("runs-list").innerHTML = runs.map((r) =>
    `<li data-id="${r.id}" class="${r.id === selectedRun ? "selected" : ""}">
      <span><strong>#${r.id}</strong> ${r.kind}${r.dry_run ? " (dry-run)" : ""} <span class="muted">${r.created_at}</span></span>
      <span class="row-actions"><span class="pill ${r.status}">${r.status}</span><button data-del-run="${r.id}" class="danger">limpar</button></span>
    </li>`).join("") || "<li>Nenhuma execução ainda.</li>";
  document.querySelectorAll("#runs-list li[data-id]").forEach((li) => {
    li.addEventListener("click", (e) => {
      if (e.target.dataset.delRun) return;
      selectedRun = Number(li.dataset.id); refreshRunDetail(); refreshRuns();
    });
  });
  document.querySelectorAll("[data-del-run]").forEach((b) => b.addEventListener("click", async (e) => {
    e.stopPropagation();
    await api(`/api/runs/${b.dataset.delRun}`, { method: "DELETE" });
    if (selectedRun === Number(b.dataset.delRun)) { selectedRun = null; $("run-logs").textContent = "Selecione uma execução."; $("run-detail-id").textContent = ""; $("run-summary").innerHTML = ""; }
    refreshRuns(); refreshStatus();
  }));
  if (selectedRun) refreshRunDetail();
}

async function refreshRunDetail() {
  if (!selectedRun) return;
  const r = await api(`/api/runs/${selectedRun}`);
  $("run-detail-id").textContent = `#${r.id} · ${r.kind}${r.dry_run ? " · dry-run" : ""} · ${r.status}`;
  $("run-logs").textContent = r.logs.map((l) => `[${l.ts}] ${l.message}`).join("\n") || "(sem logs)";
  const s = r.summary || {};
  $("run-summary").innerHTML = s.error
    ? `<span style="color:#b91c1c">Erro: ${s.error}</span>`
    : `Contas: <strong>${s.deliveries ?? "—"}</strong> · Mensagens: <strong>${s.messages ?? "—"}</strong>`;
  return r.status;
}

// run form
$("run-mode").addEventListener("change", (e) => {
  $("run-date-wrap").classList.toggle("hidden", e.target.value !== "date");
  $("run-month-wrap").classList.toggle("hidden", e.target.value !== "month");
});
$("run-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = { mode: fd.get("mode"), dry_run: $("run-dry").checked };
  if (body.mode === "date") body.date = $("run-date").value;
  if (body.mode === "month") body.month = $("run-month").value;
  try {
    const run = await api("/api/runs", { method: "POST", body: JSON.stringify(body) });
    selectedRun = run.id;
    await refreshRuns();
    startPolling();
  } catch (err) { alert("Falha ao iniciar: " + err.message); }
});

async function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const status = await refreshRunDetail().catch(() => null);
    await refreshRuns().catch(() => null);
    if (status && status !== "running") { clearInterval(pollTimer); refreshStatus().catch(() => null); }
  }, 2000);
}

// installations + contacts
async function refreshInstallations() {
  const insts = await api("/api/installations");
  $("inst-list").innerHTML = insts.map((i) =>
    `<li><span class="mono"><strong>${i.code}</strong>${i.label ? " · " + i.label : ""} <span class="muted">(${i.contacts})</span></span>
     <span class="row-actions"><button data-del-inst="${i.code}" class="danger">excluir</button></span></li>`).join("") || "<li>Nenhuma instalação.</li>";
  $("contact-inst").innerHTML = insts.map((i) => `<option value="${i.code}">${i.code}${i.label ? " · " + i.label : ""}</option>`).join("");
  document.querySelectorAll("[data-del-inst]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm(`Excluir instalação ${b.dataset.delInst} e seus contatos?`)) return;
    await api(`/api/installations/${b.dataset.delInst}`, { method: "DELETE" });
    refreshInstallations(); refreshContacts(); refreshStatus();
  }));
  refreshContacts();
}
async function refreshContacts() {
  const contacts = await api("/api/contacts");
  $("contact-list").innerHTML = contacts.map((c) =>
    `<li data-contact="${c.id}"><span><strong class="mono">${c.installation}</strong>${c.installation_label ? " (" + c.installation_label + ")" : ""} · <span class="mono">${c.phone}</span>${c.name ? " · " + c.name : ""}</span>
     <span class="row-actions"><button data-edit-contact="${c.id}">editar</button><button data-del-contact="${c.id}" class="danger">excluir</button></span></li>`).join("") || "<li>Nenhum contato.</li>";
  document.querySelectorAll("[data-del-contact]").forEach((b) => b.addEventListener("click", async () => {
    await api(`/api/contacts/${b.dataset.delContact}`, { method: "DELETE" });
    refreshContacts(); refreshInstallations(); refreshStatus();
  }));
  document.querySelectorAll("[data-edit-contact]").forEach((b) => b.addEventListener("click", () => {
    const c = contacts.find((x) => String(x.id) === b.dataset.editContact);
    const li = document.querySelector(`li[data-contact="${c.id}"]`);
    li.innerHTML = `<span class="grid" style="flex:1">
        <label>WhatsApp <input id="edit-phone-${c.id}" value="${c.phone}"></label>
        <label>Nome <input id="edit-name-${c.id}" value="${c.name || ""}"></label>
      </span>
      <span class="row-actions"><button id="save-${c.id}">salvar</button><button id="cancel-${c.id}">cancelar</button></span>`;
    $(`cancel-${c.id}`).addEventListener("click", refreshContacts);
    $(`save-${c.id}`).addEventListener("click", async () => {
      try {
        await api(`/api/contacts/${c.id}`, { method: "PATCH", body: JSON.stringify({ phone: $(`edit-phone-${c.id}`).value, name: $(`edit-name-${c.id}`).value || null }) });
        refreshContacts(); refreshStatus();
      } catch (err) { alert("Falha: " + err.message); }
    });
  }));
}
$("inst-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await api("/api/installations", { method: "POST", body: JSON.stringify({ code: fd.get("code"), label: fd.get("label") || null }) });
    e.target.reset(); refreshInstallations(); refreshStatus();
  } catch (err) { alert("Falha: " + err.message); }
});
$("contact-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await api("/api/contacts", { method: "POST", body: JSON.stringify({ installation: fd.get("installation"), phone: fd.get("phone"), name: fd.get("name") || null }) });
    e.target.reset(); refreshContacts(); refreshInstallations(); refreshStatus();
  } catch (err) { alert("Falha: " + err.message); }
});

// accounts
async function refreshAccounts() {
  const accs = await api("/api/accounts");
  $("account-list").innerHTML = accs.map((a) =>
    `<li><span><strong>${a.label}</strong> · <span class="mono">${a.username}</span> <span class="muted">${a.host}</span>
      <span class="pill ${a.enabled ? "done" : "running"}">${a.enabled ? "ativa" : "pausada"}</span></span>
     <span class="row-actions">
       <button data-toggle-acc="${a.id}" data-enabled="${a.enabled ? 0 : 1}">${a.enabled ? "pausar" : "ativar"}</button>
       <button data-del-acc="${a.id}" class="danger">excluir</button>
     </span></li>`).join("") || "<li>Nenhuma conta.</li>";
  document.querySelectorAll("[data-toggle-acc]").forEach((b) => b.addEventListener("click", async () => {
    await api(`/api/accounts/${b.dataset.toggleAcc}`, { method: "PATCH", body: JSON.stringify({ enabled: b.dataset.enabled === "1" }) });
    refreshAccounts(); refreshStatus();
  }));
  document.querySelectorAll("[data-del-acc]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Excluir esta conta de e-mail?")) return;
    await api(`/api/accounts/${b.dataset.delAcc}`, { method: "DELETE" });
    refreshAccounts(); refreshStatus();
  }));
}
$("account-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await api("/api/accounts", { method: "POST", body: JSON.stringify({ label: fd.get("label"), host: fd.get("host") || "imap.gmail.com", username: fd.get("username"), password: fd.get("password") }) });
    e.target.reset(); refreshAccounts(); refreshStatus();
  } catch (err) { alert("Falha: " + err.message); }
});

// init
(async () => {
  await refreshStatus();
  await refreshRuns();
  await refreshInstallations();
  await refreshAccounts();
})();
