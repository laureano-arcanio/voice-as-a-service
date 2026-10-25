import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";

/**
 * Terminal con Claude Code, simulada: el formato de texto de la sesión (prompt `>`, llamadas a herramientas MCP
 * `● atentina - <tool> (MCP)(args)` con su resultado `⎿`, respuestas con `●`), sin el logo ni los colores de
 * marca de Claude Code (docs/VIDEOS.md: nada de interfaces de terceros imitadas). La ventana es la de la marca.
 */

const DIM = "#8b97ad";
const TXT = "#e8ecf4";
const GREEN = "#5ee49a";
const YELLOW = "#ffd88a";
const FS = 23;
const LH = 1.45;

export type Item =
  | { k: "cmd"; at: number; dur: number; text: string }
  | { k: "out"; at: number; lines: string[]; color?: string }
  | { k: "user"; at: number; dur: number; text: string }
  | { k: "tool"; at: number; name: string; args?: string; done: number; result: string[]; more?: number; hl?: [number, number] }
  | { k: "say"; at: number; text: string; dur?: number }
  | { k: "node"; at: number; until?: number; node: React.ReactNode };

/** Segundo actual dentro de la escena. */
export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

const Prompt: React.FC = () => <span style={{ color: GREEN }}>~/mi-proyecto $ </span>;

const Cursor: React.FC<{ t: number }> = ({ t }) => (
  <span style={{ display: "inline-block", width: 12, height: FS * 1.05, background: TXT, verticalAlign: "text-bottom", opacity: Math.floor(t * 2.2) % 2 ? 0.15 : 0.9 }} />
);

const typed = (text: string, t: number, a: number, dur: number) =>
  text.slice(0, Math.floor(interpolate(t, [a, a + dur], [0, text.length], CLAMP)));

/** Una línea de resultado JSON coloreada (claves, textos y números), en gris como los resultados de Claude Code. */
const Json: React.FC<{ line: string }> = ({ line }) => {
  const parts: React.ReactNode[] = [];
  const re = /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null|\d[\d.]*)\b/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) parts.push(<span key={i++}>{line.slice(last, m.index)}</span>);
    if (m[1]) parts.push(<span key={i++} style={{ color: m[2] ? "#a9bdf5" : "#e3cf9c" }}>{m[1]}{m[2] ?? ""}</span>);
    else parts.push(<span key={i++} style={{ color: "#9fe3bd" }}>{m[3]}</span>);
    last = re.lastIndex;
  }
  if (last < line.length) parts.push(<span key={i++}>{line.slice(last)}</span>);
  return <>{parts}</>;
};

const Row: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", ...style }}>{children}</div>
);

const ToolBlock: React.FC<{ it: Extract<Item, { k: "tool" }>; t: number }> = ({ it, t }) => {
  const running = t < it.done;
  const hl = it.hl ? interpolate(t, [it.hl[0], it.hl[0] + 0.25, it.hl[1] - 0.25, it.hl[1]], [0, 1, 1, 0], CLAMP) : 0;
  const shown = running ? 0 : Math.min(it.result.length, Math.floor((t - it.done) / 0.05) + 1);
  return (
    <div style={{ marginTop: 14 }}>
      <Row style={{
        background: `rgba(36,86,230,${0.32 * hl})`, boxShadow: hl ? `inset 4px 0 0 rgba(157,182,255,${hl})` : undefined,
        borderRadius: 6, margin: "0 -10px", padding: "0 10px",
      }}>
        <span style={{ color: running ? TXT : GREEN, opacity: running ? (Math.floor(t * 3) % 2 ? 0.25 : 1) : 1 }}>● </span>
        <span style={{ color: TXT, fontWeight: 600 }}>atentina - {it.name} (MCP)</span>
        {it.args !== undefined ? <span style={{ color: DIM }}>({it.args})</span> : null}
      </Row>
      {running ? <Row style={{ color: DIM }}>{"  ⎿  Running…"}</Row> : null}
      {it.result.slice(0, shown).map((l, i) => (
        <Row key={i} style={{ color: DIM }}>{i === 0 ? "  ⎿  " : "     "}<Json line={l} /></Row>
      ))}
      {!running && it.more && shown >= it.result.length ? (
        <Row style={{ color: DIM }}>{`     … +${it.more} lines (ctrl+o to expand)`}</Row>
      ) : null}
    </div>
  );
};

