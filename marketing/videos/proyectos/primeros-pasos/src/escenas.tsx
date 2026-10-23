import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { useIn, usePop } from "../../../src/comun/ui";
import {
  AppBar, Body, Btn, CardUI, Chip, Cursor, Input, Phone, RadioCard, Section, SwitchUI,
  TabsBar, Titulo, Toast, useT,
} from "./panel";

const Check: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 18, color: C.ink2, lineHeight: 1.25 }}>
    <span style={{ color: C.ok, fontWeight: 800 }}>✓</span>
    <span>{children}</span>
  </div>
);

// 1. Apertura: gracias por probar Atentina.
export const Intro: React.FC = () => {
  const p = useIn(0.15, 0.8);
  const s = usePop(0.3);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.1 }}>
        <defs>
          <pattern id="dots-dark" width={36} height={36} patternUnits="userSpaceOnUse">
            <circle cx={2} cy={2} r={1.6} fill={C.ctaMuted} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots-dark)" />
      </svg>
      <div style={{ position: "absolute", left: 84, right: 84, top: 440, opacity: p }}>
        <div style={{ transform: `scale(${s})`, transformOrigin: "left center", width: 210 }}>
          <AgenteLogo size={200} />
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.12em", color: C.accentOnDark, marginTop: 58 }}>
          PRIMEROS PASOS
        </div>
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 78, lineHeight: 1.03, letterSpacing: "-0.02em",
          color: "#fff", marginTop: 18,
        }}>
          Gracias por probar<br /><span style={{ color: C.accentOnDark }}>Atentina.</span>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 34, color: C.ctaMuted, marginTop: 30 }}>
          Te cuento cómo empezar.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 2. Agentes > Nuevo agente.
export const Agentes: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 1 · tu primer agente" text="Abrí Agentes y creá uno" accent="nuevo." />
    <Phone>
      <AppBar />
      <Body>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, color: C.ink, letterSpacing: "-0.01em" }}>Agentes</div>
        <div style={{ fontFamily: F.body, fontSize: 20, color: C.muted, marginTop: 2 }}>Tus agentes de voz</div>
        <Btn primary style={{ marginTop: 18, height: 62, fontSize: 27 }}>+ Nuevo agente</Btn>
        <div style={{
          marginTop: 26, height: 300, borderRadius: 20, border: `2px dashed ${C.line2}`, background: "rgba(255,255,255,.6)",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 40px", textAlign: "center",
        }}>
          <div style={{
            width: 82, height: 82, borderRadius: 41, background: C.accentSoft, display: "flex", alignItems: "center",
            justifyContent: "center", marginBottom: 18,
          }}>
            <AgenteLogo size={58} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 27, color: C.ink }}>Todavía no hay agentes</div>
          <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted, lineHeight: 1.35, marginTop: 6 }}>
            Creá el primero para atender llamadas y WhatsApp.
          </div>
        </div>
      </Body>
      <Cursor x={598} y={240} at={2.0} click={3.1} />
    </Phone>
  </AbsoluteFill>
);

// 3. Nuevo agente: nombre y Asistente básico (con zoom al escribir).
export const Nombre: React.FC = () => {
  const t = useT();
  const texto = "Atención al cliente";
  const n = Math.floor(interpolate(t, [1.15, 3.5], [0, texto.length], CLAMP));
  const escrito = texto.slice(0, n);
  const typing = t > 1.15 && n < texto.length;
  const zoom = interpolate(t, [0.55, 1.15], [1, 1.1], CLAMP);
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Paso 2 · nombre y base" text="Un nombre claro y" accent={"Asistente\u00A0básico."} size={54} />
      <Phone scale={zoom} origin="50% 22%">
        <AppBar />
        <div style={{ position: "absolute", inset: 0, top: 0, background: "rgba(11,18,32,.45)" }} />
        <div style={{
          position: "absolute", left: 24, right: 24, top: 156, background: "#fff", borderRadius: 22, padding: 22,
          boxShadow: "0 24px 60px rgba(11,18,32,.25)",
        }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Nuevo agente</div>
            <div style={{ flex: 1 }} />
            <div style={{ fontFamily: F.body, fontSize: 30, color: C.muted, lineHeight: 1 }}>×</div>
          </div>

          <Input label="Nombre" value={escrito} focused caret={typing} />
          <Input label="Descripción" placeholder="Opcional: para qué lo usás." style={{ marginTop: 14 }} />

          <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 19, color: C.ink2, marginTop: 18, marginBottom: 9 }}>
            Punto de partida
          </div>
          <RadioCard
            title="Asistente básico" selected
            desc="Atiende, responde con la base de conocimiento y toma un contacto si no puede."
          />
          <RadioCard title="En blanco" desc="Solo lo mínimo para que sea válido." style={{ marginTop: 8 }} />

          <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
            <Btn style={{ flex: 1 }}>Cancelar</Btn>
            <Btn primary style={{ flex: 1.45 }}>Crear agente</Btn>
          </div>
        </div>
        <Cursor x={556} y={776} at={6.1} click={7.0} />
      </Phone>
    </AbsoluteFill>
  );
};

