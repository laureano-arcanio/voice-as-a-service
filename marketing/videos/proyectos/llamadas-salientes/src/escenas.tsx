import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { Dato, Nota, Ruta, Shot, useT } from "./piezas";

// Marco de las capturas del panel (16:9) y columna de la derecha
const S = { left: 80, top: 258, w: 1260, h: 709 };
const COL = 1390;

/** Paso del tutorial: los cuatro, para la intro y el cierre. */
const PASOS = ["El número", "El equipo", "Los contactos", "El teléfono"];

const PasoChip: React.FC<{ n: number; t: string; p: number }> = ({ n, t, p }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 14, background: "#16213a", border: "2px solid #23304d", borderRadius: 18, padding: "14px 24px",
    transform: `scale(${p})`, opacity: Math.min(1, p * 1.4) }}>
    <span style={{ width: 40, height: 40, borderRadius: 20, background: C.accent, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.display, fontWeight: 800, fontSize: 24 }}>{n}</span>
    <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 30, color: C.ctaInk }}>{t}</span>
  </div>
);

/** 0. Intro oscura: qué se va a hacer y los cuatro pasos. */
export const Intro: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.8, 0.7);
  const chips = [usePop(6.9), usePop(7.6), usePop(8.2), usePop(9.0)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.1, 0.5) }}>
        TUTORIAL · LLAMADAS DEL EQUIPO
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 215, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 460 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 390, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 74, lineHeight: 1.08,
        color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em" }}>
        Llamadas salientes<br /><span style={{ color: C.accentOnDark }}>con el número de tu empresa.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 660, display: "flex", justifyContent: "center", gap: 20 }}>
        {PASOS.map((t, i) => <PasoChip key={t} n={i + 1} t={t} p={chips[i]} />)}
      </div>
    </AbsoluteFill>
  );
};

/** 1. El número: el administrador lo asigna y aparece en el panel del cliente. */
export const Numero: React.FC = () => (
  <AbsoluteFill>
    <Headline eyebrow="Paso 1 de 4 · El número" text="Un número asignado" accent="a tu cuenta." />
    <Shot src="01-admin-numeros.png" {...S} a={0.3} b={2.9} cam={[[0.3, 1, 0.5, 0.5], [1.2, 1.7, 0.9, 0.3], [2.9, 1.8, 0.9, 0.32]]}
      rings={[{ x: 1722, y: 345, w: 106, h: 42, a: 1.3, b: 2.9 }]} />
    <Shot src="02-asignar.png" {...S} a={2.7} b={4.9} cam={[[2.7, 1, 0.5, 0.5], [4.9, 1.5, 0.5, 0.52]]}
      rings={[{ x: 720, y: 497, w: 480, h: 43, a: 3.0, b: 4.9 }]} />
    <Shot src="03-cuenta-numeros.png" {...S} a={4.7} b={10.4} cam={[[4.7, 1, 0.5, 0.5], [5.8, 1.3, 0.45, 0.33], [10.4, 1.4, 0.45, 0.33]]}
      rings={[{ x: 323, y: 285, w: 1090, h: 115, a: 5.2, b: 10.4 }]} />
    <Ruta n={1} titulo="El administrador asigna el número" ruta="Administración › Números › Asignar" a={0.5} b={4.7} left={COL} top={290} />
    <Ruta n={2} titulo="Aparece en tu panel" ruta="Cuenta › Números" a={4.7} b={10.4} left={COL} top={470} />
    <Dato at={6.9} left={COL} top={660} tone="ok">Con ese número ya podés llamar.</Dato>
  </AbsoluteFill>
);

