// Sandbox de las herramientas de codigo (docs/features/HERRAMIENTAS.md). POST /run con Bearer TOOLS_RUNNER_TOKEN:
// corre la funcion en un proceso Deno nuevo (runner.js), sin permisos salvo la red a allowed_hosts, con
// tope de memoria y de tiempo. Solo en la red interna atentina-tools; la salida a internet es por el proxy
// de egress (Smokescreen), que niega IPs privadas.
const TOKEN = Deno.env.get("TOOLS_RUNNER_TOKEN") ?? "";
const CONCURRENCY = Number(Deno.env.get("TOOLS_RUNNER_CONCURRENCY") ?? "8");
const PROXY = Deno.env.get("TOOLS_EGRESS_PROXY") ?? "";
const MAX_CODE = 20_000;
const MAX_TIMEOUT = 30_000;
const MAX_OUTPUT = 2_000_000;
const HOST_RE = /^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+(:\d{1,5})?$/;
const RUNNER = new URL("./runner.js", import.meta.url).pathname;

let running = 0;
const waiting: (() => void)[] = [];

async function acquire(deadline: number): Promise<boolean> {
  if (running < CONCURRENCY) {
    running++;
    return true;
  }
  return await new Promise((resolve) => {
    const wake = () => { clearTimeout(timer); running++; resolve(true); };
    const timer = setTimeout(() => {
      const i = waiting.indexOf(wake);
      if (i >= 0) waiting.splice(i, 1);
      resolve(false);
    }, Math.max(deadline - Date.now(), 0));
    waiting.push(wake);
  });
}

function release() {
  running--;
  waiting.shift()?.();
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

async function run(body: Record<string, unknown>): Promise<Record<string, unknown>> {
  const timeout = Math.min(Number(body.timeout_ms ?? 5000), MAX_TIMEOUT);
  const hosts = (body.allowed_hosts as string[] ?? []).filter((h) => HOST_RE.test(h));
  const marker = `@@atentina-${crypto.randomUUID()}@@`;
  const args = ["run", "--quiet", "--no-prompt", "--no-config", "--no-lock", "--no-npm", "--no-remote",
    "--v8-flags=--max-old-space-size=64"];
  if (hosts.length) args.push(`--allow-net=${hosts.join(",")}`);
  args.push(RUNNER);
  const env: Record<string, string> = { NO_COLOR: "1", DENO_DIR: "/tmp/deno", HOME: "/tmp", DENO_NO_UPDATE_CHECK: "1" };
  if (PROXY) Object.assign(env, { HTTPS_PROXY: PROXY, HTTP_PROXY: PROXY });
  const child = new Deno.Command(Deno.execPath(), {
    args, env, clearEnv: true, stdin: "piped", stdout: "piped", stderr: "piped", cwd: "/tmp",
  }).spawn();
  const writer = child.stdin.getWriter();
  await writer.write(new TextEncoder().encode(JSON.stringify({
    marker, code: body.code, args: body.args, secrets: body.secrets, call: body.call, vars: body.vars,
  })));
  await writer.close();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; try { child.kill("SIGKILL"); } catch { /* ya termino */ } },
    timeout);
  const started = performance.now();
  const output = await child.output().catch(() => null);
  clearTimeout(timer);
  const ms = Math.round(performance.now() - started);
  if (timedOut) return { ok: false, error: `se pasó del tiempo (${timeout} ms)`, logs: [], ms };
  const stdout = new TextDecoder().decode(output?.stdout.slice(0, MAX_OUTPUT) ?? new Uint8Array());
  const line = stdout.split("\n").reverse().find((l) => l.startsWith(marker));
  if (!line) {
    const stderr = new TextDecoder().decode(output?.stderr ?? new Uint8Array());
    const memory = /heap limit|out of memory|allocation failed/i.test(stderr);
    const detail = stderr.split("\n").find((l) => /error/i.test(l))?.slice(0, 300) ?? "";
    return { ok: false, error: memory ? "se quedó sin memoria (64 MB)" : `la función terminó sin resultado ${detail}`.trim(),
      logs: [], ms };
  }
  return { ...JSON.parse(line.slice(marker.length)), ms };
}

Deno.serve({ hostname: "0.0.0.0", port: 8080 }, async (req) => {
  const path = new URL(req.url).pathname;
  if (path === "/health") return json({ ok: true, running });
  if (path !== "/run" || req.method !== "POST") return json({ error: "not found" }, 404);
  if (!TOKEN || req.headers.get("authorization") !== `Bearer ${TOKEN}`) return json({ error: "unauthorized" }, 401);
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "JSON invalido" }, 400);
  }
  if (typeof body.code !== "string" || body.code.length > MAX_CODE) return json({ error: "code invalido" }, 400);
  const timeout = Math.min(Number(body.timeout_ms ?? 5000), MAX_TIMEOUT);
  if (!(await acquire(Date.now() + timeout))) return json({ ok: false, error: "sandbox ocupado", logs: [] });
  try {
    return json(await run(body));
  } finally {
    release();
  }
});
