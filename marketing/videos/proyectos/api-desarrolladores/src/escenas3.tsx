import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { CodeWindow, Ok } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, useIn, usePop } from "../../../src/comun/ui";
import { CALL_DETAIL, CAMPAIGN, PY_USO, VERIFY } from "./datos";
import { Code, Nota, PlanBadge, useT } from "./piezas";

const Pop: React.FC<{ at: number; style: React.CSSProperties; origin?: string; children: React.ReactNode }> = ({ at, style, origin = "50% 0%", children }) => {
  const p = usePop(at);
  return <div style={{ position: "absolute", transform: `scale(${p})`, transformOrigin: origin, opacity: Math.min(1, p * 1.4), ...style }}>{children}</div>;
};

const LEAD = [
  ["Contacto", "Martín"],
  ["Empresa", "Empresa Ejemplo"],
  ["Resultado", "Interesado sin reunión"],
  ["Duración", "95 s"],
];

/** 7. GET /calls/{id}: estado, resultado y datos; y cómo los usa la app del integrador. */
export const Resultado: React.FC = () => {
  const rows = LEAD.map((_, i) => useIn(7.6 + i * 0.3, 0.3));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Demo 5 · Resultado" text="Estado, resultado y datos," accent="en un GET." />
      <Pop at={0.2} style={{ left: 100, top: 250, width: 1000 }}>
        <CodeWindow tab="curl" method="GET" path="/api/v1/calls/{conversation_id}" status={<Ok>200 OK</Ok>} fontSize={19}>
          <Code text={CALL_DETAIL} at={0.4} stagger={0.03}
            hl={[{ a: 1.6, b: 3.4, lines: [5, 9] }, { a: 3.4, b: 5.0, lines: [6, 7] }, { a: 5.0, b: 7.0, lines: [10, 11, 12, 13, 14] }]} />
        </CodeWindow>
        <Nota p={useIn(1.0)} style={{ marginTop: 8 }}>Llamada real del 20-oct-2026 · nombre, empresa y teléfono anonimizados</Nota>
      </Pop>
      <Pop at={5.8} style={{ left: 1140, top: 260, width: 690 }}>
        <CodeWindow tab="tu_app.py" fontSize={17}>
          <Code text={PY_USO} at={5.9} />
        </CodeWindow>
      </Pop>
      <Pop at={7.3} style={{ left: 1140, top: 520, width: 690 }}>
        <Card style={{ padding: "20px 26px", borderColor: C.accent }}>
          <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent, marginBottom: 8 }}>TU SISTEMA · NUEVO LEAD</div>
          {LEAD.map(([k, v], i) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderTop: `2px solid ${C.line}`, opacity: rows[i] }}>
              <span style={{ fontFamily: F.body, fontSize: 24, color: C.muted }}>{k}</span>
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink }}>{v}</span>
            </div>
          ))}
        </Card>
        <Nota p={useIn(8.4)} style={{ marginTop: 8 }}>crm.guardar y esta pantalla: ilustrativos, tu código</Nota>
      </Pop>
    </AbsoluteFill>
  );
};

