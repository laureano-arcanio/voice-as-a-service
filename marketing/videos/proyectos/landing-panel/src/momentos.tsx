import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, CLAMP, F } from "../../../src/comun/theme";
import {
  AppFrame, Badge, Boton, Camara, Campo, Cursor, ein, HEADER, PageTitle, Pestanas, presionDe, Retrato, RetratoId, SIDEBAR,
  BordeBlanco, Tarjeta, usePopAt, useT, WIN,
} from "./panel";

/**
 * Los cinco momentos del panel (tiempos locales, en segundos desde que entra cada uno), en una ventana angosta y
 * alta (el panel en una columna, como se ve en una pantalla chica) para el cuadro vertical 4:5. Los nombres de
 * pantallas, pestañas, campos y botones son los de web/src (README, "Afirmaciones y fuentes"). Datos ilustrativos.
 */

// Origen del contenido (a la derecha del menú, abajo del header) en coordenadas de la ventana
const OX = SIDEBAR;
const OY = HEADER;
const X0 = 36; // margen del contenido
const CW = WIN.w - SIDEBAR - 2 * X0; // ancho del contenido (728)
const abs = (x: number, y: number, w?: number, extra?: React.CSSProperties): React.CSSProperties => ({
  position: "absolute", left: x, top: y, width: w, boxSizing: "border-box", ...extra,
});
const popStyle = (p: number, origen = "50% 50%"): React.CSSProperties => ({
  opacity: Math.min(1, p * 1.6), transform: `scale(${0.85 + 0.15 * p})`, transformOrigin: origen,
});

const Fondo: React.FC = () => <AbsoluteFill style={{ background: C.bg }} />;
// Velo detrás de los modales: blanco suave (v4; el gris oscuro se veía como un bloque contra la página blanca)
const Velo: React.FC<{ o?: number }> = ({ o = 1 }) => (
  <div style={{ position: "absolute", left: -OX, top: -OY, width: WIN.w, height: WIN.h, background: "rgba(255,255,255,0.72)", opacity: o }} />
);

// ---------------------------------------------------------------- 1. Editor del agente: nombre, objetivo y voz

const TABS_AGENTE = ["Resumen", "Conversación", "Datos", "Herramientas", "Voz y canales", "Modelo"];
const VOCES: { id: RetratoId; nombre: string; genero: string }[] = [
  { id: "paula", nombre: "Paula", genero: "Mujer" },
  { id: "sofia", nombre: "Sofía", genero: "Mujer" },
  { id: "carolina", nombre: "Carolina", genero: "Mujer" },
  { id: "martin", nombre: "Martín", genero: "Hombre" },
  { id: "diego", nombre: "Diego", genero: "Hombre" },
  { id: "mateo", nombre: "Mateo", genero: "Hombre" },
];
const M1 = { clickTab: 1.45, cambio: 1.55, clickVoz: 2.45, clickPlay: 3.0 };
// Tarjetas de voz: 3 columnas x 2 filas (contenido)
const VC = { x: X0 + 28, y: 372, w: 214, h: 100, gx: 10, gy: 12 };
const vozPos = (i: number) => ({ x: VC.x + (i % 3) * (VC.w + VC.gx), y: VC.y + Math.floor(i / 3) * (VC.h + VC.gy) });
const PREV = { x: X0 + 28, y: 620 }; // la voz elegida y la prueba, debajo de la grilla
const PLAY = { x: PREV.x + 32, y: PREV.y + 300 };

const Onda: React.FC<{ n?: number; alto: number; color: string; vivo: number }> = ({ n = 30, alto, color, vivo }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, height: alto }}>
      {Array.from({ length: n }).map((_, i) => {
        const base = 0.25 + 0.35 * Math.abs(Math.sin(i * 1.7));
        const h = base + vivo * 0.5 * Math.abs(Math.sin(frame / 3.1 + i * 0.9));
        return <div key={i} style={{ width: 7, height: Math.min(1, h) * alto, borderRadius: 3.5, background: color }} />;
      })}
    </div>
  );
};