// 4. Definición: rol, voz, objetivo, apertura, reglas y base.
export const Definicion: React.FC = () => {
  const s1 = useIn(0.35, 0.5);
  const s2 = useIn(0.7, 0.5);
  const s3 = useIn(1.05, 0.5);
  const s4 = useIn(1.4, 0.5);
  const s5 = useIn(1.75, 0.5);
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Paso 3 · la definición" text="Rol, objetivo y" accent="apertura." />
      <Phone>
        <AppBar />
        <div style={{ padding: "12px 20px 8px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontFamily: F.body, fontSize: 28, color: C.muted, lineHeight: 1 }}>‹</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Atención al cliente</div>
          <Chip style={{ fontSize: 16, padding: "3px 9px" }}>v1</Chip>
        </div>
        <TabsBar active="Definición" />
        <Body style={{ padding: "12px 16px" }}>
          <Section title="Agente" style={{ opacity: s1, transform: `translateY(${(1 - s1) * 16}px)` }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 19, color: C.muted, marginBottom: 5 }}>
              <span>Rol</span><span style={{ color: C.ink, fontWeight: 700 }}>Asistente virtual</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 19, color: C.muted }}>
              <span>Idioma</span><span style={{ color: C.ink, fontWeight: 700 }}>es-AR</span>
            </div>
          </Section>

          <Section title="Voz" style={{ marginTop: 10, opacity: s2, transform: `translateY(${(1 - s2) * 16}px)` }}>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              <Chip active>✓ Sofía</Chip>
              <Chip>Valentina</Chip>
              <Chip>Martín</Chip>
            </div>
            <div style={{ fontFamily: F.body, fontSize: 16, color: C.muted, marginTop: 9 }}>
              La voz ya viene elegida: podés cambiarla y escuchar la apertura.
            </div>
          </Section>

          <Section title="Objetivo y apertura" style={{ marginTop: 10, opacity: s3, transform: `translateY(${(1 - s3) * 16}px)` }}>
            <div style={{ fontFamily: F.body, fontSize: 17, color: C.ink2, lineHeight: 1.25 }}>
              Atender, entender qué necesita la persona y responder con la base de conocimiento.
            </div>
            <div style={{
              marginTop: 8, background: C.surface2, borderRadius: 10, padding: "8px 10px", fontFamily: F.body,
              fontSize: 16, color: C.ink2, lineHeight: 1.25,
            }}>
              “Hola, gracias por comunicarte. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?”
            </div>
          </Section>

          <Section title="Reglas" style={{ marginTop: 10, opacity: s4, transform: `translateY(${(1 - s4) * 16}px)` }}>
            <Check>Hablar de vos, con dos frases cortas por turno.</Check>
            <div style={{ height: 5 }} />
            <Check>Responder solo con la base de conocimiento.</Check>
          </Section>

          <Section title="Base de conocimiento" style={{ marginTop: 10, opacity: s5, transform: `translateY(${(1 - s5) * 16}px)` }}>
            <div style={{ fontFamily: F.body, fontSize: 17, color: C.ink2, lineHeight: 1.3 }}>
              La empresa: a qué se dedica, dirección y horarios.<br />
              Preguntas frecuentes: una respuesta por línea.
            </div>
          </Section>
        </Body>
        <div style={{ position: "absolute", left: 16, right: 16, bottom: 20 }}>
          <Btn primary style={{ height: 60 }}>Guardar</Btn>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// 5. Guardar: cada cambio es una versión nueva.
