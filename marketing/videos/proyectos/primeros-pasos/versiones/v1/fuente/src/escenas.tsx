import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { useIn, usePop } from "../../../src/comun/ui";
import {
  Aviso, Boton, Cabecera, Campo, DetalleAgente, HEADER, Icono, Insignia, Interruptor, P, Tarjeta, Telefono, Texto, Titulo,
  Toque, useScroll, useTipeo, useZoom, VH, W,
} from "./panel";
import { en, TIPEO } from "./timeline";

// ---------- comunes de las escenas ----------

const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Título de la escena para el formato vertical: rótulo en mono y frase con el remate en el acento. */
const Encabezado: React.FC<{ rotulo: string; texto: string; acento: string }> = ({ rotulo, texto, acento }) => {
  const p = useIn(0.05, 0.6);
  return (
    <>
    {/* Banda detrás del título: con el zoom el teléfono pasa por debajo y el título se sigue leyendo */}
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 440, zIndex: 60,
      background: "linear-gradient(180deg, rgba(246,248,251,1) 0%, rgba(246,248,251,0.97) 80%, rgba(246,248,251,0) 100%)" }} />
    <div style={{ position: "absolute", left: 80, right: 80, top: 118, opacity: p, transform: `translateY(${(1 - p) * 20}px)`, zIndex: 61 }}>
      <div style={{ fontFamily: F.mono, fontSize: 28, letterSpacing: "0.08em", color: C.accent, textTransform: "uppercase" }}>{rotulo}</div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 70, lineHeight: 1.06, color: C.ink, marginTop: 16, letterSpacing: "-0.015em" }}>
        {texto} <span style={{ color: C.accent }}>{acento}</span>
      </div>
    </div>
    </>
  );
};

/** Contenido de la página debajo de la cabecera, desplazado `scroll` px. */
const Pagina: React.FC<{ scroll: number; children: React.ReactNode }> = ({ scroll, children }) => (
  <div style={{ position: "absolute", left: 0, top: HEADER - scroll, width: W, height: 3000 }}>{children}</div>
);

/** Velo oscuro de los modales de Mantine. */
const Velo: React.FC<{ o: number }> = ({ o }) => (
  <div style={{ position: "absolute", left: 0, top: 0, width: W, height: VH, background: "rgba(11,18,32,0.45)", opacity: o, zIndex: 25 }} />
);

const TituloTarjeta: React.FC<{ y: number; t: string; desc?: string; w?: number }> = ({ y, t, desc, w = W - 72 }) => (
  <>
    <Texto x={36} y={y} s={18} peso={700} f={F.display} style={{ letterSpacing: "-0.015em" }}>{t}</Texto>
    {desc ? <Texto x={36} y={y + 27} w={w} s={12} c={P.dim} lh={1.4}>{desc}</Texto> : null}
  </>
);

// ---------- 0. Intro ----------

