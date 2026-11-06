// Panel del admin de Registros, sin compilar. Los datos entran siempre con textContent, nunca como HTML.
// Habla con /admin/api; las páginas son cascarones que llena según data-page.
"use strict";

const byId = (id) => document.getElementById(id);

function show(el, text) {
  el.textContent = text;
  el.hidden = !text;
}

function fullDate(iso) {
  return iso ? new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" }) : "";
}

// Crea un elemento con texto y clases; los hijos pueden ser nodos o texto.
function el(tag, { text, className, attrs } = {}, ...children) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  node.append(...children);
  return node;
}

async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    return { status: 0, data: { detail: "No se pudo conectar. Revisá tu conexión y probá de nuevo." } };
  }
  if (response.status === 401) {
    location.assign(`/login?next=${encodeURIComponent(location.pathname)}`);
    return new Promise(() => {}); // la página se va
  }
  let data = null;
  try {
    data = await response.json();
  } catch { /* 204 o un error sin JSON */ }
  return { status: response.status, data };
}

const FIELD_NAMES = {
  slug: "Identificador", name: "Nombre", charge_amount: "Monto", currency: "Moneda", email: "Correo",
  password: "Clave", scope: "Alcance", form_html: "form.html", schema: "schema.json", manifest: "manifest.json",
};

// 422 de esquema: lista de {loc, msg}; los de admin_ops, un texto. Nunca repite lo escrito.
function errorText(result) {
  const detail = result.data && result.data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => {
      const field = item.loc && item.loc[item.loc.length - 1];
      return FIELD_NAMES[field] ? `${FIELD_NAMES[field]}: ${item.msg}` : item.msg;
    }).join(". ");
  }
  return "No se pudo completar. Probá de nuevo.";
}

// Marca como inválidos los campos que nombra un 422 de esquema.
function markInvalid(form, result) {
  for (const input of form.querySelectorAll(".invalid")) input.classList.remove("invalid");
  const detail = result.data && result.data.detail;
  if (!Array.isArray(detail)) return;
  for (const item of detail) {
    const name = item.loc && item.loc[item.loc.length - 1];
    const input = name && form.elements[name];
    if (input && input.classList) input.classList.add("invalid");
  }
}

async function submitting(form, work) {
  const button = form.querySelector("button[type=submit]");
  if (button.disabled) return;
  button.disabled = true;
  try {
    await work();
  } finally {
    button.disabled = false;
  }
}

function badge(text, ok) {
  return el("span", { text, className: `badge ${ok ? "ok" : "off"}` });
}

function setActiveBadge(node, active) {
  node.textContent = active ? "Activo" : "Desactivado";
  node.className = `badge ${active ? "ok" : "off"}`;
}

const tenantsUrl = (id, rest = "") => `/admin/api/tenants/${id}${rest}`;

// --- Lista de espacios ---

function listPage() {
  const form = byId("new-tenant");

  async function load() {
    show(byId("error"), "");
    const result = await api("GET", "/admin/api/tenants");
    if (result.status !== 200) {
      show(byId("error"), errorText(result));
      return;
    }
    const rows = byId("rows");
    rows.replaceChildren();
    byId("empty").hidden = result.data.length > 0;
    byId("results").hidden = result.data.length === 0;
    for (const tenant of result.data) {
      const row = rows.insertRow();
      const link = el("a", { text: tenant.name, attrs: { href: `/admin/espacios/${tenant.id}` } });
      row.insertCell().append(link, el("br"), el("span", { text: tenant.slug, className: "muted mono" }));
      row.insertCell().textContent = `${tenant.currency} ${tenant.charge_amount}`;
      row.insertCell().textContent = tenant.users_active;
      row.insertCell().textContent = tenant.keys_active;
      row.insertCell().textContent = tenant.persons_active;
      row.insertCell().append(el("span", { text: tenant.has_form ? "Cargado" : "Falta", className: `badge ${tenant.has_form ? "ok" : "warn"}` }));
      // `active` lo suma la API cuando hay desactivación; sin él no se pinta nada.
      row.insertCell().append(tenant.active === undefined ? "" : badge(tenant.active ? "Activo" : "Desactivado", tenant.active));
    }
  }

  byId("new-toggle").addEventListener("click", () => {
    form.hidden = !form.hidden;
    if (!form.hidden) form.elements.slug.focus();
  });
  byId("new-cancel").addEventListener("click", () => {
    form.hidden = true;
    form.reset();
    show(byId("new-error"), "");
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(form, async () => {
      show(byId("new-error"), "");
      const result = await api("POST", "/admin/api/tenants", {
        slug: form.elements.slug.value.trim(),
        name: form.elements.name.value.trim(),
        charge_amount: form.elements.charge_amount.value.trim(),
        currency: form.elements.currency.value.trim(),
      });
      if (result.status === 201) {
        location.assign(`/admin/espacios/${result.data.id}`);
        return;
      }
      markInvalid(form, result);
      show(byId("new-error"), errorText(result));
    });
  });
  load();
}