/** Contenido de la terminal: los ítems visibles hasta `t`; lo nuevo empuja lo viejo hacia arriba. */
const History: React.FC<{ items: Item[]; t: number }> = ({ items, t }) => (
  <>
    {items.filter((it) => t >= it.at && !(it.k === "node" && it.until !== undefined && t >= it.until)).map((it, i) => {
      if (it.k === "cmd") {
        const done = t >= it.at + it.dur;
        return <Row key={i} style={{ color: TXT, marginTop: i ? 10 : 0 }}><Prompt />{typed(it.text, t, it.at, it.dur)}{done ? null : <Cursor t={t} />}</Row>;
      }
      if (it.k === "out") return <div key={i}>{it.lines.map((l, j) => <Row key={j} style={{ color: it.color ?? DIM }}>{l || " "}</Row>)}</div>;
      if (it.k === "user") {
        if (t < it.at + it.dur + 0.3) return null; // todavía se escribe en la caja de abajo
        return <Row key={i} style={{ color: TXT, background: "#1a2438", borderRadius: 6, margin: "8px -10px 0", padding: "4px 10px" }}><span style={{ color: DIM }}>{"> "}</span>{it.text}</Row>;
      }
      if (it.k === "tool") return <ToolBlock key={i} it={it} t={t} />;
      if (it.k === "say") {
        const n = Math.floor(interpolate(t, [it.at, it.at + (it.dur ?? 0.9)], [0, it.text.length], CLAMP));
        return <Row key={i} style={{ color: TXT, marginTop: 14 }}><span style={{ color: TXT }}>● </span>{it.text.slice(0, n)}</Row>;
      }
      return <div key={i}>{it.node}</div>;
    })}
  </>
);

/** La caja de entrada de Claude Code: lo que se está escribiendo (o vacía, con el cursor). */
const InputBox: React.FC<{ items: Item[]; t: number }> = ({ items, t }) => {
  const cur = items.filter((it): it is Extract<Item, { k: "user" }> => it.k === "user" && t >= it.at && t < it.at + it.dur + 0.3).pop();
  return (
    <div style={{ flexShrink: 0, marginTop: 16 }}>
      <div style={{ border: `2px solid #3a4763`, borderRadius: 10, padding: "8px 14px", color: TXT, minHeight: FS * LH }}>
        <span style={{ color: DIM }}>{"> "}</span>{cur ? typed(cur.text, t, cur.at, cur.dur) : null}<Cursor t={t} />
      </div>
      <div style={{ color: "#5d6a84", fontSize: 18, marginTop: 6, paddingLeft: 4 }}>? for shortcuts</div>
    </div>
  );
};

/** Movimiento de cámara: [segundo, escala, x, y] (x, y: punto de foco en px de la ventana). */
export type Cam = [number, number, number, number][];

export const Terminal: React.FC<{
  items: Item[]; claude?: boolean; title?: string; cam?: Cam; badge?: React.ReactNode;
  style?: React.CSSProperties; t?: number;
}> = ({ items, claude = true, title, cam, badge, style, t: tOverride }) => {
  const tNow = useT();
  const t = tOverride ?? tNow;
  let scale = 1, ox = 840, oy = 370;
  if (cam && cam.length) {
    const ts = cam.map((c) => c[0]);
    const opt = { ...CLAMP, easing: EASE };
    scale = interpolate(t, ts, cam.map((c) => c[1]), opt);
    ox = interpolate(t, ts, cam.map((c) => c[2]), opt);
    oy = interpolate(t, ts, cam.map((c) => c[3]), opt);
  }
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 196, height: 744, background: C.ink, borderRadius: 22, overflow: "hidden",
      boxShadow: "0 24px 60px rgba(11,18,32,.28)", display: "flex", flexDirection: "column", ...style,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 18px", background: "#151d2e", flexShrink: 0 }}>
        {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
        <div style={{ fontFamily: F.mono, fontSize: 18, color: C.ctaInk, marginLeft: 12, background: "#0b1220", borderRadius: 8, padding: "3px 12px" }}>
          {title ?? (claude ? "claude · ~/mi-proyecto" : "bash · ~/mi-proyecto")}
        </div>
        <div style={{ flex: 1 }} />
        {badge}
      </div>
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        <div style={{
          position: "absolute", inset: 0, padding: "18px 30px 14px", display: "flex", flexDirection: "column",
          fontFamily: F.mono, fontSize: FS, lineHeight: LH, transform: `scale(${scale})`, transformOrigin: `${ox}px ${oy}px`,
        }}>
          {/* Arriba mientras entra; cuando se llena, lo nuevo empuja lo viejo hacia arriba (como una terminal) */}
          <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
            <div style={{ minHeight: "100%", flexShrink: 0, display: "flex", flexDirection: "column" }}>
              <History items={items} t={t} />
              {claude ? <InputBox items={items} t={t} /> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const TERM = { DIM, TXT, GREEN, YELLOW };