export const Guardar: React.FC = () => {
  const t = useT();
  const guardado = t > 1.9;
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Paso 4 · guardar" text="Guardar crea una" accent={"versión\u00A0nueva."} />
      <Phone>
        <AppBar />
        <div style={{ padding: "12px 20px 8px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Atención al cliente</div>
          <Chip active style={{ fontSize: 16, padding: "3px 9px" }}>{guardado ? "v2" : "v1"}</Chip>
        </div>
        <TabsBar active="Versiones" />
        <Body style={{ padding: "14px 16px" }}>
          <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted, lineHeight: 1.35, marginBottom: 12 }}>
            Guardar crea una versión nueva. Las llamadas en curso siguen con la versión con la que empezaron.
          </div>
          <CardUI style={{ display: "flex", alignItems: "center", gap: 12, padding: 14, borderColor: guardado ? C.ok : C.line }}>
            <div style={{
              width: 44, height: 44, borderRadius: 22, background: guardado ? C.okSoft : C.surface2, color: guardado ? C.ok : C.muted,
              display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 17,
            }}>{guardado ? "✓" : "v1"}</div>
            <div>
              <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 21, color: C.ink }}>
                {guardado ? "Versión 2" : "Versión 1"}
              </div>
              <div style={{ fontFamily: F.body, fontSize: 17, color: C.muted }}>
                {guardado ? "Guardada recién · vos" : "La definición actual"}
              </div>
            </div>
          </CardUI>
          <CardUI style={{ display: "flex", alignItems: "center", gap: 12, padding: 14, marginTop: 9, opacity: 0.7 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 22, background: C.surface2, color: C.muted,
              display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 17,
            }}>v1</div>
            <div>
              <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 21, color: C.ink }}>Versión 1</div>
              <div style={{ fontFamily: F.body, fontSize: 17, color: C.muted }}>El punto de partida</div>
            </div>
          </CardUI>
          <div style={{
            marginTop: 16, background: C.accentSoft, borderRadius: 14, padding: 14, fontFamily: F.body,
            fontSize: 18, color: C.ink2, lineHeight: 1.3,
          }}>
            Si algo no te convence, restaurá una versión anterior y seguí probando.
          </div>
        </Body>
        <div style={{ position: "absolute", left: 16, right: 16, bottom: 20 }}>
          <Btn primary style={{ height: 60, background: guardado ? C.ok : C.accent }}>Guardar</Btn>
        </div>
        <Cursor x={588} y={1316} at={1.0} click={1.75} />
        <Toast at={2.05} title="Agente guardado" sub="Versión 2 · ya podés probarlo." />
      </Phone>
    </AbsoluteFill>
  );
};

// 6. Probar: Modo prueba.
export const Probar: React.FC = () => {
  const t = useT();
  const on = t > 2.1;
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Paso 5 · probar" text="Modo prueba, sin" accent="teléfono." />
      <Phone>
        <AppBar />
        <div style={{ padding: "12px 20px 8px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Atención al cliente</div>
          <Chip active style={{ fontSize: 16, padding: "3px 9px" }}>v2</Chip>
        </div>
        <TabsBar active="Probar" />
        <Body style={{ padding: "12px 16px" }}>
          <CardUI pad={14}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 22, color: C.ink }}>Conversación por texto</div>
            <Input placeholder="Escribile al agente…" style={{ marginTop: 8 }} />
          </CardUI>

          <CardUI style={{ marginTop: 10 }} pad={16}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 23, color: C.ink }}>Llamada con este agente</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 21, color: C.ink }}>Modo prueba</div>
                <div style={{ fontFamily: F.body, fontSize: 16, color: C.muted, lineHeight: 1.2 }}>
                  Te conectás por navegador y hacés de interesado.
                </div>
              </div>
              <SwitchUI on={on} />
            </div>
            <Input label="Teléfono" value={on ? "No hace falta" : ""} placeholder="+54 9 11…" disabled={on} style={{ marginTop: 11 }} />
            <Input label="Voz" value="Sofía" style={{ marginTop: 10 }} />
            <Btn primary disabled={!on} style={{ marginTop: 16, height: 58, fontSize: 23 }}>Crear llamada de prueba</Btn>
            <div style={{ fontFamily: F.body, fontSize: 15, color: C.muted, lineHeight: 1.25, marginTop: 9 }}>
              No se marca ningún teléfono: te aparece un link para conectarte desde el navegador.
            </div>
          </CardUI>
        </Body>
        <Cursor x={638} y={388} at={1.2} click={2.05} />
      </Phone>
    </AbsoluteFill>
  );
};