/** 2. El equipo: una persona con su teléfono y su usuario, y el número atendido por el equipo. */
export const Equipo: React.FC = () => (
  <AbsoluteFill>
    <Headline eyebrow="Paso 2 de 4 · El equipo" text="Cada persona, con su teléfono" accent="y su usuario." />
    <Shot src="04-equipo-nueva.png" {...S} a={0.3} b={6.5} cam={[[0.3, 1, 0.5, 0.5], [1.3, 1.45, 0.5, 0.38], [4.4, 1.45, 0.5, 0.38], [5.0, 1.5, 0.5, 0.62], [6.5, 1.5, 0.5, 0.62]]}
      rings={[{ x: 720, y: 268, w: 480, h: 185, a: 2.0, b: 4.7 }, { x: 720, y: 608, w: 480, h: 110, a: 4.7, b: 6.5 }]} />
    <Shot src="06-numero-equipo.png" {...S} a={6.2} b={13.0} cam={[[6.2, 1, 0.5, 0.5], [7.0, 1.4, 0.5, 0.4], [8.3, 1.4, 0.5, 0.4], [9.0, 1.4, 0.5, 0.52], [13.0, 1.4, 0.5, 0.52]]}
      rings={[{ x: 612, y: 272, w: 700, h: 62, a: 6.9, b: 8.6 }, { x: 612, y: 498, w: 696, h: 132, a: 8.6, b: 13.0 }]} />
    <Ruta n={1} titulo="Agregás a cada persona" ruta="Agenda › Equipo › Agregar persona" a={0.5} b={6.2} left={COL} top={290} />
    <Ruta n={2} titulo="El equipo atiende el número" ruta="Cuenta › Números › Editar › El equipo" a={6.2} b={13.0} left={COL} top={470} />
    <Dato at={10.2} left={COL} top={660}>Así también reciben las entrantes.</Dato>
  </AbsoluteFill>
);

/** 3. Los contactos. */
export const Contactos: React.FC = () => (
  <AbsoluteFill>
    <Headline eyebrow="Paso 3 de 4 · Los contactos" text="Tu agenda," accent="lista para llamar." />
    <Shot src="07-contacto-nuevo.png" {...S} a={0.3} b={6.6} cam={[[0.3, 1, 0.5, 0.5], [1.5, 1.5, 0.5, 0.5], [6.6, 1.55, 0.5, 0.52]]}
      rings={[{ x: 612, y: 388, w: 696, h: 166, a: 4.3, b: 6.6 }]} />
    <Shot src="08-contactos-lista.png" {...S} a={6.2} b={10.4} cam={[[6.2, 1, 0.5, 0.5], [7.2, 1.3, 0.62, 0.3], [10.4, 1.35, 0.62, 0.3]]}
      rings={[{ x: 1517, y: 111, w: 176, h: 42, a: 6.7, b: 10.4 }]} />
    <Ruta n={1} titulo="Cargás un contacto" ruta="Agenda › Contactos › Nuevo contacto" a={0.5} b={6.4} left={COL} top={290} />
    <Ruta n={2} titulo="O importás varios" ruta="Agenda › Contactos › Importar" a={6.4} b={10.4} left={COL} top={470} />
  </AbsoluteFill>
);