// --- Un espacio ---

const SCOPE_TEXT = { read: "read: identificar", charge: "charge: identificar y cobrar" };
const KEY_ENV = { read: "REGISTROS_READ_KEY", charge: "REGISTROS_CHARGE_KEY" };

function tenantPage() {
  const id = byId("tenant").dataset.tenantId;
  const dataForm = byId("data-form");
  const formForm = byId("form-form");
  const userForm = byId("user-form");
  const passwordForm = byId("password-form");
  const keyForm = byId("key-form");
  let tenant = null;
  let passwordUser = null;

  function fillData() {
    byId("title").textContent = tenant.name;
    document.title = `${tenant.name} · Registros`;
    dataForm.elements.slug.value = tenant.slug;
    dataForm.elements.name.value = tenant.name;
    dataForm.elements.charge_amount.value = tenant.charge_amount;
    dataForm.elements.currency.value = tenant.currency;
    byId("form-state").textContent = tenant.has_form
      ? "Hay un formulario cargado. Cargar uno nuevo lo reemplaza."
      : "Todavía no hay formulario: sin él, el espacio no puede cargar fichas.";
    byId("form-download").hidden = !tenant.has_form;
    renderActive();
  }

  function renderActive() {
    const toggle = byId("active-toggle");
    if (tenant.active === undefined) { // la API todavía no informa el estado
      byId("active-badge").hidden = true;
      byId("active-note").textContent = "";
      toggle.hidden = true;
      return;
    }
    byId("active-badge").hidden = false;
    setActiveBadge(byId("active-badge"), tenant.active);
    byId("active-note").textContent = tenant.active
      ? "Sus usuarios entran y el agente identifica y cobra."
      : "Sin login, sin identificar ni cobrar. Desde acá se sigue viendo y editando todo.";
    toggle.textContent = tenant.active ? "Desactivar el espacio" : "Reactivar el espacio";
    toggle.className = tenant.active ? "danger" : "ghost";
    toggle.hidden = false;
  }

  function renderUsers() {
    const rows = byId("users-rows");
    rows.replaceChildren();
    byId("users-empty").hidden = tenant.users.length > 0;
    byId("users-table").hidden = tenant.users.length === 0;
    for (const user of tenant.users) {
      const row = rows.insertRow();
      row.insertCell().textContent = user.email;
      row.insertCell().append(badge(user.active ? "Activo" : "Desactivado", user.active));
      row.insertCell().textContent = fullDate(user.created_at);
      const actions = el("div", { className: "cell-actions" });
      const pass = el("button", { text: "Nueva clave", className: "ghost", attrs: { type: "button" } });
      pass.addEventListener("click", () => openPassword(user));
      const toggle = el("button", { text: user.active ? "Desactivar" : "Activar", className: "ghost", attrs: { type: "button" } });
      toggle.addEventListener("click", () => toggleUser(user));
      actions.append(pass, toggle);
      row.insertCell().append(actions);
    }
  }

  function renderKeys() {
    const rows = byId("keys-rows");
    rows.replaceChildren();
    byId("keys-empty").hidden = tenant.keys.length > 0;
    byId("keys-table").hidden = tenant.keys.length === 0;
    for (const key of tenant.keys) {
      const row = rows.insertRow();
      row.insertCell().textContent = key.name;
      row.insertCell().textContent = SCOPE_TEXT[key.scope] || key.scope;
      row.insertCell().textContent = fullDate(key.created_at);
      row.insertCell().append(key.revoked_at ? badge(`Revocada ${fullDate(key.revoked_at)}`, false) : badge("Activa", true));
      const cell = row.insertCell();
      if (!key.revoked_at) {
        const revoke = el("button", { text: "Revocar", className: "danger", attrs: { type: "button" } });
        revoke.addEventListener("click", () => revokeKey(key));
        cell.append(revoke);
      }
    }
  }

  async function load() {
    const result = await api("GET", tenantsUrl(id));
    if (result.status !== 200) {
      show(byId("error"), errorText(result));
      return;
    }
    tenant = result.data;
    fillData();
    renderUsers();
    renderKeys();
  }

  // Datos
  dataForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(dataForm, async () => {
      show(byId("data-error"), "");
      show(byId("data-ok"), "");
      const result = await api("PATCH", tenantsUrl(id), {
        name: dataForm.elements.name.value.trim(),
        charge_amount: dataForm.elements.charge_amount.value.trim(),
        currency: dataForm.elements.currency.value.trim(),
      });
      markInvalid(dataForm, result);
      if (result.status !== 200) {
        show(byId("data-error"), errorText(result));
        return;
      }
      tenant = { ...tenant, ...result.data };
      fillData();
      show(byId("data-ok"), "Datos guardados.");
    });
  });

  // Activar o desactivar
  byId("active-toggle").addEventListener("click", async () => {
    const next = !tenant.active;
    const question = next
      ? "¿Reactivar este espacio? Vuelven a valer las claves de API que no estén revocadas y sus usuarios pueden entrar. Las sesiones cerradas no vuelven."
      : "¿Desactivar este espacio? Corta el login y los links de sus usuarios, y el agente deja de identificar y cobrar. Las conversaciones en curso no se cobran.";
    if (!window.confirm(question)) return;
    show(byId("error"), "");
    const result = await api("PUT", tenantsUrl(id, "/active"), { active: next });
    if (result.status !== 204) {
      show(byId("error"), errorText(result));
      return;
    }
    await load();
  });

  // Formulario
  formForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(formForm, async () => {
      show(byId("form-error"), "");
      show(byId("form-ok"), "");
      const files = ["form_html", "schema", "manifest"].map((name) => formForm.elements[name].files[0]);
      if (files.some((file) => !file)) {
        show(byId("form-error"), "Elegí los tres archivos: form.html, schema.json y manifest.json.");
        return;
      }
      const [form_html, schema, manifest] = await Promise.all(files.map((file) => file.text()));
      const result = await api("PUT", tenantsUrl(id, "/form"), { form_html, schema, manifest });
      if (result.status !== 200) {
        show(byId("form-error"), errorText(result));
        return;
      }
      formForm.reset();
      show(byId("form-ok"), `Formulario cargado. Fichas actualizadas: ${result.data.persons_updated}.`);
      await load();
    });
  });
  byId("form-download").addEventListener("click", async () => {
    show(byId("form-error"), "");
    const result = await api("GET", tenantsUrl(id, "/form"));
    if (result.status !== 200) {
      show(byId("form-error"), errorText(result));
      return;
    }
    const files = [["form.html", result.data.form_html, "text/html"], ["schema.json", result.data.schema, "application/json"],
      ["manifest.json", result.data.manifest, "application/json"]];
    for (const [name, text, type] of files) {
      const url = URL.createObjectURL(new Blob([text], { type }));
      const link = el("a", { attrs: { href: url, download: name } });
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  });

  // Usuarios
  userForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(userForm, async () => {
      show(byId("user-error"), "");
      show(byId("user-ok"), "");
      const result = await api("POST", tenantsUrl(id, "/users"), {
        email: userForm.elements.email.value.trim(),
        password: userForm.elements.password.value,
      });
      markInvalid(userForm, result);
      if (result.status !== 201) {
        show(byId("user-error"), errorText(result));
        return;
      }
      show(byId("user-ok"), `Usuario ${result.data.email} creado.`);
      userForm.reset();
      await load();
    });
  });
  function openPassword(user) {
    passwordUser = user;
    byId("password-title").textContent = `Clave nueva para ${user.email}`;
    show(byId("password-error"), "");
    passwordForm.reset();
    passwordForm.hidden = false;
    passwordForm.elements.password.focus();
  }
  byId("password-cancel").addEventListener("click", () => {
    passwordForm.hidden = true;
    passwordForm.reset();
  });
  passwordForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(passwordForm, async () => {
      show(byId("password-error"), "");
      const result = await api("PUT", tenantsUrl(id, `/users/${passwordUser.id}/password`), {
        password: passwordForm.elements.password.value,
      });
      markInvalid(passwordForm, result);
      if (result.status !== 204) {
        show(byId("password-error"), errorText(result));
        return;
      }
      passwordForm.hidden = true;
      passwordForm.reset();
      show(byId("user-ok"), `Clave cambiada para ${passwordUser.email}. Sus sesiones se cerraron.`);
    });
  });
  async function toggleUser(user) {
    const next = !user.active;
    if (!next && !window.confirm(`¿Desactivar a ${user.email}? Se cierran sus sesiones.`)) return;
    show(byId("user-error"), "");
    const result = await api("PUT", tenantsUrl(id, `/users/${user.id}/active`), { active: next });
    if (result.status !== 204) {
      show(byId("user-error"), errorText(result));
      return;
    }
    await load();
  }

  // Claves
  keyForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitting(keyForm, async () => {
      show(byId("key-error"), "");
      if (!byId("key-box").hidden) { // la clave anterior no se vuelve a mostrar: que no se pierda
        show(byId("key-error"), "Copiá la clave de arriba y tocá \"Ya la copié\" antes de crear otra.");
        return;
      }
      const result = await api("POST", tenantsUrl(id, "/keys"), {
        name: keyForm.elements.name.value.trim(),
        scope: keyForm.elements.scope.value,
      });
      markInvalid(keyForm, result);
      if (result.status !== 201) {
        show(byId("key-error"), errorText(result));
        return;
      }
      byId("key-value").value = result.data.key;
      byId("key-hint").textContent = `Cargala en Atentina, en el cliente de este espacio, como ${KEY_ENV[result.data.scope]}.`;
      byId("key-box").hidden = false;
      byId("key-value").select();
      keyForm.reset();
      await load();
    });
  });
  byId("key-value").addEventListener("focus", (event) => event.target.select());
  byId("key-copy").addEventListener("click", async () => {
    const input = byId("key-value");
    input.select();
    let copied = false;
    try {
      await navigator.clipboard.writeText(input.value);
      copied = true;
    } catch { /* sin https no hay clipboard: queda execCommand */ }
    if (!copied) copied = document.execCommand("copy");
    byId("key-copy").textContent = copied ? "Copiada" : "Seleccionada: copiala con Ctrl+C";
  });
  byId("key-close").addEventListener("click", () => {
    byId("key-value").value = "";
    byId("key-box").hidden = true;
    byId("key-copy").textContent = "Copiar";
  });
  async function revokeKey(key) {
    if (!window.confirm(`¿Revocar la clave "${key.name}"? Si el agente la usa, deja de identificar y de cobrar hasta que le cargues otra. No se puede deshacer.`)) return;
    show(byId("error"), "");
    const result = await api("DELETE", tenantsUrl(id, `/keys/${key.id}`));
    if (result.status !== 204) {
      show(byId("error"), errorText(result));
      return;
    }
    await load();
  }

  load();
}

