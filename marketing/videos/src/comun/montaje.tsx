import React from "react";
import { Audio } from "@remotion/media";
import { AbsoluteFill, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { CLAMP } from "./theme";
import { Backdrop } from "./ui";

export const FPS = 30;
export const f = (s: number) => Math.round(s * FPS);
const FADE = 8;

// Música: 0,32 sin voz, 0,12 debajo de la voz (medido: la locución queda clara y la mezcla en ~-16 LUFS)
const MUSIC = 0.32;
const DUCK = 0.12;

export type Escena = { from: number; len: number };
export type Voz = { id: string; scene: string; at: number };

/** Arma las escenas en orden; la primera puede ser una intro que se funde (INTRO_FADE s) con la siguiente. */
export const armarEscenas = <K extends string>(lens: Record<K, number>, intro?: K, introFade = 0.6) => {
  let at = 0;
  const out = {} as Record<K, Escena>;
  for (const id of Object.keys(lens) as K[]) {
    out[id] = { from: at, len: lens[id] };
    at += lens[id] - (id === intro ? introFade : 0);
  }
  return out;
};

export const duracionTotal = (escenas: Record<string, Escena>) =>
  Math.max(...Object.values(escenas).map((e) => e.from + e.len));

/** Fundido de entrada y salida de una escena (frames). */
export const Fade: React.FC<{ len: number; fadeIn: number; fadeOut: number; children: React.ReactNode }> = ({ len, fadeIn, fadeOut, children }) => {
  const frame = useCurrentFrame();
  const o = Math.min(fadeIn ? interpolate(frame, [0, fadeIn], [0, 1], CLAMP) : 1, interpolate(frame, [len - fadeOut, len], [1, 0], CLAMP));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

/** Volumen de la música por frame: baja con la voz y se desvanece al final. */
export const volumenMusica = (spans: readonly (readonly [number, number])[], totalFrames: number) => (fr: number) => {
  let v = MUSIC;
  for (const [a, b] of spans) {
    const d = interpolate(fr, [a - 8, a, b, b + 12], [0, 1, 1, 0], CLAMP);
    v = Math.min(v, MUSIC - (MUSIC - DUCK) * d);
  }
  return v * interpolate(fr, [0, 15, totalFrames - 45, totalFrames], [0, 1, 1, 0], CLAMP);
};

/**
 * El video de un proyecto: escenas con fundidos, locución y música de public/<dir>/.
 * - `intro`: escena que se funde sobre la siguiente (se dibuja encima).
 * - La última escena no se funde al final: el cierre queda y la música se desvanece.
 */
export const Montaje: React.FC<{
  dir: string;
  escenas: Record<string, Escena>;
  componentes: Record<string, React.FC>;
  voces: Voz[];
  duraciones: Record<string, number>;
  intro?: string;
  introFade?: number;
}> = ({ dir, escenas, componentes, voces, duraciones, intro, introFade = 0.6 }) => {
  const ids = Object.keys(escenas);
  const ultima = ids[ids.length - 1];
  const orden = intro ? [...ids.filter((id) => id !== intro), intro] : ids;
  const spans = voces.map((v) => {
    const start = f(escenas[v.scene].from + v.at);
    return [start, start + f(duraciones[v.id])] as const;
  });
  const total = f(duracionTotal(escenas));
  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      <Backdrop />
      {orden.map((id) => {
        const s = escenas[id];
        const Comp = componentes[id];
        const len = f(s.len);
        const despuesDeIntro = intro && ids[ids.indexOf(intro) + 1] === id;
        return (
          <Sequence key={id} from={f(s.from)} durationInFrames={len} name={id}>
            <Fade len={id === ultima ? len + FADE : len} fadeIn={id === ids[0] || despuesDeIntro ? 0 : FADE}
              fadeOut={id === intro ? f(introFade) : FADE}>
              <Comp />
            </Fade>
          </Sequence>
        );
      })}
      {voces.map((v) => (
        <Sequence key={`${v.id}-${v.scene}`} from={f(escenas[v.scene].from + v.at)} name={`voz ${v.id}`} layout="none">
          <Audio src={staticFile(`${dir}/vo/${v.id}.wav`)} />
        </Sequence>
      ))}
      <Audio src={staticFile(`${dir}/musica.wav`)} volume={volumenMusica(spans, total)} />
    </AbsoluteFill>
  );
};