export const Momento1: React.FC = () => {
  const t = useT();
  const voz = t < M1.cambio;
  const elegida = t >= M1.clickVoz + 0.05 ? "sofia" : "paula";
  const pPreview = usePopAt(M1.clickVoz + 0.05);
  const progreso = interpolate(t, [M1.clickPlay + 0.1, M1.clickPlay + 1.6], [0, 1], CLAMP);
  const sonando = t > M1.clickPlay + 0.1;
  const pCambio = ein(t, M1.cambio, 0.3);
  const v = VOCES.find((x) => x.id === elegida)!;
  return (
    <AbsoluteFill>
      <Fondo />
      <Camara keys={[
        { t: 0, s: 1, x: 550, y: 700 },
        { t: 1.6, s: 1, x: 550, y: 700 },
        { t: 2.5, s: 1.08, x: 560, y: 690 },
        { t: 4.6, s: 1.08, x: 560, y: 690 },
      ]}>
        <AppFrame activo="agentes">
          <div style={abs(X0, 28)}>
            <PageTitle>Sofía</PageTitle>
          </div>
          <Pestanas items={TABS_AGENTE} activa={voz ? "Conversación" : "Voz y canales"} style={abs(X0, 108, CW)} />
          {voz ? (
            <>
              <Tarjeta titulo="Agente" desc="Quién es y cómo responde. El prompt se arma de estos campos." style={abs(X0, 190, CW)}>
                <div style={{ display: "flex", gap: 18 }}>
                  <Campo label="Nombre" valor="Sofía" t={t} escribe={[0.2, 0.55]} style={{ flex: 1 }} />
                  <Campo label="Idioma" valor="es-AR" style={{ width: 200 }} />
                </div>
                <Campo label="Rol" valor="atención al cliente de tu negocio" style={{ marginTop: 18 }} />
              </Tarjeta>
              <Tarjeta titulo="Objetivo y apertura" style={abs(X0, 580, CW)}>
                <Campo label="Objetivo" valor="Responder las consultas y dar turnos." t={t} escribe={[0.55, 1.15]} alto={84} />
              </Tarjeta>
            </>
          ) : (
            <div style={{ position: "absolute", inset: 0, opacity: pCambio, transform: `translateY(${(1 - pCambio) * 16}px)` }}>
              <Tarjeta titulo="Voz" desc="Con la que habla en las llamadas y las notas de voz. Elegila y escuchala acá mismo." style={abs(X0, 190, CW, { height: 880 })}>
                <div style={{ display: "flex", border: `2px solid ${C.line}`, borderRadius: 10, width: "fit-content", background: C.surface2, padding: 3 }}>
                  {["Todas (41)", "Mujeres (28)", "Hombres (13)"].map((s, i) => (
                    <div key={s} style={{
                      padding: "8px 16px", fontSize: 20, fontWeight: 600, borderRadius: 8, color: i === 0 ? C.ink : C.muted,
                      background: i === 0 ? "#fff" : "transparent", boxShadow: i === 0 ? "0 1px 3px rgba(11,18,32,.12)" : undefined,
                    }}>{s}</div>
                  ))}
                </div>
              </Tarjeta>
              {VOCES.map((x, i) => {
                const p = vozPos(i);
                const sel = x.id === elegida;
                const pop = sel && x.id === "sofia" ? 1 + 0.06 * Math.sin(Math.min(1, (t - M1.clickVoz) / 0.3) * Math.PI) : 1;
                return (
                  <div key={x.id} style={{
                    ...abs(p.x, p.y, VC.w), height: VC.h, borderRadius: 12, background: sel ? C.accentSoft : "#fff",
                    border: `2px solid ${sel ? C.accent : C.line}`, display: "flex", alignItems: "center", gap: 12, padding: "0 12px",
                    transform: `scale(${pop})`,
                  }}>
                    <Retrato id={x.id} size={62} anillo={sel ? C.accent : undefined} />
                    <div>
                      <div style={{ fontSize: 25, fontWeight: 700 }}>{x.nombre}</div>
                      <Badge style={{ marginTop: 4, fontSize: 15 }}>{x.genero}</Badge>
                    </div>
                  </div>
                );
              })}
              {/* La elegida, debajo (en una pantalla angosta, VoiceSelect pasa a una columna): nombre, género y la prueba */}
              <div style={abs(PREV.x, PREV.y, CW - 56)}>
                <div style={{ display: "flex", alignItems: "center", gap: 20, ...(elegida === "sofia" ? popStyle(pPreview, "0 50%") : {}) }}>
                  <Retrato id={v.id} size={104} anillo={C.accent} />
                  <div>
                    <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 54, lineHeight: 1 }}>{v.nombre}</div>
                    <Badge style={{ marginTop: 8 }}>{v.genero}</Badge>
                  </div>
                </div>
                <div style={{ fontSize: 22, fontWeight: 600, marginTop: 26, marginBottom: 8 }}>Prueba de voz</div>
                <div style={{ border: `2px solid ${C.line2}`, borderRadius: 10, padding: "14px 16px", fontSize: 25, lineHeight: 1.35 }}>
                  Hola, soy {v.nombre}. ¿En qué te puedo ayudar?
                </div>
              </div>
              <div style={{ ...abs(PLAY.x - 32, PLAY.y - 32, CW - 56), display: "flex", alignItems: "center", gap: 18 }}>
                <div style={{
                  width: 64, height: 64, borderRadius: 32, background: C.accent, display: "grid", placeItems: "center",
                  transform: `scale(${1 - presionDe(t, M1.clickPlay) * 0.1})`, flexShrink: 0,
                }}>
                  {sonando && progreso < 1 ? (
                    <svg width={26} height={26} viewBox="0 0 24 24"><rect x={5} y={4} width={5} height={16} rx={1.5} fill="#fff" /><rect x={14} y={4} width={5} height={16} rx={1.5} fill="#fff" /></svg>
                  ) : (
                    <svg width={28} height={28} viewBox="0 0 24 24"><path d="M7 4 L20 12 L7 20 Z" fill="#fff" /></svg>
                  )}
                </div>
                <Onda alto={56} color={sonando ? C.accent : C.line2} vivo={sonando && progreso < 1 ? 1 : 0} />
              </div>
              <div style={{ ...abs(PREV.x, PLAY.y + 50, CW - 56), height: 8, borderRadius: 4, background: C.line, overflow: "hidden" }}>
                <div style={{ width: `${progreso * 100}%`, height: "100%", background: C.accent }} />
              </div>
            </div>
          )}
        </AppFrame>
        <Cursor
          de={0.7}
          ruta={[
            { t: 0.7, x: OX + 420, y: OY + 720 },
            { t: 1.35, x: OX + 610, y: OY + 136 },
            { t: 1.7, x: OX + 610, y: OY + 136 },
            { t: 2.35, x: OX + vozPos(1).x + 120, y: OY + vozPos(1).y + 60 },
            { t: 2.55, x: OX + vozPos(1).x + 120, y: OY + vozPos(1).y + 60 },
            { t: 2.95, x: OX + PLAY.x, y: OY + PLAY.y },
          ]}
          clicks={[M1.clickTab, M1.clickVoz, M1.clickPlay]}
        />
      </Camara>
      <BordeBlanco />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 2. Herramientas: consultar_turnos en tu sistema

