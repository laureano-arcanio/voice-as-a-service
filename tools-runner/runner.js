// Corre UNA funcion del cliente (docs/TOOLS_PLAN.md, 5). Proceso Deno nuevo por ejecucion, sin permisos
// salvo --allow-net a los allowed_hosts de la herramienta (y la salida por el proxy de egress).
// Entrada por stdin: {marker, code, args, secrets, call, vars}. Salida: una linea "<marker><json>".
const MAX_RESPONSE = 1_000_000;
const MAX_LOGS = 200;

const input = JSON.parse(await new Response(Deno.stdin.readable).text());
const marker = input.marker;
const logs = [];
const fmt = (args) => args.map((x) => {
  if (typeof x === "string") return x;
  try { return JSON.stringify(x); } catch { return String(x); }
}).join(" ").slice(0, 2000);
for (const k of ["log", "info", "warn", "error", "debug"]) {
  console[k] = (...a) => { if (logs.length < MAX_LOGS) logs.push(fmt(a)); };
}

// fetch con tope de 1 MB por respuesta.
const realFetch = globalThis.fetch;
globalThis.fetch = async (...a) => {
  const res = await realFetch(...a);
  const reader = res.body?.getReader();
  const chunks = [];
  let size = 0;
  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > MAX_RESPONSE) {
      await reader.cancel();
      throw new Error(`la respuesta de ${res.url} pasa de 1 MB`);
    }
    chunks.push(value);
  }
  return new Response(chunks.length ? new Blob(chunks) : null,
    { status: res.status, statusText: res.statusText, headers: res.headers });
};

const write = Deno.stdout.writeSync.bind(Deno.stdout);
function out(obj) {
  write(new TextEncoder().encode("\n" + marker + JSON.stringify(obj) + "\n"));
}

try {
  const bytes = new TextEncoder().encode(input.code);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  const mod = await import("data:application/typescript;base64," + btoa(bin));
  if (typeof mod.default !== "function") throw new Error("el módulo no exporta una función default");
  const result = await mod.default({
    args: input.args ?? {}, secrets: input.secrets ?? {}, call: input.call ?? {}, vars: input.vars ?? {},
  });
  const json = JSON.stringify(result === undefined ? null : result);
  out({ ok: true, result: JSON.parse(json), logs });
} catch (e) {
  out({ ok: false, error: String(e?.message ?? e).slice(0, 1000), logs });
}
Deno.exit(0);