/** 8. Webhook de las campañas, con firma. */
export const Webhook: React.FC = () => {
  const t = useT();
  const x = interpolate(t, [2.6, 4.4], [0, 1], { ...CLAMP, easing: EASE });
  const pk = interpolate(t, [2.4, 2.7], [0, 1], CLAMP);
  const lane = useIn(2.0, 0.5);
  const llega = t > 4.4;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Webhook" text="En las campañas," accent="el resultado te llega solo." />
      <Pop at={0.2} style={{ left: 100, top: 250, width: 840 }}>
        <CodeWindow tab="crear la campaña" method="POST" path="/api/v1/campaigns" fontSize={18}>
          <Code text={CAMPAIGN} at={0.3} hl={[{ a: 1.4, b: 4.6, lines: [5, 6] }]} />
        </CodeWindow>
      </Pop>
      <Pop at={4.4} style={{ left: 1000, top: 250, width: 820 }}>
        <CodeWindow tab="tu webhook: verificar la firma" fontSize={18}>
          <Code text={VERIFY} at={4.5} />
        </CodeWindow>
      </Pop>
      {/* El POST que viaja de Atentina a tu sistema */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, opacity: lane }}>
        <path d="M330 690 H1460" stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeDashoffset={-t * 60} strokeLinecap="round" />
      </svg>
      <div style={{ position: "absolute", left: 100, top: 650, opacity: lane, background: C.ink, color: "#fff", borderRadius: 16, padding: "18px 24px",
        fontFamily: F.display, fontWeight: 800, fontSize: 28 }}>Atentina</div>
      <div style={{ position: "absolute", left: 1470, top: 650, opacity: lane, background: "#fff", border: `2px solid ${llega ? C.accent : C.line2}`, borderRadius: 16,
        padding: "12px 20px", fontFamily: F.mono, fontSize: 19, color: C.ink, boxShadow: shadowCard }}>
        tu-sistema.com.ar<br /><span style={{ color: llega ? C.ok : C.muted }}>{llega ? "200 OK · recibido" : "/atentina/webhook"}</span>
      </div>
      <div style={{ position: "absolute", left: 360 + x * 640, top: 640, opacity: pk }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 14, padding: "10px 18px", fontFamily: F.mono, fontSize: 20, boxShadow: "0 12px 30px rgba(36,86,230,.35)" }}>
          POST contact.finished<br />
          <span style={{ color: "#dbe5ff" }}>X-Atentina-Signature: sha256=…</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 100, top: 820, opacity: useIn(5.2) }}>
        <PlanBadge>Campañas de llamadas: Sucursal y Red</PlanBadge>
      </div>
      <Nota p={useIn(5.8)} style={{ position: "absolute", left: 100, top: 885 }}>
        Llamadas sueltas: GET /api/v1/events?after_id=… (call.ended, handoff.*)
      </Nota>
    </AbsoluteFill>
  );
};

/** 9. Cierre oscuro: TL;DR y la documentación. */
export const Cierre: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.6, 0.7);
  const steps = [usePop(2.0), usePop(2.6), usePop(3.2)];
  const url = useIn(5.2, 0.6);
  const STEPS = [
    ["1", "Panel › API › Nueva API key"],
    ["2", "base_url + Bearer vaas_…"],
    ["3", "POST /calls → GET /calls/{id}"],
  ];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 380 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 255, textAlign: "center", fontFamily: F.mono, fontSize: 24, letterSpacing: "0.1em", color: C.accentOnDark, opacity: title }}>
        TL;DR
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 300, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 70, lineHeight: 1.08,
        color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em" }}>
        Una API key y pocas líneas:<br /><span style={{ color: C.accentOnDark }}>agentes, telefonía y voz.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 520, display: "flex", justifyContent: "center", gap: 22 }}>
        {STEPS.map(([n, s], i) => (
          <div key={n} style={{ display: "flex", alignItems: "center", gap: 14, background: "#16213a", border: "2px solid #23304d", borderRadius: 18, padding: "16px 24px",
            transform: `scale(${steps[i]})`, opacity: Math.min(1, steps[i] * 1.4) }}>
            <span style={{ width: 40, height: 40, borderRadius: 20, background: C.accent, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.display, fontWeight: 800, fontSize: 24 }}>{n}</span>
            <span style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaInk }}>{s}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 680, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 16}px)` }}>
        <div style={{ background: "#fff", color: C.ink, borderRadius: 999, padding: "16px 34px", fontFamily: F.mono, fontSize: 34 }}>
          atentina.com.ar<span style={{ color: C.accent }}>/desarrolladores/docs/api</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 780, textAlign: "center", fontFamily: F.body, fontSize: 26, color: C.ctaMuted, opacity: useIn(6.0) }}>
        También, MCP para agentes de IA: /desarrolladores/docs/mcp
      </div>
    </AbsoluteFill>
  );
};