const M2 = { clickProbar: 1.15, ida: [1.25, 1.6] as const, vuelta: [1.6, 2.0] as const, resultado: 2.0 };
const SISTEMA = { x: X0 + CW / 2, y: 590 }; // centro del nodo "Tu sistema" (contenido)
const URL_PT = { x: X0 + CW / 2 + 90, y: 470 };
const PROBAR_Y = 690; // tarjeta Probar
const BOTON = { x: X0 + CW / 2, y: PROBAR_Y + 250 };
const RES_PT = { x: X0 + 330, y: PROBAR_Y + 330 };

export const Momento2: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const pSistema = usePopAt(0.35);
  const pRes = usePopAt(M2.resultado);
  const lineaO = ein(t, 0.5, 0.4);
  const ida = interpolate(t, M2.ida, [0, 1], CLAMP);
  const vuelta = interpolate(t, M2.vuelta, [0, 1], CLAMP);
  const SAL = { x: SISTEMA.x + 160, y: SISTEMA.y }; // la respuesta sale por la derecha del nodo y baja al resultado
  const ctrl = { x: X0 + CW + 20, y: SISTEMA.y + 120 };
  const bez = (k: number) => ({
    x: (1 - k) ** 2 * SAL.x + 2 * (1 - k) * k * ctrl.x + k ** 2 * RES_PT.x,
    y: (1 - k) ** 2 * SAL.y + 2 * (1 - k) * k * ctrl.y + k ** 2 * RES_PT.y,
  });
  const paquete = t >= M2.ida[0] && t < M2.ida[1]
    ? { x: URL_PT.x + (SISTEMA.x + 90 - URL_PT.x) * ida, y: URL_PT.y + (SISTEMA.y - 48 - URL_PT.y) * ida, txt: "GET" }
    : t >= M2.vuelta[0] && t < M2.vuelta[1]
      ? { ...bez(vuelta), txt: "{ }" }
      : null;
  return (
    <AbsoluteFill>
      <Fondo />
      <Camara keys={[
        { t: 0, s: 1, x: 550, y: 700 },
        { t: 1.0, s: 1, x: 550, y: 700 },
        { t: 2.0, s: 1.06, x: 560, y: 715 },
        { t: 4.2, s: 1.06, x: 560, y: 715 },
      ]}>
        <AppFrame activo="herramientas">
          <div style={abs(X0, 28, CW)}>
            <PageTitle derecha={<Boton>Guardar cambios</Boton>}>
              <span style={{ fontFamily: F.mono, fontWeight: 500, fontSize: 36, letterSpacing: 0 }}>consultar_turnos</span>
            </PageTitle>
          </div>
          <Tarjeta style={abs(X0, 130, CW)}>
            <Campo label="Nombre" valor="consultar_turnos" mono />
            <Campo label="Qué hace y cuándo usarla" valor="Consulta los turnos libres en tu sistema." style={{ marginTop: 18 }} />
            <div style={{ display: "flex", gap: 14, marginTop: 18 }}>
              <Campo label="Método" valor="GET" mono style={{ width: 110 }} />
              <Campo label="URL" valor="https://tusistema.com.ar/api/turnos" mono foco={t > M2.ida[0] && t < M2.vuelta[1]} style={{ flex: 1 }} />
            </div>
          </Tarjeta>
          <Tarjeta titulo="Probar" desc="La ejecuta de verdad, como la tenés en el editor." style={abs(X0, PROBAR_Y, CW)}>
            <Campo label="fecha" valor="jueves" mono />
            <Boton style={{ marginTop: 20, width: "100%", boxSizing: "border-box" }} presion={presionDe(t, M2.clickProbar)}>Probar</Boton>
            <div style={{ marginTop: 24, minHeight: 230, ...popStyle(pRes, "0 0") }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Badge color="green" style={{ fontSize: 20 }}>Funcionó</Badge>
                <span style={{ fontFamily: F.mono, fontSize: 22, color: C.ink2 }}>HTTP 200</span>
              </div>
              <div style={{ fontSize: 22, fontWeight: 600, marginTop: 16, marginBottom: 8 }}>Lo que recibe el agente</div>
              <div style={{ background: C.surface2, borderRadius: 10, padding: "12px 16px", fontFamily: F.mono, fontSize: 23, lineHeight: 1.45, color: C.ink }}>
                {"{ \"libres\": ["}<br />&nbsp;&nbsp;{"\"jueves 10:30\","}<br />&nbsp;&nbsp;{"\"jueves 11:00\" ] }"}
              </div>
            </div>
          </Tarjeta>
          {/* Tu sistema: adónde va el pedido (no es una pantalla del panel) */}
          <svg style={{ position: "absolute", left: 0, top: 0, overflow: "visible", opacity: lineaO }} width={1} height={1}>
            <path
              d={`M ${URL_PT.x} ${URL_PT.y} L ${SISTEMA.x + 90} ${SISTEMA.y - 48}`} stroke={C.accent} strokeWidth={4}
              strokeDasharray="4 12" strokeDashoffset={-frame * 1.5} strokeLinecap="round" fill="none"
            />
          </svg>
          <div style={{
            ...abs(SISTEMA.x - 160, SISTEMA.y - 48, 320), height: 96, background: "#fff",
            border: `3px solid ${C.accent}`, borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center", gap: 16,
            boxShadow: "0 16px 40px rgba(36,86,230,.18)", ...popStyle(pSistema),
          }}>
            <svg width={44} height={44} viewBox="0 0 24 24" fill="none" stroke={C.accent} strokeWidth={2} strokeLinecap="round">
              <ellipse cx={12} cy={5} rx={8} ry={3} /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
            </svg>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Tu sistema</div>
          </div>
          {paquete ? (
            <div style={{
              ...abs(paquete.x - 44, paquete.y - 26, 88), height: 52, borderRadius: 14, background: C.accent, color: "#fff",
              display: "grid", placeItems: "center", fontFamily: F.mono, fontSize: 21, boxShadow: "0 8px 20px rgba(36,86,230,.35)",
            }}>{paquete.txt}</div>
          ) : null}
        </AppFrame>
        <Cursor
          de={0.4}
          ruta={[
            { t: 0.4, x: OX + 600, y: OY + 1100 },
            { t: 1.05, x: OX + BOTON.x + 60, y: OY + BOTON.y },
            { t: 1.7, x: OX + BOTON.x + 60, y: OY + BOTON.y },
          ]}
          clicks={[M2.clickProbar]}
          hasta={1.7}
        />
      </Camara>
      <BordeBlanco />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 3. Derivación: área Ventas con dos personas

const M3 = { clickRot: 1.35 };
const MODAL3 = { x: 10, y: 20, w: CW + 52 };
const SEG = { x: MODAL3.x + 30 }; // el selector "A quién se llama primero" (su alto se midió en un cuadro de prueba)

export const Momento3: React.FC = () => {
  const t = useT();
  const pModal = usePopAt(0.0);
  const p1 = usePopAt(0.3);
  const p2 = usePopAt(0.55);
  const rot = ein(t, M3.clickRot + 0.05, 0.3);
  const horario = [usePopAt(1.9), usePopAt(2.05), usePopAt(2.2), usePopAt(2.35)];
  const personas: { id: RetratoId; nombre: string; tel: string; p: number }[] = [
    { id: "valentina", nombre: "Valentina", tel: "+54 9 11 5555-0101", p: p1 },
    { id: "lucas", nombre: "Lucas", tel: "+54 9 11 5555-0102", p: p2 },
  ];
  const dias = ["Lunes", "Martes", "Miércoles", "Jueves"];
  return (
    <AbsoluteFill>
      <Fondo />
      <Camara keys={[
        { t: 0, s: 1, x: 550, y: 700 },
        { t: 1.0, s: 1.06, x: 560, y: 700 },
        { t: 2.0, s: 1.06, x: 560, y: 730 },
        { t: 4.2, s: 1.06, x: 560, y: 730 },
      ]}>
        <AppFrame activo="equipo">
          <div style={abs(X0, 28, CW)}>
            <PageTitle>Equipo</PageTitle>
          </div>
          <Tarjeta titulo="Áreas" style={abs(X0, 130, CW)}>
            {["Ventas", "Administración", "Soporte"].map((a) => (
              <div key={a} style={{ padding: "14px 0", borderTop: `2px solid ${C.line}`, fontSize: 23 }}>{a}</div>
            ))}
          </Tarjeta>
          <Velo />
          <div style={{
            ...abs(MODAL3.x, MODAL3.y, MODAL3.w), background: "#fff", borderRadius: 20, padding: "26px 30px",
            border: `2px solid ${C.line}`, boxShadow: "0 16px 40px rgba(11,18,32,.10)", ...popStyle(pModal, "50% 10%"),
          }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 20 }}>
              <div style={{ flex: 1, fontSize: 30, fontWeight: 700 }}>Editar área Ventas</div>
              <div style={{ fontSize: 30, color: C.muted }}>×</div>
            </div>
            <Campo label="Nombre" valor="Ventas" />
            <Divisor texto="Personas" />
            <div style={{ fontSize: 19, color: C.muted, marginBottom: 12, lineHeight: 1.3 }}>Se las llama en este orden. Solo reciben llamadas las activas con teléfono.</div>
            {personas.map((x, i) => (
              <div key={x.id} style={{
                display: "flex", alignItems: "center", gap: 16, padding: "10px 14px", border: `2px solid ${C.line}`, borderRadius: 12,
                marginBottom: 12, ...popStyle(x.p, "0 50%"),
              }}>
                <span style={{ fontFamily: F.mono, fontSize: 22, color: C.muted, width: 18 }}>{i + 1}</span>
                <Retrato id={x.id} size={66} />
                <div style={{ flex: 1, fontSize: 28, fontWeight: 700 }}>{x.nombre}</div>
                <span style={{ fontFamily: F.mono, fontSize: 21, color: C.muted }}>{x.tel}</span>
              </div>
            ))}
            <div style={{ fontSize: 22, fontWeight: 600, marginTop: 18, marginBottom: 8 }}>A quién se llama primero</div>
            <div style={{ position: "relative", display: "flex", background: C.surface2, borderRadius: 10, padding: 4, width: 400 }}>
              <div style={{
                position: "absolute", top: 4, bottom: 4, left: 4 + rot * 196, width: 196, borderRadius: 8, background: "#fff",
                boxShadow: "0 1px 4px rgba(11,18,32,.16)",
              }} />
              {["En orden", "Rotativa"].map((s, i) => (
                <div key={s} style={{
                  position: "relative", width: 196, textAlign: "center", padding: "10px 0", fontSize: 24, fontWeight: 600,
                  color: (i === 1) === rot > 0.5 ? C.ink : C.muted,
                }}>{s}</div>
              ))}
            </div>
            <div style={{ fontSize: 19, color: C.muted, marginTop: 8, lineHeight: 1.3, height: 50 }}>
              {rot > 0.5
                ? "Empieza por la siguiente a la última que recibió una derivación, para repartirlas."
                : "Siempre empieza por la primera persona de la lista y sigue en orden."}
            </div>
            <Campo label="Timbre por persona" valor="20 s" style={{ width: 260, marginTop: 14 }} />
            <Divisor texto="Horario" />
            {dias.map((d, i) => (
              <div key={d} style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 10, ...popStyle(horario[i], "0 50%") }}>
                <div style={{ width: 150, fontSize: 24, fontWeight: 600 }}>{d}</div>
                <Hora h="09:00" /> <span style={{ color: C.muted, fontSize: 22 }}>a</span> <Hora h="18:00" />
              </div>
            ))}
          </div>
        </AppFrame>
        <Cursor
          de={0.6}
          ruta={[
            { t: 0.6, x: OX + 560, y: OY + 820 },
            { t: 1.25, x: OX + SEG.x + 4 + 196 + 98, y: OY + 578 },
            { t: 1.8, x: OX + SEG.x + 4 + 196 + 98, y: OY + 578 },
          ]}
          clicks={[M3.clickRot]}
          hasta={1.8}
        />
      </Camara>
      <BordeBlanco />
    </AbsoluteFill>
  );
};

