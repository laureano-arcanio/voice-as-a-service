// Panel de Registros, sin compilar. Los datos entran siempre con textContent, nunca como HTML.
//
// El formulario sale de la base (tenants.form_html). Lo único que espera de ese HTML:
// - `name` con la ruta del dato: datos.nombre, contactos[0].telefono.
// - Filas variables: <div data-repeat="contactos" data-add-label="Agregar contacto"><template>...
//   name="contactos[#].telefono"...</template></div>. Sin filas anidadas.
"use strict";

const byId = (id) => document.getElementById(id);

function show(el, text) {
  el.textContent = text;
  el.hidden = !text;
}

function fullDate(iso) {
  return iso ? new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" }) : "";
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
  if (response.status === 401 && document.body.dataset.page !== "login") {
    location.assign(`/login?next=${encodeURIComponent(location.pathname)}`);
    return new Promise(() => {}); // la página se va
  }
  let data = null;
  try {
    data = await response.json();
  } catch { /* 204 o un error sin JSON */ }
  return { status: response.status, data };
}

function errorText(result) {
  const detail = result.data && result.data.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail.message === "string") return detail.message;
  return "No se pudo completar. Probá de nuevo.";
}

// --- Rutas dentro de un objeto ---

function tokens(path) {
  const parts = [];
  for (const piece of path.split(".")) {
    const match = /^([^[\]]+)((?:\[\d+\])*)$/.exec(piece);
    if (!match || match[1] === "__proto__" || match[1] === "constructor" || match[1] === "prototype") return null;
    parts.push(match[1]);
    for (const index of match[2].matchAll(/\[(\d+)\]/g)) parts.push(Number(index[1]));
  }
  return parts;
}

function getPath(obj, path) {
  const parts = tokens(path);
  if (!parts) return undefined;
  let current = obj;
  for (const part of parts) {
    if (current === null || typeof current !== "object") return undefined;
    current = current[part];
  }
  return current;
}

function setPath(obj, path, value) {
  const parts = tokens(path);
  if (!parts) return;
  let current = obj;
  parts.forEach((part, i) => {
    if (i === parts.length - 1) {
      current[part] = value;
      return;
    }
    const next = current[part];
    if (next === null || typeof next !== "object") current[part] = typeof parts[i + 1] === "number" ? [] : {};
    current = current[part];
  });
}

function deletePath(obj, path) {
  const parts = tokens(path);
  if (!parts) return;
  let current = obj;
  for (const part of parts.slice(0, -1)) {
    if (current === null || typeof current !== "object") return;
    current = current[part];
  }
  if (current !== null && typeof current === "object") delete current[parts[parts.length - 1]];
}

function isEmpty(value) {
  if (value === undefined || value === null) return true;
  if (Array.isArray(value)) return value.length === 0;
  return typeof value === "object" && Object.keys(value).length === 0;
}

function prune(value) {
  if (Array.isArray(value)) {
    return Array.from(value, prune).filter((item) => !isEmpty(item));
  }
  if (value !== null && typeof value === "object") {
    const out = {};
    for (const [key, item] of Object.entries(value)) {
      const clean = prune(item);
      if (!isEmpty(clean)) out[key] = clean;
    }
    return out;
  }
  return value;
}

// --- Formulario del tenant ---

function controls(form) {
  return [...form.elements].filter((el) => el.name && !el.closest("template"));
}

function readControl(form, el) {
  const same = controls(form).filter((other) => other.name === el.name);
  if (el.type === "checkbox") {
    if (same.length > 1) return same.filter((box) => box.checked).map((box) => box.value);
    if (!el.checked) return undefined;
    return el.hasAttribute("value") ? el.value : true;
  }
  if (el.type === "radio") {
    const checked = same.find((radio) => radio.checked);
    return checked ? checked.value : undefined;
  }
  if (el.tagName === "SELECT" && el.multiple) return [...el.selectedOptions].map((option) => option.value);
  const text = el.value.trim();
  if (!text) return undefined;
  if (el.type === "number" && Number.isFinite(Number(text))) return Number(text);
  return text;
}