// --- Fichas de un espacio (solo lectura) ---

function personsPage() {
  const id = byId("persons").dataset.tenantId;
  const form = byId("filters");
  const state = { page: 1 };
  const initial = new URLSearchParams(location.search);
  form.elements.q.value = initial.get("q") || "";
  form.elements.al_dia.value = initial.get("al_dia") || "";
  state.page = Math.max(Number(initial.get("page")) || 1, 1);

  api("GET", tenantsUrl(id)).then((result) => {
    if (result.status === 200) byId("title").textContent = `Fichas de ${result.data.name}`;
  });

  async function load() {
    const params = new URLSearchParams();
    const q = form.elements.q.value.trim();
    const alDia = form.elements.al_dia.value;
    if (q) params.set("q", q);
    if (alDia) params.set("al_dia", alDia);
    if (state.page > 1) params.set("page", state.page);
    const query = params.toString();
    history.replaceState(null, "", query ? `?${query}` : location.pathname);
    show(byId("error"), "");
    const result = await api("GET", tenantsUrl(id, `/persons${query ? `?${query}` : ""}`));
    if (result.status !== 200) {
      show(byId("error"), errorText(result));
      return;
    }
    const { items, total, per_page: perPage } = result.data;
    const pages = Math.max(Math.ceil(total / perPage), 1);
    if (state.page > pages) {
      state.page = pages;
      load();
      return;
    }
    byId("empty").hidden = items.length > 0;
    byId("empty-text").textContent = q || alDia ? "No hay fichas con esa búsqueda." : "Este espacio todavía no tiene fichas.";
    byId("results").hidden = items.length === 0;
    const rows = byId("rows");
    rows.replaceChildren();
    for (const item of items) {
      const row = rows.insertRow();
      row.insertCell().append(el("a", { text: item.name, attrs: { href: `/admin/espacios/${id}/fichas/${item.id}` } }));
      row.insertCell().textContent = item.titular_name;
      row.insertCell().append(el("span", { text: item.al_dia ? "Al día" : "No está al día", className: `badge ${item.al_dia ? "ok" : "warn"}` }));
      row.insertCell().textContent = fullDate(item.updated_at);
    }
    byId("pager").hidden = total <= perPage;
    byId("position").textContent = `Página ${state.page} de ${pages}, ${total} fichas`;
    byId("prev").disabled = state.page <= 1;
    byId("next").disabled = state.page >= pages;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.page = 1;
    load();
  });
  form.elements.al_dia.addEventListener("change", () => {
    state.page = 1;
    load();
  });
  byId("prev").addEventListener("click", () => {
    state.page -= 1;
    load();
  });
  byId("next").addEventListener("click", () => {
    state.page += 1;
    load();
  });
  load();
}