const Divisor: React.FC<{ texto: string }> = ({ texto }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 14, margin: "22px 0 12px" }}>
    <span style={{ fontSize: 20, color: C.muted, fontWeight: 600 }}>{texto}</span>
    <div style={{ flex: 1, height: 2, background: C.line }} />
  </div>
);

const Hora: React.FC<{ h: string }> = ({ h }) => (
  <div style={{ border: `2px solid ${C.line2}`, borderRadius: 10, padding: "8px 16px", fontFamily: F.mono, fontSize: 23 }}>{h}</div>
);

// ---------------------------------------------------------------- 4. Probar: Hablarle ahora, en el navegador

const M4 = { click: 0.65, modal: 0.85 };
const SUBS = [
  { at: 1.25, user: false, txt: "Hola, soy Sofía. ¿En qué te ayudo?" },
  { at: 1.95, user: true, txt: "¿Tienen turno el jueves?" },
  { at: 2.55, user: false, txt: "Sí, a las 10:30. ¿Te lo reservo?" },
];
const CARD4_Y = 190;
const HABLAR = { x: X0 + CW / 2, y: CARD4_Y + 24 + 100 + 18 + 30 + 18 + 29 };

export const Momento4: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const pModal = usePopAt(M4.modal);
  const subs = [usePopAt(SUBS[0].at), usePopAt(SUBS[1].at), usePopAt(SUBS[2].at)];
  const hablaAgente = (t > SUBS[0].at - 0.1 && t < SUBS[1].at - 0.2) || t > SUBS[2].at - 0.1;
  const estado = t < SUBS[0].at - 0.15 ? "Llamando a Sofía…" : hablaAgente ? "Sofía habla…" : "Te escucha…";
  const pulso = hablaAgente ? 0.5 + 0.5 * Math.sin(frame / 4) : 0;
  const dim = ein(t, M4.modal - 0.05, 0.25);
  const MX = 14;
  const MW = CW + 44;
  return (
    <AbsoluteFill>
      <Fondo />
      <Camara keys={[
        { t: 0, s: 1, x: 550, y: 700 },
        { t: 1.0, s: 1, x: 550, y: 700 },
        { t: 1.9, s: 1.08, x: 560, y: 670 },
        { t: 4.2, s: 1.08, x: 560, y: 670 },
      ]}>
        <AppFrame activo="inicio">
          <div style={abs(X0, 28, CW)}>
            <PageTitle sub="Tus agentes, listos para probar. Hablales como si fueras un cliente.">Hola, Ana</PageTitle>
          </div>
          <Tarjeta style={abs(X0, CARD4_Y, CW)}>
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <Retrato id="sofia" size={100} />
              <div>
                <div style={{ fontSize: 32, fontWeight: 700 }}>Sofía</div>
                <div style={{ fontSize: 23, color: C.muted }}>Voz de Sofía</div>
              </div>
            </div>
            <div style={{ fontSize: 23, color: C.muted, margin: "18px 0", height: 30 }}>Responder las consultas y dar turnos.</div>
            <Boton style={{ width: "100%", boxSizing: "border-box" }} presion={presionDe(t, M4.click)}>
              <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={2.2} strokeLinecap="round"><rect x={9} y={3} width={6} height={11} rx={3} /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
              Hablarle ahora
            </Boton>
            <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
              <Boton tipo="default" style={{ flex: 1 }}>Llamame</Boton>
              <Boton tipo="default" style={{ flex: 1 }}>Editar</Boton>
            </div>
          </Tarjeta>
          <div style={{
            ...abs(X0, 600, CW), height: 260, border: `2px dashed ${C.line2}`, borderRadius: 18, display: "grid", placeItems: "center",
            textAlign: "center", color: C.ink2, fontSize: 24, fontWeight: 600,
          }}>
            <div>
              <div style={{ width: 64, height: 64, borderRadius: 32, background: C.accentSoft, color: C.accent, fontSize: 40, display: "grid", placeItems: "center", margin: "0 auto 12px" }}>+</div>
              Crear otro agente
            </div>
          </div>
          <Velo o={dim} />
          <div style={{
            ...abs(MX, 150, MW), background: "#fff", borderRadius: 22, padding: "26px 32px 30px",
            border: `2px solid ${C.line}`, boxShadow: "0 16px 40px rgba(11,18,32,.10)", ...popStyle(pModal, "50% 30%"), display: t < M4.modal ? "none" : "block",
          }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 14 }}>
              <div style={{ flex: 1, fontSize: 30, fontWeight: 700 }}>Hablar con Sofía</div>
              <div style={{ fontSize: 30, color: C.muted }}>×</div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <div style={{ borderRadius: "50%", padding: 6, border: `3px solid ${hablaAgente ? C.accent : "transparent"}`, boxShadow: hablaAgente ? `0 0 0 ${6 + pulso * 10}px rgba(36,86,230,${0.22 - pulso * 0.12})` : undefined }}>
                <Retrato id="sofia" size={124} />
              </div>
              <div style={{ fontSize: 30, fontWeight: 700, marginTop: 4 }}>Sofía</div>
              <div style={{ fontFamily: F.mono, fontSize: 22, color: C.muted }}>{estado}</div>
            </div>
            <div style={{
              border: `2px solid ${C.line}`, borderRadius: 16, padding: 16, marginTop: 16, height: 250, boxSizing: "border-box",
              display: "flex", flexDirection: "column", gap: 10, justifyContent: "flex-end", overflow: "hidden",
            }}>
              {SUBS.map((s, i) => (t >= s.at ? (
                <div key={i} style={{
                  alignSelf: s.user ? "flex-end" : "flex-start", maxWidth: "88%", padding: "10px 16px", borderRadius: 16,
                  background: s.user ? C.accentSoft : C.surface2, fontSize: 27, lineHeight: 1.3, ...popStyle(subs[i], s.user ? "100% 100%" : "0 100%"),
                }}>{s.txt}</div>
              ) : null))}
            </div>
            <div style={{ display: "flex", justifyContent: "center", marginTop: 20 }}>
              <Boton tipo="rojo">Cortar</Boton>
            </div>
          </div>
        </AppFrame>
        <Cursor
          de={0.1}
          ruta={[
            { t: 0.1, x: OX + 560, y: OY + 760 },
            { t: 0.55, x: OX + HABLAR.x + 40, y: OY + HABLAR.y },
            { t: 0.9, x: OX + HABLAR.x + 40, y: OY + HABLAR.y },
          ]}
          clicks={[M4.click]}
          hasta={0.85}
        />
      </Camara>
      <BordeBlanco />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- 5. Reportes: consultas por día, objetivo y transferidas

