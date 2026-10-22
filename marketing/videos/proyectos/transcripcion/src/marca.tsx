import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { useIn, usePop, Wave } from "../../../src/comun/ui";

const Chip: React.FC<{ p: number; children: React.ReactNode }> = ({ p, children }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 10, borderRadius: 999, padding: "10px 22px", fontFamily: F.mono, fontSize: 24,
    background: "#16213a", color: C.ctaInk, border: "2px solid #23304d", transform: `scale(${p})`,
  }}>
    {children}
  </div>
);

/** Voz que se convierte en texto: una onda que se apaga y una línea que se escribe. */
const VozATexto: React.FC<{ at: number }> = ({ at }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const p = useIn(at, 0.5);
  const k = interpolate(t, [at + 0.3, at + 2.6], [0, 1], CLAMP);
  const texto = "Hola, me llegó un cargo que no reconozco.";
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 28, opacity: p }}>
      <div style={{ background: C.accent, borderRadius: 999, padding: "12px 22px" }}>
        <Wave n={7} h={30} live={1 - k * 0.7} />
      </div>
      <svg width={60} height={20}><path d="M2 10 H52 M44 3 L54 10 L44 17" stroke={C.accentOnDark} strokeWidth={3} fill="none" strokeLinecap="round" /></svg>
      <div style={{ fontFamily: F.mono, fontSize: 26, color: C.ctaInk, width: 700, whiteSpace: "nowrap" }}>
        <span style={{ color: C.accentOnDark }}>Cliente · </span>
        {texto.slice(0, Math.floor(texto.length * k))}
        <span style={{ opacity: Math.floor(frame / 15) % 2 ? 0 : 1, color: C.accentOnDark }}>▍</span>
      </div>
    </div>
  );
};

/** 0. Intro oscura: qué es y para quién. */
export const Intro: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.9, 0.7);
  const chips = [usePop(4.2), usePop(4.5), usePop(4.8), usePop(5.1)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.1, 0.5) }}>
        TRANSCRIPCIÓN Y VOZ PARA CALL CENTERS
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 220, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 560 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 400, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 72,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Cada llamada de tu call center,<br /><span style={{ color: C.accentOnDark }}>en texto.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640 }}>
        <VozATexto at={1.8} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 800, display: "flex", justifyContent: "center", gap: 18 }}>
        {["Transcripción", "Síntesis de voz", "API", "Servidores en Argentina"].map((x, i) => <Chip key={x} p={chips[i]}>{x}</Chip>)}
      </div>
    </AbsoluteFill>
  );
};

/** 4. Cierre con la marca y el contacto. */
export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const line = useIn(0.9, 0.7);
  const contacto = useIn(2.2, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 230, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 700 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 440, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 72, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Cada llamada,<br /><span style={{ color: C.accentOnDark }}>en texto y en datos.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 680, display: "flex", justifyContent: "center", alignItems: "center", gap: 30, opacity: contacto }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 16, padding: "16px 34px", fontFamily: F.body, fontWeight: 700, fontSize: 32 }}>
          Probalo con tus grabaciones
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 32, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};