// --- Una ficha (solo lectura) ---

// Datos anidados como pares ruta -> valor: datos.nombre, contactos[0].telefono.
function flatten(value, path, out) {
  if (Array.isArray(value)) {
    value.forEach((item, i) => flatten(item, `${path}[${i}]`, out));
  } else if (value !== null && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) flatten(item, path ? `${path}.${key}` : key, out);
  } else if (value !== null && value !== undefined && value !== "") {
    out.push([path, typeof value === "boolean" ? (value ? "Sí" : "No") : String(value)]);
  }
  return out;
}

function personPage() {
  const { tenantId, personId } = byId("person").dataset;

  async function load() {
    const result = await api("GET", tenantsUrl(tenantId, `/persons/${personId}`));
    if (result.status !== 200) {
      show(byId("error"), errorText(result));
      return;
    }
    const person = result.data;
    byId("title").textContent = person.name;
    document.title = `${person.name} · Registros`;
    byId("summary").hidden = false;
    const alDia = byId("al-dia-badge");
    alDia.textContent = person.al_dia ? "Al día" : "No está al día";
    alDia.className = `badge ${person.al_dia ? "ok" : "warn"}`;
    byId("al-dia-by").textContent = person.al_dia_at ? `Marcó ${person.al_dia_by || "un usuario eliminado"}, ${fullDate(person.al_dia_at)}` : "";

    const pairs = flatten(person.data, "", []);
    byId("data").hidden = false;
    byId("data-empty").hidden = pairs.length > 0;
    byId("data-table").hidden = pairs.length === 0;
    const dataRows = byId("data-rows");
    dataRows.replaceChildren();
    for (const [path, text] of pairs) {
      const row = dataRows.insertRow();
      row.insertCell().append(el("span", { text: path, className: "mono path" }));
      row.insertCell().textContent = text;
    }

    byId("charges").hidden = false;
    byId("charges-empty").hidden = person.charges.length > 0;
    byId("charges-table").hidden = person.charges.length === 0;
    const rows = byId("charges-rows");
    rows.replaceChildren();
    for (const charge of person.charges) {
      const row = rows.insertRow();
      const status = charge.status === "simulated" ? "Simulado" : charge.status;
      [fullDate(charge.created_at), `${charge.currency} ${charge.amount}`, charge.titular_name, charge.from_phone, status, charge.operator_message]
        .forEach((text, i) => {
          const cell = row.insertCell();
          cell.textContent = text;
          if (i === 1 || i === 3) cell.className = "mono";
        });
    }
  }
  load();
}

// --- Arranque ---

const logout = byId("logout");
if (logout) {
  logout.addEventListener("click", async () => {
    await api("POST", "/auth/logout");
    location.assign("/login");
  });
}

({
  "admin-list": listPage,
  "admin-tenant": tenantPage,
  "admin-persons": personsPage,
  "admin-person": personPage,
})[document.body.dataset.page]?.();