export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const t = useIn(0.35, 0.7);
  const remate = useIn(en("p1", "te cuento") - 0.1, 0.6);
  const sub = useIn(1.6, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 420 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 700, textAlign: "center", fontFamily: F.mono, fontSize: 30, letterSpacing: "0.1em",
        color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PRIMEROS PASOS
      </div>
      <div style={{ position: "absolute", left: 80, right: 80, top: 790, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 88,
        lineHeight: 1.06, color: C.ctaInk, opacity: t, transform: `translateY(${(1 - t) * 24}px)`, letterSpacing: "-0.015em" }}>
        Gracias por probar Atentina.<br />
        <span style={{ color: C.accentOnDark, opacity: 0.25 + 0.75 * remate }}>Te cuento cómo empezar.</span>
      </div>
      <div style={{ position: "absolute", left: 100, right: 100, top: 1250, textAlign: "center", fontFamily: F.body, fontSize: 38, lineHeight: 1.35,
        color: C.ctaMuted, opacity: sub }}>
        Creá tu agente y probalo con una llamada desde el navegador
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1. Agentes ----------

const NAV = ["Inicio", "Conversaciones", "Llamadas", "Agentes", "Voces", "Modelos", "WhatsApp", "Contactos", "Campañas", "Apps", "Consumos", "API", "Uso de la API", "Mi cuenta", "Plan"];
const NAV_ICO = ["home", "messages", "phoneOut", "robot", "mic"] as const;

const Menu: React.FC<{ activo: number; o: number }> = ({ activo, o }) => (
  <div style={{ position: "absolute", left: 0, top: HEADER, width: W, height: VH - HEADER, background: "#fff", opacity: o, zIndex: 15 }}>
    {NAV.slice(0, 12).map((n, i) => (
      <div key={n} style={{ position: "absolute", left: 10, top: 10 + i * 43, width: W - 20, height: 40, borderRadius: 9, boxSizing: "border-box",
        background: i === activo ? P.blueLight : "transparent", display: "flex", alignItems: "center", gap: 16, padding: "0 13px",
        fontFamily: F.body, fontSize: 15, color: i === activo ? P.blue : P.ink, fontWeight: i === activo ? 600 : 400 }}>
        {i < NAV_ICO.length ? <Icono n={NAV_ICO[i]} s={18} c={i === activo ? P.blue : P.ink} w={1.6} /> : <div style={{ width: 18 }} />}
        {n}
      </div>
    ))}
  </div>
);

/** La página Agentes vacía (AgentsPage, vista de cliente). */
const PaginaAgentes: React.FC = () => (
  <>
    <Titulo y={16}>Agentes</Titulo>
    <Texto x={16} y={54} w={W - 32} s={14} c={P.dim} lh={1.45}>Cada agente define qué datos pide, cómo habla y cómo cierra la conversación.</Texto>
    <Boton x={16} y={100} w={150} icono="plus">Nuevo agente</Boton>
    <Tarjeta y={152} h={220}>
      <Interruptor x={20} y={22} on={0} label="Incluir archivados" />
    </Tarjeta>
    <Texto x={30} y={232} w={W - 60} s={14} c={P.dim} lh={1.45} style={{ textAlign: "center" }}>
      No tenés agentes activos. Creá uno y después elegí qué número atiende.
    </Texto>
    <Boton x={123} y={296} w={144} tipo="claro" icono="plus">Crear agente</Boton>
  </>
);

const PaginaInicio: React.FC = () => (
  <>
    <Titulo y={16}>Inicio</Titulo>
    <Texto x={16} y={54} s={14} c={P.dim}>Conversaciones del 24/9/2026 al 23/10/2026</Texto>
    <Boton x={16} y={80} w={184} tipo="borde" icono="messages">Ver conversaciones</Boton>
    <Tarjeta y={148} h={176} />
    <Campo x={36} y={170} w={220} label="Agente" valor="Todos" />
    <Campo x={36} y={243} w={170} label="Período" valor="Último mes" />
    <Tarjeta y={340} h={400} />
    <div style={{ position: "absolute", left: 36, top: 362, display: "flex", gap: 12, alignItems: "center" }}>
      <Icono n="phoneCall" s={20} c={P.ink} /><span style={{ fontFamily: F.display, fontWeight: 700, fontSize: 18 }}>Nueva llamada</span>
    </div>
    <Campo y={400} label="Agente" placeholder="Elegí un agente" />
  </>
);

export const Agentes: React.FC = () => {
  const t = useT();
  const tMenu = en("p2", "abrí") + 0.05;
  const tAg = en("p2", "tocá Agentes") + 0.35;
  const tNuevo = en("p2", "Nuevo agente") + 0.15;
  const menu = interpolate(t, [tMenu + 0.15, tMenu + 0.35, tAg + 0.3, tAg + 0.5], [0, 1, 1, 0], CLAMP);
  const enAgentes = t > tAg + 0.3;
  return (
    <AbsoluteFill>
      <Encabezado rotulo="1 · Agentes" texto="En el menú, Agentes. Después," acento="Nuevo agente." />
      <Telefono aparece={useIn(0, 0.5)}>
        <Pagina scroll={0}>{enAgentes ? <PaginaAgentes /> : <PaginaInicio />}</Pagina>
        <Menu activo={t > tAg ? 3 : 0} o={menu} />
        <Cabecera abierto={menu > 0.5} />
        <Toque x={30} y={30} t={tMenu} />
        <Toque x={110} y={HEADER + 10 + 3 * 43 + 20} t={tAg} />
        <Toque x={91} y={HEADER + 118} t={tNuevo} />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 2. Nuevo agente (zoom al escribir el nombre) ----------

const M = 104; // tope del modal
export const Nuevo: React.FC = () => {
  const t = useT();
  const nombre = useTipeo("Atención al cliente", TIPEO.nombre.desde, TIPEO.nombre.cps);
  const z = useZoom(0.3, nombre.fin + 0.35);
  const tRadio = en("p3", "Asistente básico") + 0.1;
  const tCrear = en("p3", "Crear agente") + 0.25;
  const apretado = interpolate(t, [tCrear - 0.05, tCrear + 0.05, tCrear + 0.25], [0, 1, 0], CLAMP);
  const cierre = 1; // el modal queda hasta el corte: la escena siguiente ya es el agente creado
  // en la pantalla del celular el modal no entra entero: se desplaza para llegar a "Crear agente"
  const sube = useScroll([[tCrear - 0.75, 0.5, 70]]);
  return (
    <AbsoluteFill>
      <Encabezado rotulo="2 · Nuevo agente" texto="Un nombre y el" acento="Asistente básico." />
      <Telefono zoom={{ z, x: W / 2, y: M + 130, k: 1.55 }}>
        <Pagina scroll={0}><PaginaAgentes /></Pagina>
        <Cabecera />
        <Velo o={cierre} />
        <div style={{ position: "absolute", left: 0, top: -sube, width: W, height: VH, zIndex: 30, opacity: cierre }}>
          <Tarjeta x={20} y={M} w={350} h={636} style={{ borderRadius: 16, border: "none", boxShadow: "0 12px 40px rgba(11,18,32,0.25)" }} />
          <Texto x={40} y={M + 24} s={18} peso={700} f={F.display}>Nuevo agente</Texto>
          <div style={{ position: "absolute", left: 333, top: M + 27 }}><Icono n="x" s={20} c={P.ink} w={1.6} /></div>
          <Campo x={40} y={M + 72} w={310} label="Nombre" desc="Para reconocerlo en tus listas e informes." valor={nombre.visto}
            foco={t > 0.3 && t < nombre.fin + 0.6} cursor={t > 0.5 && t < nombre.fin + 0.6} />
          <Campo x={40} y={M + 168} w={310} label="Descripción" desc="Opcional: para qué lo usás." />
          <Texto x={40} y={M + 264} s={14} peso={600}>Punto de partida</Texto>
          <Texto x={40} y={M + 285} w={310} s={12} c={P.dim} lh={1.4}>Después completás cada parte en el formulario de la definición.</Texto>
          <div style={{ position: "absolute", left: 40, top: M + 323, width: 310, height: 150, boxSizing: "border-box", borderRadius: 10,
            border: `1px solid ${P.blue}`, background: P.blueLight }}>
            <div style={{ position: "absolute", left: 13, top: 13, width: 20, height: 20, borderRadius: 10, background: P.blue }}>
              <div style={{ position: "absolute", left: 6, top: 6, width: 8, height: 8, borderRadius: 4, background: "#fff" }} />
            </div>
            <Texto x={44} y={12} s={14} peso={600}>Asistente básico</Texto>
            <Texto x={44} y={34} w={250} s={12} c={P.dim} lh={1.45}>
              Atender a quien se comunica, entender qué necesita y responderle con la base de conocimiento. Si la consulta no se puede
              resolver así, tomar su nombre y un teléfono o mail para que lo contacte una persona del equipo.
            </Texto>
          </div>
          <div style={{ position: "absolute", left: 40, top: M + 483, width: 310, height: 80, boxSizing: "border-box", borderRadius: 10, border: `1px solid ${P.line}`, background: "#fff" }}>
            <div style={{ position: "absolute", left: 13, top: 13, width: 20, height: 20, borderRadius: 10, boxSizing: "border-box", border: `1px solid ${P.input}` }} />
            <Texto x={44} y={12} s={14} peso={600}>En blanco</Texto>
            <Texto x={44} y={34} w={250} s={12} c={P.dim} lh={1.45}>Solo lo mínimo para que sea válido: un dato a obtener y el resultado por defecto.</Texto>
          </div>
          <Boton x={119} y={M + 580} w={94} tipo="borde">Cancelar</Boton>
          <Boton x={229} y={M + 580} w={122} apretado={apretado}>Crear agente</Boton>
          <Toque x={140} y={M + 350} t={tRadio} />
          <Toque x={290} y={M + 598} t={tCrear} />
        </div>
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 3. Definición: voz ----------

const VOCES: [string, string][] = [["Sofía", "Mujer"], ["Jimena", "Mujer"], ["Carolina", "Mujer"], ["Tomás", "Hombre"], ["Lucas", "Hombre"], ["Gabriela", "Mujer"]];
const APERTURA_PLANTILLA = "Hola, gracias por comunicarte. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?";

/** Barra de guardar del formulario (DefinitionTab). */
const BarraGuardar: React.FC<{ y: number; version: number; sucio: boolean; apretado?: number }> = ({ y, version, sucio, apretado = 0 }) => (
  <>
    <Tarjeta y={y} h={88} />
    <Texto x={36} y={y + 14} s={14} c={P.dim} f={F.mono}>v{version}</Texto>
    {sucio ? <Insignia x={66} y={y + 15} bg={P.yellowSoft} fg={P.yellow}>Cambios sin guardar</Insignia> : null}
    <Insignia x={sucio ? 212 : 66} y={y + 15} bg={P.okSoft} fg={P.ok}>Válida</Insignia>
    <Boton x={36} y={y + 44} w={84} h={30} s={13} tipo={sucio ? "borde" : "apagado"}>Descartar</Boton>
    <Boton x={130} y={y + 44} w={174} h={30} s={13} tipo={sucio ? "primario" : "apagado"} icono="save" apretado={apretado}>Guardar versión nueva</Boton>
  </>
);

const Y_VOZ = 800;
export const Voz: React.FC = () => {
  const t = useT();
  const toast = interpolate(t, [0, 0.25, 2.0, 2.3], [0, 1, 1, 0], CLAMP);
  const tCard = en("p4", "Elegí") + 0.2;
  const tPlay = en("p4", "escuchala") + 0.25;
  const scroll = useScroll([[1.5, 1.0, Y_VOZ - 10], [tPlay - 0.6, 0.45, Y_VOZ + 90]]);
  const prog = interpolate(t, [tPlay, tPlay + 6], [0, 1], CLAMP);
  const sonando = t > tPlay;
  const pulso = interpolate(t, [tCard, tCard + 0.15, tCard + 0.4], [0, 1, 0], CLAMP);
  const V = Y_VOZ;
  return (
    <AbsoluteFill>
      <Encabezado rotulo="3 · Definición · Voz" texto="Elegí la voz" acento="y escuchala." />
      <Telefono>
        <Pagina scroll={scroll}>
          <DetalleAgente y={0} version={1} tab="definicion" />
          <BarraGuardar y={324} version={1} sucio={false} />
          <Tarjeta y={428} h={356} />
          <TituloTarjeta y={450} t="Agente" desc="Quién es y cómo responde. El prompt se arma de estos campos." />
          <Campo y={516} label="Nombre" desc="Cómo se presenta." valor="Sofía" />
          <Campo y={600} label="Rol" desc="Quién es y para quién trabaja." valor="asistente virtual de la empresa, en Argentina" />
          <Campo y={684} label="Idioma" desc="Código, como es-AR." valor="es-AR" />
          <Tarjeta y={V} h={640} />
          <TituloTarjeta y={V + 22} t="Voz" desc="Con la que habla en las llamadas y las notas de voz. Elegila y escuchala acá mismo." />
          <div style={{ position: "absolute", left: 36, top: V + 86, height: 30, borderRadius: 9, background: "#eef1f5", display: "flex", alignItems: "center",
            padding: "0 4px", gap: 4, fontFamily: F.body, fontSize: 13, color: P.ink2 }}>
            <span style={{ background: "#fff", borderRadius: 7, padding: "4px 10px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>Todas (41)</span>
            <span style={{ padding: "4px 8px" }}>Mujeres (28)</span>
            <span style={{ padding: "4px 8px" }}>Hombres (13)</span>
          </div>
          {VOCES.map(([n, g], i) => {
            const x = 36 + (i % 2) * 163;
            const y = V + 132 + Math.floor(i / 2) * 76;
            const sel = i === 0;
            return (
              <div key={n} style={{ position: "absolute", left: x, top: y, width: 153, height: 66, boxSizing: "border-box", borderRadius: 10,
                border: `1px solid ${sel ? P.blue : P.line}`, background: sel ? P.blueLight : "#fff", transform: sel ? `scale(${1 + 0.04 * pulso})` : undefined }}>
                <div style={{ position: "absolute", left: 10, top: 15, width: 36, height: 36, borderRadius: 18, background: sel ? P.blue : "#e9edf3",
                  color: sel ? "#fff" : P.ink, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.body, fontWeight: 700, fontSize: 15 }}>{n[0]}</div>
                <Texto x={58} y={11} s={14} peso={600}>{n}</Texto>
                <Insignia x={58} y={35} bg="#eef1f5" fg={P.ink2}>{g}</Insignia>
              </div>
            );
          })}
          <Texto x={46} y={V + 368} s={14} c={P.blue} peso={600}>Ver todas (41)</Texto>
          <div style={{ position: "absolute", left: 36, top: V + 402, width: W - 72, height: 214, boxSizing: "border-box", borderRadius: 12, border: `1px solid ${P.line}` }}>
            <Texto x={14} y={12} s={18} peso={800} f={F.display}>Sofía</Texto>
            <Insignia x={232} y={16} bg="#eef1f5" fg={P.ink2}>Mujer</Insignia>
            <Texto x={14} y={48} s={14} peso={600}>Prueba de voz</Texto>
            <Texto x={14} y={68} s={12} c={P.dim}>93/600 caracteres</Texto>
            <Campo x={14} y={88} w={288} valor={APERTURA_PLANTILLA} alto={76} s={13} />
            <div style={{ position: "absolute", left: 14, top: 174, width: 30, height: 30, borderRadius: 15, background: P.blue, display: "flex", alignItems: "center", justifyContent: "center" }}>
              {sonando ? <div style={{ display: "flex", gap: 4 }}><div style={{ width: 3, height: 11, background: "#fff" }} /><div style={{ width: 3, height: 11, background: "#fff" }} /></div>
                : <Icono n="play" s={14} c="#fff" />}
            </div>
            <div style={{ position: "absolute", left: 54, top: 187, width: 170, height: 4, borderRadius: 2, background: "#e3e8ef" }}>
              <div style={{ width: `${prog * 100}%`, height: 4, borderRadius: 2, background: P.blue }} />
            </div>
            <Texto x={234} y={180} s={12} c={P.dim} f={F.mono}>{`0:0${Math.min(6, Math.floor(prog * 6))} / 0:06`}</Texto>
          </div>
          <Toque x={110} y={V + 165} t={tCard} />
          <Toque x={65} y={V + 591} t={tPlay} />
        </Pagina>
        <Cabecera />
        <Aviso texto="Agente Atención al cliente creado." o={toast} />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 4. Definición: apertura (zoom al escribir) ----------

const OBJETIVO = "Atender a quien se comunica, entender qué necesita y responderle con la base de conocimiento. Si la consulta no se puede resolver así, tomar su nombre y un teléfono o mail para que lo contacte una persona del equipo.";
export const APERTURA = "Hola, gracias por llamar a Casa Norte. Te habla Sofía. ¿En qué te puedo ayudar?";

/** Texto viejo que se selecciona y se reemplaza por el que se escribe. */
const useReemplazo = (viejo: string, nuevo: string, desde: number, cps: number) => {
  const t = useT();
  const tip = useTipeo(nuevo, desde, cps);
  const seleccionado = t > desde - 0.4 && t < desde;
  return { valor: t < desde ? viejo : tip.visto, seleccionado, fin: tip.fin };
};

const Seleccion: React.FC<{ texto: string; on: boolean }> = ({ texto, on }) =>
  on ? <span style={{ background: "rgba(36,86,230,0.25)" }}>{texto}</span> : <>{texto}</>;

export const Apertura: React.FC = () => {
  const t = useT();
  const A = 16; // tope de la tarjeta
  const r = useReemplazo(APERTURA_PLANTILLA, APERTURA, TIPEO.apertura.desde, TIPEO.apertura.cps);
  const z = useZoom(0.35, r.fin + 0.3);
  const enFoco = t > 0.35 && t < r.fin + 0.5;
  return (
    <AbsoluteFill>
      <Encabezado rotulo="3 · Definición · Apertura" texto="Lo primero que dice" acento="cuando atiende." />
      <Telefono zoom={{ z, x: W / 2, y: HEADER + A + 340, k: 1.55 }}>
        <Pagina scroll={0}>
          <Tarjeta y={A} h={560} />
          <TituloTarjeta y={A + 22} t="Objetivo y apertura" />
          <Campo y={A + 60} label="Objetivo" desc="Qué tiene que lograr en la conversación." valor={OBJETIVO} alto={140} />
          <Campo y={A + 248} label="Apertura" desc="Lo primero que dice al atender o al llamar. Por WhatsApp es la guía del saludo." descLineas={2}
            valor={r.seleccionado ? undefined : r.valor} alto={62} foco={enFoco} cursor={enFoco && !r.seleccionado} />
          {r.seleccionado ? (
            <div style={{ position: "absolute", left: 49, top: A + 248 + 63, width: W - 98, fontFamily: F.body, fontSize: 14, lineHeight: 1.55, color: P.ink }}>
              <Seleccion texto={APERTURA_PLANTILLA} on />
            </div>
          ) : null}
          <Interruptor x={36} y={A + 386} on={0} label="Pregenerar el audio de la apertura" w={270}
            desc="En las llamadas, la apertura se sintetiza entera al guardar (suena más natural que frase por frase) y se reproduce ese audio." />
          <Campo y={A + 470} label="Espera antes de la apertura (ms)" desc="En las llamadas, cuánto espera desde que se conecta hasta que empieza a hablar." descLineas={2} valor="200" />
        </Pagina>
        <Cabecera />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 5. Definición: base de conocimiento (zoom al escribir) ----------

const BASE_PLANTILLA = "- La empresa: nombre, a qué se dedica, dirección y horarios de atención.\n- Preguntas frecuentes: las respuestas que el agente puede dar, una por línea.";
export const BASE = "- Casa Norte: artículos para el hogar.\n- Horarios: de lunes a viernes, de 9 a 18.\n- Dirección: Av. Colón 1234, Córdoba.\n- Envíos: a todo el país, en 48 horas.\n- Cambios: hasta 30 días, con el ticket.";

export const Conocimiento: React.FC = () => {
  const t = useT();
  const B = 16;
  const r = useReemplazo(BASE_PLANTILLA, BASE, TIPEO.conocimiento.desde, TIPEO.conocimiento.cps);
  const z = useZoom(0.35, r.fin + 0.3);
  const enFoco = t > 0.35 && t < r.fin + 0.5;
  return (
    <AbsoluteFill>
      <Encabezado rotulo="3 · Definición · Conocimiento" texto="Lo que sabe tu agente," acento="y nada más." />
      <Telefono zoom={{ z, x: W / 2, y: HEADER + B + 186, k: 1.5 }}>
        <Pagina scroll={0}>
          <Tarjeta y={B} h={312} />
          <TituloTarjeta y={B + 22} t="Base de conocimiento"
            desc="Lo único que el agente sabe del negocio: productos, precios, horarios, direcciones, preguntas frecuentes. Lo que no esté acá, no lo responde." />
          <Campo y={B + 106} valor={r.seleccionado ? undefined : r.valor} alto={180} foco={enFoco} cursor={enFoco && !r.seleccionado} />
          {r.seleccionado ? (
            <div style={{ position: "absolute", left: 49, top: B + 115, width: W - 98, fontFamily: F.body, fontSize: 14, lineHeight: 1.55, color: P.ink, whiteSpace: "pre-wrap" }}>
              <Seleccion texto={BASE_PLANTILLA} on />
            </div>
          ) : null}
          <Tarjeta y={B + 328} h={300} />
          <TituloTarjeta y={B + 350} t="Datos a obtener"
            desc="Lo que el agente pregunta, en este orden salvo que la persona los dé antes." />
          <Boton x={228} y={B + 344} w={126} h={30} s={13} tipo="borde" icono="plus">Agregar dato</Boton>
          <div style={{ position: "absolute", left: 36, top: B + 420, width: W - 72, height: 120, boxSizing: "border-box", borderRadius: 12, border: `1px solid ${P.line}` }}>
            <Texto x={14} y={12} s={16} peso={700} f={F.display}>1 <span style={{ marginLeft: 6 }}>Consulta</span> <span style={{ fontFamily: F.mono, fontWeight: 500, fontSize: 13, color: P.dim, marginLeft: 6 }}>consulta</span></Texto>
          </div>
        </Pagina>
        <Cabecera />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 6. Guardar ----------

export const Guardar: React.FC = () => {
  const t = useT();
  const tG = en("p7", "Guardar") + 0.25;
  const guardado = t > tG + 0.2;
  const apretado = interpolate(t, [tG - 0.05, tG + 0.05, tG + 0.25], [0, 1, 0], CLAMP);
  const toast = interpolate(t, [tG + 0.25, tG + 0.5], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Encabezado rotulo="4 · Guardar" texto="Cada cambio queda como una" acento="versión nueva." />
      <Telefono>
        <Pagina scroll={0}>
          <DetalleAgente y={0} version={guardado ? 2 : 1} tab="definicion" />
          <BarraGuardar y={324} version={guardado ? 2 : 1} sucio={!guardado} apretado={apretado} />
          <Tarjeta y={428} h={356} />
          <TituloTarjeta y={450} t="Agente" desc="Quién es y cómo responde. El prompt se arma de estos campos." />
          <Campo y={516} label="Nombre" desc="Cómo se presenta." valor="Sofía" />
          <Toque x={217} y={324 + 59} t={tG} />
        </Pagina>
        <Cabecera />
        <Aviso texto="Versión 2 guardada." o={toast} />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 7. Probar ----------

const L = 582; // tope de la tarjeta "Llamada con este agente"

/** Pestaña Probar (TestTab + NewCallForm), con el modo prueba prendido o no. */
const PestanaProbar: React.FC<{ modo: boolean; apretado?: number; alerta?: number }> = ({ modo, apretado = 0, alerta = 0 }) => {
  const d = modo ? 0 : 74; // con el modo prueba se oculta "Número de origen"
  return (
    <>
      <div style={{ position: "absolute", left: 16, top: 330 }}><Icono n="history" s={16} c={P.blue} w={1.8} /></div>
      <Texto x={16} y={350} w={W - 32} s={14} c={P.blue} lh={1.45}>Ver conversaciones de este agente (incluidas las pruebas)</Texto>
      <Tarjeta y={408} h={158} />
      <TituloTarjeta y={430} t="Conversación por texto" desc="Probá el agente escribiendo, sin llamada ni voz. Queda registrada como conversación de origen API." />
      <Boton x={36} y={510} w={182} tipo="borde">Empezar conversación</Boton>
      <Tarjeta y={L} h={(alerta > 0 ? 1000 : 840) + d} />
      <TituloTarjeta y={L + 22} t="Llamada con este agente" />
      <Interruptor x={36} y={L + 62} on={modo ? 1 : 0} label="Modo prueba" desc="Sin teléfono real: te conectás por navegador y hacés de interesado." w={270} />
      <Campo y={L + 122} label="Teléfono" placeholder={modo ? "(no hace falta en modo prueba)" : "+5491155551234"} apagado={modo} />
      {!modo ? <Campo y={L + 196} label="Número de origen" placeholder="El cliente no tiene números" apagado /> : null}
      <Campo y={L + 196 + d} label="Voz" valor="La del agente (sofia)" />
      <Campo y={L + 270 + d} w={120} label="Género" valor="Todas" s={13} />
      <Campo x={166} y={L + 270 + d} w={110} label="WER máx. (%)" />
      <Texto x={36} y={L + 340 + d} w={W - 72} s={12} c={P.dim} lh={1.4}>WER: errores del ASR sobre frases de dominio (menos es más claro). car/s: velocidad del habla. 41 voces con estos filtros.</Texto>
      <Texto x={36} y={L + 400 + d} s={14} peso={600}>Prueba de voz</Texto>
      <Texto x={36} y={L + 421 + d} s={12} c={P.dim}>93/600 caracteres</Texto>
      <Campo y={L + 440 + d} valor={APERTURA} alto={70} s={13} />
      <div style={{ position: "absolute", left: 36, top: L + 522 + d, width: 30, height: 30, borderRadius: 15, background: P.blue, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icono n="play" s={14} c="#fff" />
      </div>
      <div style={{ position: "absolute", left: 78, top: L + 535 + d, width: 200, height: 4, borderRadius: 2, background: "#e3e8ef" }} />
      <Boton x={36} y={L + 580 + d} w={212} icono="phoneCall" apretado={apretado}>{modo ? "Crear llamada de prueba" : "Llamar"}</Boton>
      <Texto x={36} y={L + 628 + d} w={W - 72} s={12} c={P.dim} lh={1.4}>
        {modo ? "Se crea la llamada sin marcar ningún teléfono. Te aparece un link para conectarte por navegador (LiveKit Meet) y hablar con el agente."
          : "Llamada saliente: el agente marca el número (formato E.164, ej. +5491155551234)."}
      </Texto>
      {alerta > 0 ? (
        <div style={{ position: "absolute", left: 36, top: L + 700, width: W - 72, height: 156, boxSizing: "border-box", borderRadius: 12, background: P.okSoft,
          opacity: alerta, transform: `translateY(${(1 - alerta) * 10}px)` }}>
          <div style={{ position: "absolute", left: 16, top: 18 }}><Icono n="check" s={18} c={P.ok} /></div>
          <Texto x={52} y={17} s={14} peso={700} c={P.ok}>Llamada de prueba creada</Texto>
          <Texto x={52} y={44} w={240} s={16} peso={600} c={P.blue} lh={1.3}>Conectate acá para hablar con el agente</Texto>
          <Texto x={52} y={94} s={12} c={P.dim}>Abrilo ahora: el link no se vuelve a mostrar.</Texto>
          <Texto x={52} y={118} s={14} c={P.blue}>Ver en vivo</Texto>
        </div>
      ) : null}
    </>
  );
};

export const Probar: React.FC = () => {
  const t = useT();
  const tTab = en("p8", "andá a Probar") + 0.35;
  const tModo = en("p8", "activá") + 0.3;
  const tCrear = en("p8", "tocá Crear") + 0.45;
  const scroll = useScroll([[tTab + 0.35, 0.8, L - 20], [tModo + 0.35, 0.7, L + 400]]);
  const apretado = interpolate(t, [tCrear - 0.05, tCrear + 0.05, tCrear + 0.25], [0, 1, 0], CLAMP);
  const alerta = interpolate(t, [tCrear + 0.35, tCrear + 0.6], [0, 1], CLAMP);
  const enProbar = t > tTab + 0.1;
  return (
    <AbsoluteFill>
      <Encabezado rotulo="5 · Probar" texto="Una llamada de prueba," acento="sin teléfono." />
      <Telefono>
        <Pagina scroll={scroll}>
          <DetalleAgente y={0} version={2} tab={enProbar ? "probar" : "definicion"} />
          {enProbar ? <PestanaProbar modo={t > tModo} apretado={apretado} alerta={alerta} /> : <BarraGuardar y={324} version={2} sucio={false} />}
          <Toque x={200} y={188 + 42 + 18} t={tTab} />
          <Toque x={55} y={L + 72} t={tModo} />
          <Toque x={142} y={L + 598} t={tCrear} />
        </Pagina>
        <Cabecera />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 8. La llamada desde el navegador (pantalla genérica) ----------

type Globo = { quien: "agente" | "vos"; texto: string; t: number; d: number };

const Burbuja: React.FC<{ g: Globo; y: number }> = ({ g, y }) => {
  const o = useIn(g.t, 0.35);
  const agente = g.quien === "agente";
  return (
    <div style={{ position: "absolute", top: y, left: agente ? 20 : 92, width: 278, boxSizing: "border-box", padding: "9px 13px", borderRadius: 14,
      background: agente ? "#fff" : P.blueLight, border: `1px solid ${agente ? P.line : P.blueLight}`, opacity: o, transform: `translateY(${(1 - o) * 10}px)`,
      fontFamily: F.body, fontSize: 14, lineHeight: 1.4, color: P.ink }}>
      <div style={{ fontFamily: F.mono, fontSize: 10, letterSpacing: "0.06em", color: P.dim, marginBottom: 3 }}>{agente ? "AGENTE" : "VOS"}</div>
      {g.texto}
    </div>
  );
};

export const Llamada: React.FC = () => {
  const t = useT();
  const tLink = en("p9", "Abrí el link") + 0.3;
  const tPermitir = en("p9", "permití") + 0.35;
  const navegador = interpolate(t, [tLink + 0.25, tLink + 0.55], [0, 1], CLAMP);
  const permiso = interpolate(t, [tLink + 0.6, tLink + 0.85, tPermitir + 0.15, tPermitir + 0.35], [0, 1, 1, 0], CLAMP);
  const t0 = tPermitir + 0.6;
  const globos: Globo[] = [
    { quien: "agente", texto: APERTURA, t: t0, d: 2.2 },
    { quien: "vos", texto: "¿Hasta qué hora atienden hoy?", t: t0 + 2.4, d: 1.2 },
    { quien: "agente", texto: "Hoy atendemos hasta las seis de la tarde. ¿Te ayudo con algo más?", t: t0 + 3.8, d: 2.0 },
  ];
  const habla = globos.some((g) => g.quien === "agente" && t > g.t && t < g.t + g.d) ? 0.8 : 0;
  const vosHabla = globos.some((g) => g.quien === "vos" && t > g.t && t < g.t + g.d);
  const segundos = Math.max(0, Math.floor(t - t0 + 1));
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Encabezado rotulo="5 · Probar · La llamada" texto="Hablale como si fueras" acento="un cliente." />
      <Telefono>
        <Pagina scroll={L + 400}>
          <DetalleAgente y={0} version={2} tab="probar" />
          <PestanaProbar modo alerta={1} />
          <Toque x={170} y={L + 744} t={tLink} />
        </Pagina>
        <Cabecera />
        {/* El link abre la sala de prueba en el navegador: acá, una pantalla genérica de llamada */}
        <div style={{ position: "absolute", left: 0, top: 0, width: W, height: VH, background: "#fff", opacity: navegador, zIndex: 30 }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: W, height: 46, background: "#f1f4f9", borderBottom: `1px solid ${P.line}` }}>
            <Texto x={0} y={14} w={W} s={13} c={P.dim} style={{ textAlign: "center" }}>Llamada de prueba</Texto>
          </div>
          <div style={{ position: "absolute", left: 0, top: 70, width: W, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
            <AgenteLogo size={104} talk={habla} />
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 20, color: P.ink }}>Atención al cliente</div>
            <div style={{ fontFamily: F.mono, fontSize: 13, color: t > t0 ? P.ok : P.dim }}>
              {t > t0 ? `EN LLAMADA · 0:${String(segundos).padStart(2, "0")}` : "CONECTANDO…"}
            </div>
          </div>
          {globos.map((g, i) => <Burbuja key={i} g={g} y={[262, 362, 420][i]} />)}
          <div style={{ position: "absolute", left: 0, top: VH - 86, width: W, display: "flex", justifyContent: "center", gap: 26 }}>
            <div style={{ width: 54, height: 54, borderRadius: 27, background: vosHabla ? P.blue : "#e9edf3", display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: vosHabla ? `0 0 0 ${6 + 3 * Math.abs(Math.sin(frame / 4))}px rgba(36,86,230,0.18)` : undefined }}>
              <Icono n="mic" s={24} c={vosHabla ? "#fff" : P.ink} />
            </div>
            <div style={{ width: 54, height: 54, borderRadius: 27, background: "#d92d20", display: "flex", alignItems: "center", justifyContent: "center", transform: "rotate(135deg)" }}>
              <Icono n="phoneCall" s={24} c="#fff" />
            </div>
          </div>
          {/* Pedido del micrófono (genérico, no imita a ningún navegador) */}
          <div style={{ position: "absolute", left: 30, top: 150, width: W - 60, height: 128, boxSizing: "border-box", borderRadius: 14, background: "#fff",
            boxShadow: "0 12px 36px rgba(11,18,32,0.22)", border: `1px solid ${P.line}`, opacity: permiso, transform: `scale(${0.95 + 0.05 * permiso})` }}>
            <div style={{ position: "absolute", left: 18, top: 18, display: "flex", gap: 10, alignItems: "center" }}>
              <Icono n="mic" s={20} c={P.ink} />
              <span style={{ fontFamily: F.body, fontSize: 15, fontWeight: 600, color: P.ink }}>Usar tu micrófono</span>
            </div>
            <Boton x={70} y={74} w={110} tipo="borde">Bloquear</Boton>
            <Boton x={190} y={74} w={110}>Permitir</Boton>
            <Toque x={245} y={92} t={tPermitir} />
          </div>
        </div>
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 9. Conversaciones ----------

const Item: React.FC<{ x: number; y: number; k: string; children: React.ReactNode }> = ({ x, y, k, children }) => (
  <>
    <Texto x={x} y={y} s={12} c={P.dim}>{k}</Texto>
    <div style={{ position: "absolute", left: x, top: y + 18 }}>{children}</div>
  </>
);

const CHAT: [boolean, string][] = [
  [true, APERTURA],
  [false, "¿Hasta qué hora atienden hoy?"],
  [true, "Hoy atendemos hasta las seis de la tarde. ¿Te ayudo con algo más?"],
  [false, "No, eso era todo. Gracias."],
  [true, "Gracias por comunicarte, que tengas un buen día."],
];

export const Conversaciones: React.FC = () => {
  const scroll = useScroll([[1.6, 1.4, 250]]);
  const ins = CHAT.map((_, i) => useIn(0.5 + i * 0.25, 0.4));
  let y = 330 + 64;
  const alturas = [92, 52, 72, 52, 72];
  return (
    <AbsoluteFill>
      <Encabezado rotulo="6 · Conversaciones" texto="Todo lo que se dijo," acento="queda guardado." />
      <Telefono>
        <Pagina scroll={scroll}>
          <div style={{ position: "absolute", left: 22, top: 14, display: "flex", alignItems: "center", gap: 10, color: P.blue, fontFamily: F.body, fontWeight: 600, fontSize: 14 }}>
            <Icono n="arrowLeft" s={16} c={P.blue} /> Conversaciones
          </div>
          <Titulo y={42}>Conversación</Titulo>
          <Insignia x={200} y={52} bg={P.okSoft} fg={P.ok}>Completo</Insignia>
          <Tarjeta y={96} h={218} />
          <Item x={36} y={116} k="Origen"><Insignia x={0} y={0} bg="#eef1f5" fg={P.ink2}>Prueba</Insignia></Item>
          <Item x={206} y={116} k="Estado"><Insignia x={0} y={0} bg={P.okSoft} fg={P.ok}>Finalizada</Insignia></Item>
          <Item x={36} y={176} k="Fecha"><span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" }}>23/10/2026, 10:21</span></Item>
          <Item x={206} y={176} k="Resultado"><Insignia x={0} y={0} bg={P.okSoft} fg={P.ok}>Consulta resuelta</Insignia></Item>
          <Item x={36} y={236} k="Agente"><span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 14, color: P.blue, whiteSpace: "nowrap" }}>Atención al cliente</span></Item>
          <Tarjeta y={330} h={470} />
          <Texto x={36} y={350} s={18} peso={700} f={F.display}>Conversación</Texto>
          {CHAT.map(([agente, texto], i) => {
            const top = y;
            y += alturas[i] + 10;
            return (
              <div key={i} style={{ position: "absolute", top, left: agente ? 36 : 96, width: 258, boxSizing: "border-box", padding: "8px 12px", borderRadius: 12,
                background: agente ? "#f1f4f9" : P.blueLight, opacity: ins[i], fontFamily: F.body, fontSize: 13.5, lineHeight: 1.4, color: P.ink }}>
                <div style={{ fontFamily: F.mono, fontSize: 10, letterSpacing: "0.06em", color: P.dim, marginBottom: 2 }}>{agente ? "AGENTE IA" : "INTERESADO"}</div>
                {texto}
              </div>
            );
          })}
        </Pagina>
        <Cabecera />
      </Telefono>
    </AbsoluteFill>
  );
};

// ---------- 10. Cierre ----------

export const Cierre: React.FC = () => {
  const t1 = useIn(0.2, 0.7);
  const remate = useIn(en("p11", "Cada cambio") - 0.1, 0.6);
  const logo = useIn(2.2, 0.6);
  const pasos = ["Agentes · Nuevo agente", "Definición: voz, apertura y conocimiento", "Guardar versión nueva", "Probar · Modo prueba"];
  const ins = pasos.map((_, i) => useIn(0.9 + i * 0.25, 0.5));
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 80, right: 80, top: 380, fontFamily: F.display, fontWeight: 800, fontSize: 88, lineHeight: 1.06, color: C.ctaInk,
        opacity: t1, transform: `translateY(${(1 - t1) * 24}px)`, letterSpacing: "-0.015em" }}>
        Ajustalo y probalo <span style={{ color: C.accentOnDark }}>las veces que quieras.</span>
      </div>
      <div style={{ position: "absolute", left: 80, right: 80, top: 720, display: "flex", flexDirection: "column", gap: 22 }}>
        {pasos.map((p, i) => (
          <div key={p} style={{ display: "flex", alignItems: "center", gap: 24, opacity: ins[i], transform: `translateX(${(1 - ins[i]) * -20}px)` }}>
            <div style={{ width: 56, height: 56, borderRadius: 28, background: "#16213a", border: "2px solid #23304d", color: C.accentOnDark,
              display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.mono, fontSize: 26 }}>{i + 1}</div>
            <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 38, color: C.ctaInk }}>{p}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 80, right: 80, top: 1110, fontFamily: F.body, fontSize: 36, color: C.ctaMuted, opacity: remate, lineHeight: 1.35 }}>
        Cada cambio queda guardado como una versión.
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1480, display: "flex", flexDirection: "column", alignItems: "center", gap: 26, opacity: logo }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 340 }} />
        <div style={{ fontFamily: F.mono, fontSize: 28, color: C.ctaMuted, letterSpacing: "0.04em" }}>atentina.com.ar · hola@atentina.com.ar</div>
      </div>
    </AbsoluteFill>
  );
};