function writeControl(el, value) {
  if (el.type === "checkbox") {
    el.checked = Array.isArray(value) ? value.includes(el.value) : value === true || (value !== undefined && value === el.value);
  } else if (el.type === "radio") {
    el.checked = value !== undefined && String(value) === el.value;
  } else if (el.tagName === "SELECT" && el.multiple) {
    for (const option of el.options) option.selected = Array.isArray(value) && value.includes(option.value);
  } else {
    el.value = value === undefined || value === null ? "" : String(value);
  }
}

class Repeat {
  constructor(box, page) {
    this.box = box;
    this.page = page;
    this.prefix = box.dataset.repeat;
    this.template = box.querySelector("template");
    this.rows = document.createElement("div");
    this.add = document.createElement("button");
    this.add.type = "button";
    this.add.className = "ghost";
    this.add.textContent = box.dataset.addLabel || "Agregar";
    this.add.addEventListener("click", () => this.addRow());
    box.append(this.rows, this.add);
  }

  addRow() {
    const row = document.createElement("div");
    row.className = "repeat-row";
    row.append(this.template.content.cloneNode(true));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost";
    remove.textContent = "Quitar";
    remove.addEventListener("click", () => {
      const index = [...this.rows.children].indexOf(row);
      const stored = getPath(this.page.baseline, this.prefix);
      if (Array.isArray(stored)) stored.splice(index, 1);
      row.remove();
      this.renumber();
    });
    row.append(remove);
    this.rows.append(row);
    this.renumber();
    return row;
  }

  renumber() {
    [...this.rows.children].forEach((row, index) => {
      for (const el of row.querySelectorAll("[name]")) {
        el.dataset.nameTemplate ??= el.name;
        el.name = el.dataset.nameTemplate.replace("[#]", `[${index}]`);
      }
    });
  }

  setCount(count) {
    this.rows.replaceChildren();
    for (let i = 0; i < count; i += 1) this.addRow();
  }
}

class PersonPage {
  constructor() {
    this.form = byId("ficha");
    this.personId = byId("status").dataset.personId;
    this.version = null;
    this.baseline = {};
    this.repeats = [...this.form.querySelectorAll("[data-repeat]")].map((box) => new Repeat(box, this));
    this.accordions();
    this.form.addEventListener("submit", (event) => {
      event.preventDefault();
      this.save();
    });
    byId("reload").addEventListener("click", () => this.load());
    byId("delete").addEventListener("click", () => this.remove());
    byId("al-dia-toggle").addEventListener("click", () => this.toggleAlDia());
    if (this.personId) {
      this.load();
    } else {
      for (const repeat of this.repeats) repeat.setCount(1);
    }
  }

  // Cada fieldset de primer nivel pasa a ser un acordeón: en una ficha nueva abre el primero; en una
  // existente, todos cerrados (los cobros, arriba, quedan abiertos).
  accordions() {
    const sets = [...this.form.querySelectorAll("fieldset")].filter((set) => !set.parentElement.closest("fieldset"));
    sets.forEach((set, index) => {
      const details = document.createElement("details");
      details.className = "acc";
      details.open = !this.personId && index === 0;
      const summary = document.createElement("summary");
      const legend = set.querySelector(":scope > legend");
      summary.textContent = legend ? legend.textContent : "Sección";
      if (legend) legend.hidden = true;
      set.before(details);
      details.append(summary, set);
    });
  }

  fill(person) {
    this.personId = person.id;
    this.version = person.version;
    this.baseline = structuredClone(person.data);
    for (const repeat of this.repeats) {
      const stored = getPath(person.data, repeat.prefix);
      repeat.setCount(Math.max(Array.isArray(stored) ? stored.length : 0, 1));
    }
    for (const el of controls(this.form)) writeControl(el, getPath(person.data, el.name));
    byId("title").textContent = person.name;
    document.title = `${person.name} · Registros`;
    byId("delete").hidden = false;
    byId("reload").hidden = true;
    this.renderAlDia(person);
    this.renderCharges(person.charges);
  }