// Ilustrativo: siete días con llamadas entrantes, WhatsApp y web, y las transferencias pedidas
const DIAS = [
  { d: "20/10", tel: 96, wa: 58, web: 18, tr: 9 },
  { d: "21/10", tel: 112, wa: 64, web: 22, tr: 11 },
  { d: "22/10", tel: 104, wa: 71, web: 20, tr: 10 },
  { d: "23/10", tel: 121, wa: 76, web: 26, tr: 14 },
  { d: "24/10", tel: 118, wa: 82, web: 24, tr: 12 },
  { d: "25/10", tel: 62, wa: 49, web: 15, tr: 6 },
  { d: "26/10", tel: 34, wa: 36, web: 10, tr: 4 },
];
const KPIS = [
  { label: "Consultas", valor: 1218, fmt: (n: number) => n.toLocaleString("es-AR"), sub: "", delta: "↗ 12 % vs. período anterior" },
  { label: "Objetivo cumplido", valor: 84, fmt: (n: number) => `${n} %`, sub: "991 de 1.180", delta: "↗ 3 pts vs. período anterior" },
  { label: "Transferidas", valor: 66, fmt: (n: number) => String(n), sub: "5 % · 61 atendidas", delta: "↘ 8 % vs. período anterior" },
];
const KPI_Y = 770;