// 7. El link de la llamada de prueba.
export const Enlace: React.FC = () => {
  const t = useT();
  const alerta = t > 2.75;
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Paso 6 · el link" text="Conectate desde el" accent="navegador." />
      <Phone>
        <AppBar />
        <div style={{ padding: "12px 20px 8px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Atención al cliente</div>
          <Chip active style={{ fontSize: 16, padding: "3px 9px" }}>v2</Chip>
        </div>
        <TabsBar active="Probar" />
        <Body style={{ padding: "12px 16px" }}>
          <CardUI pad={16}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ flex: 1, fontFamily: F.display, fontWeight: 800, fontSize: 23, color: C.ink }}>Llamada con este agente</div>
              <Chip active style={{ fontSize: 16 }}>Modo prueba</Chip>
            </div>
            <Input label="Teléfono" value="No hace falta" disabled style={{ marginTop: 11 }} />
            <Input label="Voz" value="Sofía" style={{ marginTop: 10 }} />
            <Btn primary style={{ marginTop: 16, height: 58, fontSize: 23 }}>Crear llamada de prueba</Btn>
            <div style={{ opacity: alerta ? 0 : 1, fontFamily: F.body, fontSize: 15, color: C.muted, lineHeight: 1.25, marginTop: 9 }}>
              No se marca ningún teléfono.
            </div>
          </CardUI>

          <div style={{
            marginTop: 12, background: C.okSoft, border: `1.5px solid ${C.ok}`, borderRadius: 16, padding: 14,
            opacity: alerta ? 1 : 0, transform: `translateY(${alerta ? 0 : 14}px)`,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 14, background: C.ok, color: "#fff", display: "flex",
                alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 16,
              }}>✓</div>
              <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 21, color: C.ink }}>Llamada de prueba creada</div>
            </div>
            <div style={{
              marginTop: 9, fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.accent,
              textDecoration: "underline", lineHeight: 1.2,
            }}>
              Conectate acá para hablar con el agente
            </div>
            <div style={{ fontFamily: F.body, fontSize: 16, color: C.ink2, marginTop: 5 }}>
              Abrilo ahora: el link no se vuelve a mostrar.
            </div>
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 17, color: C.accent, marginTop: 7 }}>Ver en vivo</div>
          </div>
        </Body>
        <Cursor x={398} y={686} at={1.2} click={2.15} />
        <Cursor x={430} y={706} at={4.7} click={5.45} />
      </Phone>
    </AbsoluteFill>
  );
};