  renderAlDia(person) {
    byId("status").hidden = false;
    this.alDia = person.al_dia;
    const badge = byId("al-dia-badge");
    badge.textContent = person.al_dia ? "Al día" : "No está al día";
    badge.className = `badge ${person.al_dia ? "ok" : "warn"}`;
    byId("al-dia-by").textContent = person.al_dia_at ? `Marcó ${person.al_dia_by || "un usuario eliminado"}, ${fullDate(person.al_dia_at)}` : "";
    byId("al-dia-toggle").textContent = person.al_dia ? "Marcar que no está al día" : "Marcar al día";
  }

  renderCharges(charges) {
    byId("charges").hidden = false;
    byId("charges-empty").hidden = charges.length > 0;
    byId("charges-table").hidden = charges.length === 0;
    const rows = byId("charges-rows");
    rows.replaceChildren();
    for (const charge of charges) {
      const row = rows.insertRow();
      const status = charge.status === "simulated" ? "Simulado" : charge.status;
      const cells = [fullDate(charge.created_at), `${charge.currency} ${charge.amount}`, charge.titular_name, charge.from_phone, status, charge.operator_message];
      cells.forEach((text, i) => {
        const cell = row.insertCell();
        cell.textContent = text;
        if (i === 1 || i === 3) cell.className = "mono";
      });
    }
  }

  async load() {
    this.clearMessages();
    const result = await api("GET", `/panel/api/persons/${this.personId}`);
    if (result.status !== 200) {
      show(byId("error"), errorText(result));
      return;
    }
    this.fill(result.data);
  }

  collect() {
    const data = structuredClone(this.baseline);
    const seen = new Set();
    for (const el of controls(this.form)) {
      if (seen.has(el.name)) continue;
      seen.add(el.name);
      const value = readControl(this.form, el);
      if (isEmpty(value)) deletePath(data, el.name);
      else setPath(data, el.name, value);
    }
    return prune(data);
  }

  clearMessages() {
    for (const el of this.form.querySelectorAll(".field-error, .field-warning")) el.remove();
    for (const el of this.form.querySelectorAll(".invalid")) el.classList.remove("invalid");
    show(byId("error"), "");
    show(byId("form-errors"), "");
    show(byId("saved"), "");
    byId("form-warnings").replaceChildren();
    byId("form-warnings").hidden = true;
  }

  fieldNote(field, message, className) {
    const el = controls(this.form).find((control) => control.name === field);
    if (!el) return false;
    const note = document.createElement("span");
    note.className = className;
    note.textContent = message;
    (el.closest("label") || el).after(note);
    const details = el.closest("details");
    if (details) details.open = true;
    return el;
  }

  showErrors(result) {
    const detail = result.data && result.data.detail;
    show(byId("form-errors"), errorText(result));
    if (!detail || !Array.isArray(detail.fields)) return;
    let first = null;
    const orphan = [];
    for (const { field, message } of detail.fields) {
      const el = this.fieldNote(field, message, "field-error");
      if (el) {
        el.classList.add("invalid");
        first ??= el;
      } else {
        orphan.push(`${field}: ${message}`);
      }
    }
    if (orphan.length) show(byId("form-errors"), `${errorText(result)}. ${orphan.join(". ")}`);
    (first || byId("form-errors")).focus?.();
  }

  showWarnings(warnings) {
    const box = byId("form-warnings");
    for (const { field, message } of warnings) {
      if (!this.fieldNote(field, message, "field-warning")) {
        const item = document.createElement("li");
        item.textContent = message;
        box.append(item);
        box.hidden = false;
      }
    }
  }