export const Momento5: React.FC = () => {
  const t = useT();
  const CH = { x: 20, y: 30, w: CW - 96, h: 320 }; // área del gráfico dentro de la tarjeta
  const max = 240;
  const cuenta = interpolate(t, [1.3, 2.3], [0, 1], { ...CLAMP, easing: (x) => 1 - (1 - x) ** 3 });
  const kp = [usePopAt(1.2), usePopAt(1.35), usePopAt(1.5)];
  const linea = ein(t, 0.9, 0.6);
  const bw = 54;
  const paso = CH.w / DIAS.length;
  const pts = DIAS.map((d, i) => `${CH.x + paso * i + paso / 2},${CH.y + CH.h - (d.tr / max) * CH.h}`).join(" ");
  return (
    <AbsoluteFill>
      <Fondo />
      <Camara keys={[
        { t: 0, s: 1, x: 550, y: 700 },
        { t: 4.2, s: 1, x: 550, y: 700 },
      ]}>
        <AppFrame activo="reportes">
          <div style={abs(X0, 28, CW)}>
            <PageTitle>Reportes</PageTitle>
          </div>
          <Pestanas items={["Resumen", "Consumo", "Llamadas", "Resultados", "Mensajes", "Transferencias"]} activa="Resumen" style={abs(X0, 108, CW)} />
          <Tarjeta titulo="Consultas por día" style={abs(X0, 190, CW)}>
            <div style={{ position: "relative", height: 490 }}>
              {[0, 1, 2, 3].map((g) => (
                <div key={g} style={{ position: "absolute", left: CH.x, width: CH.w, top: CH.y + (CH.h / 4) * g, height: 2, background: C.line }} />
              ))}
              {DIAS.map((d, i) => {
                const k = interpolate(t, [0.15 + i * 0.09, 0.75 + i * 0.09], [0, 1], { ...CLAMP, easing: (x) => 1 - (1 - x) ** 3 });
                const hTel = (d.tel / max) * CH.h * k;
                const hWa = (d.wa / max) * CH.h * k;
                const hWeb = (d.web / max) * CH.h * k;
                const x = CH.x + paso * i + paso / 2 - bw / 2;
                const base = CH.y + CH.h;
                return (
                  <React.Fragment key={d.d}>
                    <div style={{ position: "absolute", left: x, width: bw, top: base - hTel, height: hTel, background: "#2456e6" }} />
                    <div style={{ position: "absolute", left: x, width: bw, top: base - hTel - hWa, height: hWa, background: "#0d9488" }} />
                    <div style={{ position: "absolute", left: x, width: bw, top: base - hTel - hWa - hWeb, height: hWeb, background: "#adb5bd", borderRadius: "6px 6px 0 0" }} />
                    <div style={{ position: "absolute", left: x - 20, width: bw + 40, top: base + 12, textAlign: "center", fontSize: 19, color: C.muted }}>{d.d}</div>
                  </React.Fragment>
                );
              })}
              <svg style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }} width={1} height={1}>
                <polyline points={pts} fill="none" stroke="#495057" strokeWidth={4} strokeDasharray={1400} strokeDashoffset={1400 * (1 - linea)} />
              </svg>
              <div style={{ position: "absolute", left: CH.x, width: CH.w, top: CH.y + CH.h + 56, display: "flex", flexWrap: "wrap", columnGap: 26, rowGap: 8, fontSize: 20, color: C.ink2 }}>
                {[["#2456e6", "Teléfono entrante"], ["#0d9488", "WhatsApp"], ["#adb5bd", "Web"], ["#495057", "Transferencias pedidas"]].map(([c, l]) => (
                  <span key={l} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 16, height: 16, borderRadius: 4, background: c }} /> {l}
                  </span>
                ))}
              </div>
            </div>
          </Tarjeta>
          {KPIS.map((k, i) => (
            <div key={k.label} style={{
              ...abs(X0, KPI_Y + i * 176, CW), height: 168, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "18px 28px",
              ...popStyle(kp[i], "50% 0"),
            }}>
              <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", textTransform: "uppercase", color: C.muted }}>{k.label}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 8 }}>
                <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 72, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{k.fmt(Math.round(k.valor * cuenta))}</span>
                {k.sub ? <span style={{ fontSize: 23, color: C.muted }}>{k.sub}</span> : null}
              </div>
              <div style={{ fontSize: 20, color: C.muted, marginTop: 10 }}>{k.delta}</div>
            </div>
          ))}
        </AppFrame>
      </Camara>
      <BordeBlanco />
    </AbsoluteFill>
  );
};
