import React from "react";
import { useCurrentFrame } from "remotion";
import { C } from "./theme";

// Personajes en estilo plano: busto de 240 x 300 (viewBox), escalable con `size` (alto en px).

type Hair = "short" | "bun" | "long" | "curly";
type Pose = "none" | "phone" | "texting" | "laptop" | "back";

export type PersonProps = {
  size: number;
  skin: string;
  hair: string;
  hairStyle: Hair;
  top: string;
  topDark: string;
  shirt?: string;
  tie?: string;
  glasses?: boolean;
  mood?: "happy" | "neutral" | "sad";
  talk?: number; // 0..1, apertura de la boca
  pose?: Pose;
  blinkOffset?: number;
  style?: React.CSSProperties;
};

const useBlink = (offset = 0) => {
  const frame = useCurrentFrame() + offset;
  const k = frame % 110;
  return k > 104 ? 0.15 : 1;
};

const HairBack: React.FC<{ s: Hair; c: string }> = ({ s, c }) => {
  if (s === "long") return <path d="M58 118 Q56 48 120 46 Q184 48 182 118 L190 236 Q120 252 50 236 Z" fill={c} />;
  if (s === "bun") return <circle cx={120} cy={50} r={26} fill={c} />;
  return null;
};

const HairFront: React.FC<{ s: Hair; c: string }> = ({ s, c }) => {
  if (s === "short")
    return <path d="M66 112 Q62 54 120 52 Q178 54 174 112 Q168 84 150 80 Q122 92 88 80 Q72 88 66 112 Z" fill={c} />;
  if (s === "curly")
    return (
      <g fill={c}>
        {[
          [76, 92, 18], [92, 70, 20], [118, 62, 22], [144, 68, 20], [164, 88, 18], [70, 112, 12], [170, 112, 12],
        ].map(([x, y, r], i) => (
          <circle key={i} cx={x} cy={y} r={r} />
        ))}
      </g>
    );
  // bun y long: flequillo con raya al costado
  return <path d="M64 116 Q60 58 120 56 Q180 58 176 116 Q162 80 128 74 Q100 96 64 116 Z" fill={c} />;
};

