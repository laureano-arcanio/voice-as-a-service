// Timbre de una entrante: dos tonos cortos con Web Audio, sin archivos. Si el navegador no deja sonar
// (sin un clic previo en la página, o sin Web Audio), no suena y queda el aviso visual.

let ctx: AudioContext | null = null;

export function playRingtone() {
  try {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    ctx ??= new Ctor();
    if (ctx.state === 'suspended') void ctx.resume().catch(() => undefined);
    const now = ctx.currentTime;
    for (const start of [0, 0.35]) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, now + start);
      gain.gain.exponentialRampToValueAtTime(0.2, now + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + start + 0.25);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + start);
      osc.stop(now + start + 0.26);
    }
  } catch {
    // solo visual
  }
}

// Tono de llamada saliente (el "ringback" que oye quien llama mientras suena del otro lado): 425 Hz, 1 s sí
// y 4 s no, como en las líneas de Argentina. Un ciclo entero; el que llama lo repite cada RINGBACK_REPEAT_MS.
export const RINGBACK_REPEAT_MS = 5_000;

export function playRingback() {
  try {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    ctx ??= new Ctor();
    if (ctx.state === 'suspended') void ctx.resume().catch(() => undefined);
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 425;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.15, now + 0.03);
    gain.gain.setValueAtTime(0.15, now + 0.97);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 1.01);
  } catch {
    // sin sonido: queda el estado en la barra
  }
}
