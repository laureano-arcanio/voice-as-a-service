import React from "react";
import { interpolate } from "remotion";
import { C, CLAMP, F } from "./theme";

const YELLOW = "#ffd88a";
const GREEN = "#5ee49a";

/** Colorea una línea: claves de JSON, textos, números y booleanos, y comentarios con #. */
export const CodeLine: React.FC<{ line: string; base?: string }> = ({ line, base = C.ctaMuted }) => {
  const parts: React.ReactNode[] = [];
  const re = /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null|\d+)\b|(#.*$)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) parts.push(<span key={k++} style={{ color: base }}>{line.slice(last, m.index)}</span>);
    if (m[1]) {
      parts.push(<span key={k++} style={{ color: m[2] ? C.accentOnDark : YELLOW }}>{m[1]}</span>);
      if (m[2]) parts.push(<span key={k++} style={{ color: C.ctaMuted }}>{m[2]}</span>);
    } else if (m[3]) parts.push(<span key={k++} style={{ color: GREEN }}>{m[3]}</span>);
    else parts.push(<span key={k++} style={{ color: "#7d8aa5", fontStyle: "italic" }}>{m[4]}</span>);
    last = re.lastIndex;
  }
  if (last < line.length) parts.push(<span key={k++} style={{ color: base }}>{line.slice(last)}</span>);
  return <div>{parts.length ? parts : " "}</div>;
};

/** Texto que se va escribiendo entre `a` y `b` (s). */
export const Typed: React.FC<{ text: string; a: number; b: number; t: number; base?: string }> = ({ text, a, b, t, base }) => {
  const n = Math.floor(interpolate(t, [a, b], [0, text.length], CLAMP));
  return <>{text.slice(0, n).split("\n").map((l, i) => <CodeLine key={i} line={l} base={base} />)}</>;
};

const METHOD: Record<string, [string, string]> = {
  GET: ["#1e3a2a", GREEN],
  POST: ["#1d2f63", C.accentOnDark],
  PUT: ["#3b2f14", YELLOW],
  PY: ["#2a2440", "#c4b5fd"],
};

/** Ventana oscura de código o de un pedido HTTP, con su barra de método y ruta. */
export const CodeWindow: React.FC<{
  tab: string; method?: string; path?: string; status?: React.ReactNode; fontSize?: number; children: React.ReactNode;
  style?: React.CSSProperties; minHeight?: number;
}> = ({ tab, method, path, status, fontSize = 21, children, style, minHeight }) => (
  <div style={{ background: C.ink, borderRadius: 24, overflow: "hidden", boxShadow: "0 24px 60px rgba(11,18,32,.25)", ...style }}>
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 18px", background: "#151d2e" }}>
      {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
      <div style={{ fontFamily: F.mono, fontSize: 18, color: C.ctaInk, marginLeft: 12, background: "#0b1220", borderRadius: 8, padding: "3px 12px" }}>{tab}</div>
    </div>
    {method ? (
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 20px", borderBottom: "2px solid #1e2940", fontFamily: F.mono, fontSize: 20 }}>
        <span style={{ background: METHOD[method][0], color: METHOD[method][1], borderRadius: 8, padding: "3px 10px" }}>{method}</span>
        <span style={{ color: C.ctaInk }}>{path}</span>
        <div style={{ flex: 1 }} />
        {status}
      </div>
    ) : null}
    <div style={{ padding: "16px 22px", fontFamily: F.mono, fontSize, lineHeight: 1.5, whiteSpace: "pre", minHeight }}>{children}</div>
  </div>
);

export const Ok: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: GREEN }}>{children}</span>;