export const Person: React.FC<PersonProps> = ({
  size, skin, hair, hairStyle, top, topDark, shirt = "#ffffff", tie, glasses, mood = "neutral", talk = 0,
  pose = "none", blinkOffset = 0, style,
}) => {
  const blink = useBlink(blinkOffset);
  const open = talk > 0.06;
  const brow = mood === "sad" ? 5 : mood === "happy" ? -2 : 0;
  if (pose === "back") {
    // De espaldas: solo pelo y hombros
    return (
      <svg viewBox="0 0 240 300" height={size} width={size * 0.8} style={style}>
        <path d="M26 300 Q30 214 120 204 Q210 214 214 300 Z" fill={top} />
        <rect x={104} y={160} width={32} height={50} fill={skin} />
        <ellipse cx={120} cy={116} rx={54} ry={60} fill={hair} />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 240 300" height={size} width={size * 0.8} style={{ overflow: "visible", ...style }}>
      <HairBack s={hairStyle} c={hair} />
      {/* torso */}
      <path d="M26 300 Q30 214 120 204 Q210 214 214 300 Z" fill={top} />
      <path d="M96 208 L120 262 L144 208 Z" fill={shirt} />
      {tie ? <path d="M114 214 L126 214 L130 262 L120 274 L110 262 Z" fill={tie} /> : null}
      <path d="M86 210 L120 270 L100 300 L64 300 Q70 240 86 210 Z" fill={topDark} opacity={0.55} />
      <path d="M154 210 L120 270 L140 300 L176 300 Q170 240 154 210 Z" fill={topDark} opacity={0.55} />
      {/* cuello y cabeza */}
      <rect x={106} y={158} width={28} height={52} rx={10} fill={skin} />
      <circle cx={66} cy={122} r={11} fill={skin} />
      <circle cx={174} cy={122} r={11} fill={skin} />
      <ellipse cx={120} cy={118} rx={54} ry={60} fill={skin} />
      <HairFront s={hairStyle} c={hair} />
      {/* cara */}
      <path d={`M90 ${100 + brow} Q100 ${94 - brow} 110 ${100}`} stroke={hair} strokeWidth={4} fill="none" strokeLinecap="round" />
      <path d={`M130 100 Q140 ${94 - brow} 150 ${100 + brow}`} stroke={hair} strokeWidth={4} fill="none" strokeLinecap="round" />
      <ellipse cx={100} cy={118} rx={5.5} ry={6.5 * blink} fill={C.ink} />
      <ellipse cx={140} cy={118} rx={5.5} ry={6.5 * blink} fill={C.ink} />
      {glasses ? (
        <g stroke={C.ink} strokeWidth={3.5} fill="none">
          <rect x={84} y={104} width={32} height={26} rx={9} />
          <rect x={124} y={104} width={32} height={26} rx={9} />
          <path d="M116 116 L124 116" />
        </g>
      ) : null}
      <circle cx={88} cy={140} r={8} fill="#f08f8f" opacity={0.25} />
      <circle cx={152} cy={140} r={8} fill="#f08f8f" opacity={0.25} />
      {open ? (
        <ellipse cx={120} cy={146} rx={9 + talk * 3} ry={2.5 + talk * 8} fill="#7a2a2a" />
      ) : mood === "sad" ? (
        <path d="M108 152 Q120 142 132 152" stroke="#7a2a2a" strokeWidth={4} fill="none" strokeLinecap="round" />
      ) : (
        <path d={mood === "happy" ? "M104 142 Q120 158 136 142" : "M108 146 Q120 152 132 146"} stroke="#7a2a2a"
          strokeWidth={4} fill="none" strokeLinecap="round" />
      )}
      {pose === "phone" ? (
        <g>
          <path d="M44 300 Q40 230 62 150" stroke={top} strokeWidth={30} strokeLinecap="butt" fill="none" />
          <rect x={44} y={92} width={22} height={52} rx={6} fill={C.ink} transform="rotate(-12 55 118)" />
          <circle cx={62} cy={146} r={14} fill={skin} />
        </g>
      ) : null}
      {pose === "texting" ? (
        <g>
          <path d="M196 300 Q200 268 160 252" stroke={top} strokeWidth={28} strokeLinecap="butt" fill="none" />
          <rect x={128} y={214} width={34} height={58} rx={7} fill={C.ink} transform="rotate(-14 145 243)" />
          <rect x={133} y={220} width={24} height={40} rx={3} fill="#25d366" opacity={0.85} transform="rotate(-14 145 243)" />
          <circle cx={158} cy={256} r={13} fill={skin} />
        </g>
      ) : null}
      {pose === "laptop" ? (
        <g>
          <path d="M40 300 L58 236 L182 236 L200 300 Z" fill="#c9d2e0" />
          <path d="M58 236 L182 236 L200 300 L40 300 Z" fill="none" stroke="#aab4c4" strokeWidth={3} />
          <g transform="translate(108 256) scale(0.38)">
            <path d="M55.07 38.62A24 24 0 1 1 55.07 25.38" fill="none" stroke="#ffffff" strokeWidth={8} strokeLinecap="round" />
          </g>
        </g>
      ) : null}
    </svg>
  );
};

/**
 * El agente de Atentina: el logo (aro + tres barras) en un círculo blanco. Las barras se mueven con la voz
 * (`talk`, 0..1) y en reposo quedan como en la marca. Desde el 21-oct-2026 el agente se representa así, no con
 * la mascota (docs/VIDEOS.md, "Estilo visual").
 */
export const AgenteLogo: React.FC<{ size: number; talk?: number; style?: React.CSSProperties }> = ({ size, talk = 0, style }) => {
  const frame = useCurrentFrame();
  const base = [12, 22, 12];
  const h = base.map((b, i) => {
    const wob = 0.6 + 0.4 * Math.abs(Math.sin(frame / 2.3 + i * 1.7));
    return Math.min(30, b * (1 + (talk > 0.04 ? talk * wob * 0.7 : 0)));
  });
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} style={{ overflow: "visible", ...style }}>
      <circle cx={32} cy={32} r={31} fill="#ffffff" stroke={C.line} strokeWidth={1} />
      <g transform="translate(32 32) scale(0.78) translate(-32 -32)">
        <path d="M55.07 38.62A24 24 0 1 1 55.07 25.38" fill="none" stroke={C.ink} strokeWidth={8} strokeLinecap="round" />
        {h.map((v, i) => (
          <rect key={i} x={20 + i * 9} y={32 - v / 2} width={6} height={v} rx={3} fill={C.accent} />
        ))}
      </g>
    </svg>
  );
};