  async save() {
    this.clearMessages();
    const isNew = !this.personId;
    const data = this.collect();
    const result = isNew
      ? await api("POST", "/panel/api/persons", { data })
      : await api("PUT", `/panel/api/persons/${this.personId}`, { data, version: this.version });
    if (result.status === 200 || result.status === 201) {
      this.fill(result.data);
      if (isNew) history.replaceState(null, "", `/personas/${result.data.id}`);
      show(byId("saved"), "Ficha guardada.");
      this.showWarnings(result.data.warnings);
      return;
    }
    if (result.status === 409 && !isNew) {
      show(byId("form-errors"), `${errorText(result)}. Tus cambios no se guardaron: siguen en pantalla para que los compares.`);
      byId("reload").hidden = false;
      return;
    }
    this.showErrors(result);
  }

  async toggleAlDia() {
    show(byId("error"), "");
    const result = await api("PUT", `/panel/api/persons/${this.personId}/al-dia`, { al_dia: !this.alDia });
    if (result.status === 200) this.renderAlDia(result.data);
    else show(byId("error"), errorText(result));
  }

  async remove() {
    if (!window.confirm("¿Dar de baja esta ficha? Deja de verse en el panel y de identificar llamadas.")) return;
    const result = await api("DELETE", `/panel/api/persons/${this.personId}`);
    if (result.status === 204) location.assign("/personas");
    else show(byId("error"), errorText(result));
  }
}

// --- Listado ---

function listPage() {
  const form = byId("filters");
  const state = { page: 1 };
  const initial = new URLSearchParams(location.search);
  form.elements.q.value = initial.get("q") || "";
  form.elements.al_dia.value = initial.get("al_dia") || "";
  state.page = Math.max(Number(initial.get("page")) || 1, 1);

  function emptyState(filtered) {
    const box = byId("empty");
    box.replaceChildren();
    const title = document.createElement("p");
    title.textContent = filtered ? "No hay fichas con esa búsqueda." : "Todavía no hay fichas.";
    box.append(title);
    if (!filtered) {
      const add = document.createElement("a");
      add.className = "button";
      add.href = "/personas/nueva";
      add.textContent = "Cargar la primera ficha";
      box.append(add);
    }
    box.hidden = false;
  }

  async function load() {
    const params = new URLSearchParams();
    const q = form.elements.q.value.trim();
    const alDia = form.elements.al_dia.value;
    if (q) params.set("q", q);
    if (alDia) params.set("al_dia", alDia);
    if (state.page > 1) params.set("page", state.page);
    const query = params.toString();
    history.replaceState(null, "", query ? `/personas?${query}` : "/personas");
    show(byId("error"), "");
    const result = await api("GET", `/panel/api/persons${query ? `?${query}` : ""}`);
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
    byId("empty").hidden = true;
    byId("results").hidden = items.length === 0;
    if (items.length === 0) emptyState(Boolean(q || alDia));
    const rows = byId("rows");
    rows.replaceChildren();
    for (const item of items) {
      const row = rows.insertRow();
      const link = document.createElement("a");
      link.href = `/personas/${item.id}`;
      link.textContent = item.name;
      row.insertCell().append(link);
      row.insertCell().textContent = item.titular_name;
      const badge = document.createElement("span");
      badge.className = `badge ${item.al_dia ? "ok" : "warn"}`;
      badge.textContent = item.al_dia ? "Al día" : "No está al día";
      row.insertCell().append(badge);
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

// --- Login ---

function loginPage() {
  const form = byId("login");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    show(byId("error"), "");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const result = await api("POST", "/auth/login", {
      tenant: form.elements.tenant.value.trim(),
      email: form.elements.email.value,
      password: form.elements.password.value,
    });
    button.disabled = false;
    if (result.status === 200) {
      location.assign(form.dataset.next); // el servidor ya la validó
      return;
    }
    show(byId("error"), result.status === 422 ? "Completá los tres datos." : errorText(result));
  });
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
  login: loginPage,
  list: listPage,
  person: () => new PersonPage(),
})[document.body.dataset.page]?.();