// 8. La llamada desde el navegador.
export const Llamada: React.FC = () => {
  const p1 = useIn(1.1, 0.4);
  const p2 = useIn(3.3, 0.4);
  return (
    <AbsoluteFill>
      <Titulo eyebrow="La llamada" text="Hablá y escuchá la" accent="respuesta." />
      <Phone>
        <div style={{ height: 46, background: "#fff", borderBottom: `1px solid ${C.line}`, display: "flex", alignItems: "center", gap: 8, padding: "0 16px" }}>
          <span style={{ fontSize: 26, color: C.muted, lineHeight: 1 }}>‹</span>
          <svg width={16} height={18} viewBox="0 0 16 18">
            <rect x={1.5} y={7.5} width={13} height={9} rx={2.5} fill="none" stroke={C.muted} strokeWidth={1.8} />
            <path d="M5 7.5V5a3 3 0 0 1 6 0v2.5" fill="none" stroke={C.muted} strokeWidth={1.8} />
          </svg>
          <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 18, color: C.ink2 }}>Llamada de prueba</div>
          <div style={{ flex: 1 }} />
          <div style={{ fontFamily: F.body, fontSize: 22, color: C.muted, letterSpacing: 2 }}>···</div>
        </div>

        <div style={{ position: "relative", height: 1340, background: C.ink }}>
          <div style={{
            margin: "22px auto 0", width: "fit-content", display: "flex", alignItems: "center", gap: 8,
            background: "rgba(27,156,91,.18)", border: `1.5px solid ${C.ok}`, color: "#7ee2ac",
            borderRadius: 999, padding: "5px 14px", fontFamily: F.body, fontWeight: 700, fontSize: 17,
          }}>● En llamada</div>

          <div style={{ position: "relative", width: 250, height: 250, margin: "34px auto 0" }}>
            <div style={{ position: "absolute", inset: -14, borderRadius: "50%", border: `2px solid rgba(157,182,255,.35)` }} />
            <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "rgba(157,182,255,.10)" }} />
            <div style={{ position: "absolute", left: 26, top: 26 }}><AgenteLogo size={198} /></div>
          </div>

          <div style={{ textAlign: "center", marginTop: 22 }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 43, color: "#fff", letterSpacing: "-0.01em" }}>Sofía</div>
            <div style={{ fontFamily: F.body, fontSize: 19, color: C.ctaMuted, marginTop: 4 }}>
              Asistente virtual · Atención al cliente
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 25, color: C.accentOnDark, marginTop: 10, letterSpacing: "0.06em" }}>
              00:12
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
            <svg width={190} height={46} viewBox="0 0 190 46">
              {Array.from({ length: 19 }).map((_, i) => {
                const h = 8 + 30 * Math.abs(Math.sin(i * 1.17 + 0.4));
                return <rect key={i} x={i * 10} y={23 - h / 2} width={5} height={h} rx={2.5} fill={C.accentOnDark} opacity={0.85} />;
              })}
            </svg>
          </div>

          <div style={{ padding: "20px 20px 0" }}>
            <div style={{
              marginLeft: "auto", width: "fit-content", maxWidth: 470, background: C.accent, color: "#fff",
              borderRadius: "18px 18px 4px 18px", padding: "11px 15px", fontFamily: F.body, fontSize: 19,
              lineHeight: 1.25, opacity: p1, transform: `translateY(${p1 ? 0 : 12}px)`,
            }}>
              Hola, quería hacer una consulta.
            </div>
            <div style={{
              width: "fit-content", maxWidth: 510, background: "#1b2438", color: "#eef2ff", marginTop: 10,
              borderRadius: "18px 18px 18px 4px", padding: "11px 15px", fontFamily: F.body, fontSize: 19,
              lineHeight: 1.25, opacity: p2, transform: `translateY(${p2 ? 0 : 12}px)`,
            }}>
              Hola, soy Sofía, la asistente virtual. Contame, ¿en qué te puedo ayudar?
            </div>
          </div>

          <div style={{ position: "absolute", left: 0, right: 0, bottom: 38, display: "flex", alignItems: "center", justifyContent: "center", gap: 46 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{
                width: 76, height: 76, borderRadius: 38, background: "#1b2438", border: `2px solid #2a3652`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <svg width={30} height={32} viewBox="0 0 24 24">
                  <rect x={9} y={3} width={6} height={11} rx={3} fill="#fff" />
                  <path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6" fill="none" stroke="#fff" strokeWidth={1.8} strokeLinecap="round" />
                </svg>
              </div>
              <div style={{ fontFamily: F.body, fontSize: 15, color: C.ctaMuted, marginTop: 6 }}>Micrófono</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{
                width: 86, height: 86, borderRadius: 43, background: C.warn, display: "flex", alignItems: "center",
                justifyContent: "center", boxShadow: "0 12px 26px rgba(180,35,24,.4)",
              }}>
                <svg width={40} height={40} viewBox="0 0 24 24" style={{ transform: "rotate(135deg)" }}>
                  <path d="M5 3h3l2 5-2.5 1.5a11 11 0 0 0 7 7L16 14l5 2v3a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2Z" fill="#fff" />
                </svg>
              </div>
              <div style={{ fontFamily: F.body, fontSize: 15, color: C.ctaMuted, marginTop: 6 }}>Colgar</div>
            </div>
          </div>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// 9. Cierre.
export const Cierre: React.FC = () => {
  const p = useIn(0.2, 0.8);
  const s = usePop(0.35);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.1 }}>
        <defs>
          <pattern id="dots-dark-2" width={36} height={36} patternUnits="userSpaceOnUse">
            <circle cx={2} cy={2} r={1.6} fill={C.ctaMuted} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots-dark-2)" />
      </svg>
      <div style={{ position: "absolute", left: 84, right: 84, top: 570, opacity: p }}>
        <div style={{ transform: `scale(${s})`, transformOrigin: "left center", width: 170 }}>
          <AgenteLogo size={160} />
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 23, letterSpacing: "0.12em", color: C.accentOnDark, marginTop: 50 }}>
          EMPIEZA ACÁ
        </div>
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 70, lineHeight: 1.04, letterSpacing: "-0.02em",
          color: "#fff", marginTop: 16,
        }}>
          Tu agente, listo<br />para <span style={{ color: C.accentOnDark }}>atender.</span>
        </div>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 12, marginTop: 42, background: "#151d2e",
          border: `2px solid #24304a`, borderRadius: 999, padding: "12px 24px",
          fontFamily: F.mono, fontSize: 27, color: "#fff",
        }}>
          app.atentina.com.ar
        </div>
        <div style={{ fontFamily: F.body, fontSize: 29, color: C.ctaMuted, marginTop: 30 }}>
          Gracias por probar Atentina.
        </div>
      </div>
    </AbsoluteFill>
  );
};