/** NO USAR desde el 21-oct-2026: el agente va con el logo (`AgenteLogo`). Queda por los videos ya entregados. */
/** Atentina: la cabeza es la marca (aro con las tres barras como boca), con vincha y saco azul. */
export const Mascot: React.FC<{ size: number; talk?: number; bodyless?: boolean; style?: React.CSSProperties }> = ({
  size, talk = 0, bodyless, style,
}) => {
  const frame = useCurrentFrame();
  const blink = useBlink(37);
  // Las barras de la marca se mueven con la voz; en reposo respiran apenas
  const idle = 0.12 + 0.06 * Math.sin(frame / 9);
  const bars = [0, 1, 2].map((i) => {
    const wob = 0.55 + 0.45 * Math.abs(Math.sin(frame / 2.3 + i * 1.7));
    const lv = talk > 0.04 ? talk * wob : idle;
    return [16, 30, 16][i] * (0.55 + lv * 1.1);
  });
  const vb = bodyless ? "40 30 160 170" : "0 0 240 300";
  return (
    <svg viewBox={vb} height={size} width={bodyless ? size * (160 / 170) : size * 0.8} style={{ overflow: "visible", ...style }}>
      {bodyless ? null : (
        <g>
          <path d="M26 300 Q30 214 120 204 Q210 214 214 300 Z" fill={C.accent} />
          <path d="M98 208 L120 256 L142 208 Z" fill="#ffffff" />
          <path d="M86 210 L120 262 L100 300 L62 300 Q70 240 86 210 Z" fill={C.accent2} />
          <path d="M154 210 L120 262 L140 300 L178 300 Q170 240 154 210 Z" fill={C.accent2} />
          <circle cx={168} cy={250} r={9} fill="#ffffff" />
          <rect x={108} y={164} width={24} height={44} rx={10} fill="#e9edf5" />
        </g>
      )}
      {/* cabeza: el aro de la marca */}
      <circle cx={120} cy={115} r={58} fill="#ffffff" />
      <path d="M175.7 131 A58 58 0 1 1 175.7 99" fill="none" stroke={C.ink} strokeWidth={15} strokeLinecap="round" />
      <ellipse cx={104} cy={96} rx={5.5} ry={6.5 * blink} fill={C.ink} />
      <ellipse cx={136} cy={96} rx={5.5} ry={6.5 * blink} fill={C.ink} />
      {bars.map((h, i) => (
        <rect key={i} x={100 + i * 15} y={128 - h / 2} width={10} height={h} rx={5} fill={C.accent} />
      ))}
      {/* vincha con micrófono */}
      <path d="M60 104 Q60 36 120 34 Q180 36 180 104" fill="none" stroke={C.ink} strokeWidth={7} strokeLinecap="round" />
      <rect x={50} y={96} width={18} height={34} rx={8} fill={C.ink} />
      <rect x={172} y={96} width={18} height={34} rx={8} fill={C.ink} />
      <path d="M60 128 Q66 158 92 160" fill="none" stroke={C.ink} strokeWidth={5} strokeLinecap="round" />
      <circle cx={95} cy={160} r={6} fill={C.accent} />
    </svg>
  );
};

// Elenco: siempre los mismos colores para cada personaje
export const CAST = {
  cliente: { skin: "#e8b48f", hair: "#4a2c1a", hairStyle: "long", top: "#e07a5f", topDark: "#b85a42" },
  duena: { skin: "#f2c9a5", hair: "#2b2b33", hairStyle: "bun", top: "#3d4a63", topDark: "#232c3d", shirt: "#eaf0ff" },
  integrador: { skin: "#c68a63", hair: "#1d1d22", hairStyle: "curly", top: "#2f3a4d", topDark: "#1b2230", glasses: true },
  cliente2: { skin: "#d9a07e", hair: "#3b2a1e", hairStyle: "short", top: "#2a9d8f", topDark: "#1f7a6f" },
  cliente3: { skin: "#f1c7a8", hair: "#c9a15a", hairStyle: "long", top: "#8e6cc9", topDark: "#6c4fa3", glasses: true },
  otro: { skin: "#d9a07e", hair: "#6b4a2e", hairStyle: "short", top: "#7c8aa5", topDark: "#5b6780" },
} as const;
