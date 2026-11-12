import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn } from "../../../src/comun/ui";
import { NAR, NAR_SOFT, Pie } from "./escenas";
import { AT } from "./timeline";

// "Dónde podríamos mejorar con Atentina" (PDF, página 2): cada tarjeta entra con su frase; "Con Atentina" se suma ~1,1 s después.
// a4a dice "Dónde podríamos mejorar." y "Hoy atienden..." arranca a ~1,85 s.
const M = { horas: AT.a4a + 1.85, canales: AT.a4b + 0.1, cotiza: AT.a4c + 0.1, reclamos: AT.a4d + 0.1 };
const LUEGO = 1.1;

const Tarjeta: React.FC<{ x: number; y: number; p: number; q: number; titulo: string; con: string; children: React.ReactNode }> = ({
  x, y, p, q, titulo, con, children,
}) => (
  <div style={{
    position: "absolute", left: x, top: y, width: 825, height: 345, boxSizing: "border-box", overflow: "hidden",
    background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${NAR}`, borderRadius: 24, boxShadow: shadowCard,
    opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
  }}>
    <div style={{ padding: "22px 34px 0" }}>
      <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: NAR }}>HOY</div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.01em", marginTop: 4, whiteSpace: "nowrap" }}>{titulo}</div>
      <div style={{ height: 128, marginTop: 14, position: "relative" }}>{children}</div>
    </div>
    <div style={{
      position: "absolute", left: 0, right: 0, bottom: 0, height: 76, boxSizing: "border-box", padding: "0 34px", display: "flex", alignItems: "center", gap: 18,
      background: C.accentSoft, borderTop: "2px solid #c9d7ff", opacity: q, transform: `translateY(${(1 - q) * 20}px)`,
    }}>
      <span style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent, whiteSpace: "nowrap" }}>CON ATENTINA</span>
      <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, color: C.accent2, whiteSpace: "nowrap" }}>{con}</span>
    </div>
  </div>
);

const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
// Horario publicado (sitio y Google Maps, los cuatro locales): lu a vie 8–13 y 14–18; sábado y domingo cerrado
const ABIERTO: [number, number][][] = [...Array(5).fill([[8, 13], [14, 18]]), [], []];
// Canales publicados (comercial/demos/experto.md, 1): WhatsApp central, 4 teléfonos de sucursal con WhatsApp, 0800, mail y formulario
const CANALES = ["WhatsApp central", "Punilla", "Carlos Paz", "Zona Sur", "Rivadavia", "0800", "Mail", "Formulario"];

const Sobre: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg viewBox="0 0 24 24" width={size} height={size}>
    <rect x="3" y="5.5" width="18" height="13" rx="2" fill="none" stroke={color} strokeWidth={2} />
    <path d="M3.5 7l8.5 6 8.5-6" fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
  </svg>
);

/** 2. Dónde podríamos mejorar: cuatro hechos que cualquier cliente ve hoy, cada uno con lo que cambia con Atentina. */
export const Mejorar: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const p = [useIn(M.horas, 0.6), useIn(M.canales, 0.6), useIn(M.cotiza, 0.6), useIn(M.reclamos, 0.6)];
  const q = [useIn(M.horas + 2.2, 0.5), useIn(M.canales + LUEGO, 0.5), useIn(M.cotiza + LUEGO, 0.5), useIn(M.reclamos + LUEGO + 0.6, 0.5)];
  const semana = interpolate(t, [M.horas + 0.2, M.horas + 1.6], [0, 1], CLAMP);
  const horas = Math.round(45 * semana);
  const chips = CANALES.map((_, i) => interpolate(t, [M.canales + 0.15 + i * 0.09, M.canales + 0.45 + i * 0.09], [0, 1], CLAMP));
  const flecha = interpolate(t, [M.canales + 0.9, M.canales + 1.3], [0, 1], CLAMP);
  const productos = Math.round(interpolate(t, [M.cotiza + 0.2, M.cotiza + 1.4], [0, 331], { ...CLAMP, easing: EASE }));
  const mail = interpolate(t, [M.reclamos + 0.3, M.reclamos + 1.3], [0, 1], { ...CLAMP, easing: EASE });
  const espera = interpolate(t, [M.reclamos + 1.4, M.reclamos + 2.0], [0, 1], CLAMP);
  const W = 460;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde podríamos mejorar con Atentina" text="Lo que hoy pasa por un asesor," accent="puede llegarle listo." size={60} />

      <Tarjeta x={120} y={250} p={p[0]} q={q[0]} titulo="45 de 168 horas con atención" con="Las 168 horas, atendidas">
        <div style={{ position: "relative" }}>
          {DIAS.map((d, i) => (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 10, height: 17, marginBottom: 1 }}>
              <span style={{ width: 30, fontFamily: F.mono, fontSize: 13, color: C.muted }}>{d}</span>
              <div style={{ position: "relative", width: W, height: 13, borderRadius: 4, background: C.surface2, overflow: "hidden" }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: 13, width: W * semana, background: "#f6c9ad" }} />
                {ABIERTO[i].map(([a, b]) => (
                  <div key={a} style={{ position: "absolute", left: (a / 24) * W, width: ((b - a) / 24) * W, top: 0, height: 13, background: C.ok, opacity: semana > 0 ? 1 : 0 }} />
                ))}
              </div>
            </div>
          ))}
          <div style={{ position: "absolute", left: 520, top: 4, whiteSpace: "nowrap" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, color: C.ok, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{horas} hs</div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 8 }}>de las 168 de la semana</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 8 }}>
              <span style={{ width: 13, height: 13, borderRadius: 3, background: C.ok }} />abierto
              <span style={{ width: 13, height: 13, borderRadius: 3, background: "#f6c9ad", marginLeft: 8 }} />cerrado
            </div>
          </div>
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={250} p={p[1]} q={q[1]} titulo="Muchos canales, un asesor" con="Clasifica y deriva solo">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 7, width: 470 }}>
          {CANALES.map((c, i) => (
            <div key={c} style={{
              display: "flex", alignItems: "center", gap: 6, borderRadius: 999, padding: "5px 12px", background: C.surface2,
              fontFamily: F.body, fontWeight: 600, fontSize: 18, color: C.ink2, opacity: chips[i], transform: `translateX(${(1 - chips[i]) * -16}px)`,
            }}>
              {i < 5 ? <Icon name="wa" size={18} color={C.wa} /> : i === 5 ? <Icon name="phone" size={18} color={C.accent} /> : i === 6 ? <Sobre size={18} color={C.ink2} /> : <Icon name="web" size={18} color={C.accent} />}
              {c}
            </div>
          ))}
        </div>
        <svg width={70} height={40} style={{ position: "absolute", left: 485, top: 40 }}>
          <path d="M4 20 H56 M44 8 L60 20 L44 32" stroke={NAR} strokeWidth={4} fill="none" strokeLinecap="round" opacity={flecha} />
        </svg>
        <div style={{
          position: "absolute", left: 565, top: 22, display: "flex", alignItems: "center", gap: 10, borderRadius: 16, padding: "14px 18px",
          background: NAR_SOFT, border: `2px solid ${NAR}`, opacity: flecha,
        }}>
          <Icon name="users" size={28} color={NAR} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, whiteSpace: "nowrap" }}>Un asesor,<br />a mano</span>
        </div>
      </Tarjeta>

      <Tarjeta x={120} y={625} p={p[2]} q={q[2]} titulo="Cada cotización se arma a mano" con="La cotización llega completa">
        <div style={{ display: "flex", gap: 14 }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ width: 152, height: 124, borderRadius: 14, border: `2px solid ${C.line}`, background: C.bg2, padding: 10, boxSizing: "border-box" }}>
              <div style={{ height: 44, borderRadius: 8, background: C.surface2, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 84, height: 20, borderRadius: 5, border: `2px solid ${C.line2}`, background: "#fff" }} />
              </div>
              <div style={{ height: 8, width: 90, borderRadius: 4, background: C.line, marginTop: 9 }} />
              <div style={{ marginTop: 10, borderRadius: 8, background: C.ink2, color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 13, textAlign: "center", padding: "5px 0", whiteSpace: "nowrap" }}>
                Agregar a cotización
              </div>
            </div>
          ))}
          <div style={{ marginLeft: 16, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, color: NAR, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{productos}</div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 6 }}>productos, sin precio:</div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted }}>todos pasan por un asesor</div>
          </div>
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={625} p={p[3]} q={q[3]} titulo="Reclamos que van por mail" con="Cada reclamo con dueño y fecha">
        <div style={{ position: "relative", height: 128 }}>
          <div style={{
            position: "absolute", left: 0, top: 18, width: 210, borderRadius: 14, border: `2px solid ${C.line}`, background: C.bg2, padding: "12px 14px", boxSizing: "border-box",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.body, fontWeight: 700, fontSize: 19, color: C.ink }}>
              <Sobre size={24} color={C.ink2} />Reclamo
            </div>
            <div style={{ fontFamily: F.body, fontSize: 16, color: C.ink2, marginTop: 6, lineHeight: 1.3 }}>pedido, motivo y fotos</div>
          </div>
          <div style={{ position: "absolute", left: 230, top: 48, width: 200 * mail, height: 4, borderRadius: 2, background: C.line2 }} />
          <div style={{
            position: "absolute", left: 230 + 200 * mail - 18, top: 32, opacity: mail > 0.02 && mail < 0.98 ? 1 : 0,
          }}>
            <Sobre size={36} color={NAR} />
          </div>
          <div style={{
            position: "absolute", left: 450, top: 18, width: 240, borderRadius: 14, border: `2px solid ${NAR}`, background: NAR_SOFT, padding: "12px 16px", boxSizing: "border-box",
            opacity: Math.min(1, mail * 1.2),
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 19, color: C.ink }}>ventas@</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.body, fontSize: 17, color: NAR, marginTop: 6, opacity: espera, fontWeight: 600 }}>
              <Icon name="clock" size={20} color={NAR} />espera que alguien lo retome
            </div>
          </div>
        </div>
      </Tarjeta>

      <Pie seccion="2 / 4" fuente="Fuentes: experto.com.ar y sus fichas de Google Maps, leídos el 11-nov-2026." />
    </AbsoluteFill>
  );
};