/** 4. Llamar desde el panel (y la nota de que queda grabado). */
export const Panel: React.FC = () => {
  const t = useT();
  const rec = useIn(11.3, 0.5);
  const dot = 0.5 + 0.5 * Math.abs(Math.sin(t * 3));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Paso 4 de 4 · El teléfono" text="Elegís un contacto" accent="y tocás Llamar." />
      <Shot src="09-telefono.png" {...S} a={0.3} b={16.2} fadeIn={0.5}
        cam={[[0.3, 1, 0.5, 0.5], [1.2, 1.5, 0.33, 0.4], [3.2, 1.5, 0.33, 0.4], [3.9, 1.4, 0.4, 0.6], [4.6, 1.4, 0.4, 0.6], [5.4, 1.6, 0.8, 0.25], [7.0, 1.6, 0.8, 0.25], [8.4, 1, 0.5, 0.5], [16.2, 1.08, 0.5, 0.5]]}
        rings={[
          { x: 33, y: 388, w: 232, h: 48, a: 1.4, b: 3.3 },
          { x: 323, y: 577, w: 741, h: 62, a: 3.4, b: 5.0 },
          { x: 1752, y: 218, w: 123, h: 42, a: 4.8, b: 7.0 },
        ]} />
      <Ruta n={1} titulo="Abrís el teléfono" ruta="Canales › Teléfono del equipo" a={1.4} b={3.4} left={COL} top={290} />
      <Ruta n={2} titulo="Elegís y llamás" ruta="Contacto › Llamar" a={3.4} b={7.4} left={COL} top={440} />
      <Dato at={6.0} out={11.0} left={COL} top={590}>Hablás desde el navegador, mejor con auriculares.</Dato>
      <Dato at={8.3} out={11.0} left={COL} top={720} w={440}>Tu contacto ve el número de tu empresa.</Dato>
      <div style={{ position: "absolute", left: COL, top: 590, width: 440, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 24, padding: "18px 24px",
        boxShadow: shadowCard, opacity: rec, transform: `translateY(${(1 - rec) * 16}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <span style={{ width: 16, height: 16, borderRadius: 8, background: C.warn, opacity: dot }} />
          <span style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.warn }}>SIEMPRE</span>
        </div>
        {["Se graba", "Se transcribe", "Queda en Conversaciones"].map((x, i) => (
          <div key={x} style={{ display: "flex", alignItems: "center", gap: 12, padding: "6px 0", opacity: useIn(11.6 + i * 0.6, 0.4) }}>
            <Icon name="check" size={26} color={C.ok} />
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 27, color: C.ink }}>{x}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/** Marco de celular con una pantalla adentro (capturas de 780 × 1688). */
const PW = 300;
const PH = Math.round((PW * 1688) / 780);
const PHONE = { left: 1400, top: 262, w: PW, h: PH };
const PhoneFrame: React.FC<{ p: number }> = ({ p }) => (
  <div style={{ position: "absolute", left: PHONE.left - 14, top: PHONE.top - 14, width: PW + 28, height: PH + 28, borderRadius: 46, background: "#0b1220",
    boxShadow: "0 28px 60px rgba(11,18,32,.28)", opacity: p, transform: `translateY(${(1 - p) * 30}px)` }} />
);
const Pantalla: React.FC<{ src: string; a: number; b: number; rings?: React.ComponentProps<typeof Shot>["rings"] }> = ({ src, a, b, rings }) => (
  <Shot src={src} {...PHONE} iw={780} ih={1688} a={a} b={b} zoom={[1, 1]} radius={34} border={false} fadeIn={0.25} rings={rings} />
);

/** 5. La aplicación Teléfono. */
export const App: React.FC = () => {
  const frame = usePop(2.3);
  const pasos = useIn(2.5, 0.5) * (1 - useIn(11.0, 0.4));
  const ctl = useIn(11.5, 0.5);
  const t = useT();
  const act = (a: number, b: number) => t >= a && t < b;
  const Ctl: React.FC<{ n: string; a: number; b: number }> = ({ n, a, b }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 22px", borderRadius: 20, border: `2px solid ${act(a, b) ? C.accent : C.line}`,
      background: act(a, b) ? C.accentSoft : "#fff" }}>
      <span style={{ width: 14, height: 14, borderRadius: 7, background: act(a, b) ? C.accent : C.line2 }} />
      <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 32, color: C.ink }}>{n}</span>
    </div>
  );
  return (
    <AbsoluteFill>
      <Headline eyebrow="También, en el celular" text="La aplicación Teléfono," accent="con tus contactos." />
      {/* El botón del panel que la abre */}
      <Shot src="09-telefono.png" left={80} top={262} w={1020} h={190} fitW={1900} fitH={1069} center origin="93% 12.5%" a={0.3} b={16.4} zoom={[1.2, 1.2]}
        rings={[{ x: 1640, y: 111, w: 260, h: 42, a: 2.5, b: 5.4 }]} fadeIn={0.5} />
      <div style={{ position: "absolute", left: 80, top: 480, width: 1020, opacity: useIn(4.0, 0.5), display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 14, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 999, padding: "12px 26px", boxShadow: shadowCard }}>
          <span style={{ width: 14, height: 14, borderRadius: 7, background: C.ok }} />
          <span style={{ fontFamily: F.mono, fontSize: 30, color: C.ink }}>telefono.atentina<span style={{ color: C.accent }}>.com.ar</span></span>
        </div>
        <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 24, color: C.muted, maxWidth: 260, lineHeight: 1.15 }}>su propia dirección, para el celular</span>
      </div>

      <div style={{ position: "absolute", left: 80, top: 620, width: 1020, opacity: pasos, transform: `translateY(${(1 - pasos) * 14}px)` }}>
        {[["1", "Abrís la aplicación desde el panel", 2.5, 6.8], ["2", "Elegís un contacto", 6.8, 7.8], ["3", "Tocás Llamar y sigue en pantalla completa", 7.8, 11.2]].map(([n, x, a, b]) => (
          <div key={n as string} style={{ display: "flex", alignItems: "center", gap: 18, padding: "14px 0", opacity: act(a as number, 99) ? 1 : 0.45 }}>
            <span style={{ width: 48, height: 48, borderRadius: 24, background: act(a as number, b as number) ? C.accent : C.line2, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.display, fontWeight: 800, fontSize: 28 }}>{n}</span>
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 36, color: C.ink }}>{x}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 80, top: 620, width: 1020, opacity: ctl, transform: `translateY(${(1 - ctl) * 14}px)` }}>
        <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", color: C.accent, marginBottom: 14 }}>MIENTRAS HABLÁS</div>
        <div style={{ display: "flex", gap: 18 }}>
          <Ctl n="Silenciar"  a={12.4} b={13.7} />
          <Ctl n="Teclado"  a={13.7} b={14.7} />
          <Ctl n="Subtítulos"  a={14.7} b={16.4} />
        </div>
      </div>

      <PhoneFrame p={frame} />
      <Pantalla src="11-app-contactos.png" a={2.6} b={7.2} />
      <Pantalla src="12-app-ficha.png" a={6.9} b={8.9}
        rings={[{ x: 215, y: 545, w: 150, h: 200, a: 7.6, b: 8.9 }]} />
      <Pantalla src="13-app-sonando.png" a={8.6} b={11.8} />
      <Pantalla src="14-app-llamada.png" a={11.5} b={16.4}
        rings={[{ x: 94, y: 1250, w: 160, h: 205, a: 12.4, b: 13.7 }, { x: 310, y: 1250, w: 160, h: 205, a: 13.7, b: 14.7 }, { x: 526, y: 1250, w: 160, h: 205, a: 14.7, b: 16.0 }]} />
      <Nota p={useIn(3.4)} style={{ position: "absolute", left: PHONE.left - 20, top: PHONE.top + PH + 24, width: PW + 40, textAlign: "center" }}>
        datos de ejemplo
      </Nota>
    </AbsoluteFill>
  );
};

/** 6. Cierre oscuro: resumen, requisitos y la documentación. */
export const Cierre: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.4, 0.7);
  const chips = [usePop(1.5), usePop(2.1), usePop(2.7), usePop(3.3)];
  const req = useIn(4.7, 0.6);
  const url = useIn(9.0, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 90, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 360 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 210, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 68, lineHeight: 1.08,
        color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em" }}>
        Número, equipo, contactos<br /><span style={{ color: C.accentOnDark }}>y a llamar.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 440, display: "flex", justifyContent: "center", gap: 20 }}>
        {PASOS.map((t, i) => <PasoChip key={t} n={i + 1} t={t} p={chips[i]} />)}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 575, display: "flex", justifyContent: "center", opacity: req, transform: `translateY(${(1 - req) * 16}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22, background: "#2a2410", border: "2px solid #e8b931", borderRadius: 18, padding: "14px 28px" }}>
          <span style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: "#ffd04d" }}>ANTES DE EMPEZAR</span>
          <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 27, color: "#ffe08a" }}>Plan Mostrador, Sucursal o Red · condiciones nuevas aceptadas</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 710, textAlign: "center", fontFamily: F.mono, fontSize: 22, letterSpacing: "0.1em", color: C.accentOnDark, opacity: url }}>
        LA GUÍA COMPLETA
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 760, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 16}px)` }}>
        <div style={{ background: "#fff", color: C.ink, borderRadius: 999, padding: "16px 36px", fontFamily: F.mono, fontSize: 36 }}>
          atentina.com.ar<span style={{ color: C.accent }}>/plataforma/telefono-del-equipo</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
