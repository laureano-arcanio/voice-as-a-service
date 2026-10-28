// Un intervalo que sigue con la pestaña oculta. Chrome agrupa los timers de una pestaña oculta (más de 5 min,
// sin audio ni WebRTC) a uno por minuto; los de un Worker no se frenan. El pulso de Disponible y el sondeo del
// timbre van por acá. Sin Worker (tests, navegadores viejos), setInterval.
const SOURCE =
  'let t;onmessage=(e)=>{clearInterval(t);if(e.data>0)t=setInterval(()=>postMessage(0),e.data);};';

export function every(ms: number, fn: () => void): () => void {
  let worker: Worker | null = null;
  let url = '';
  if (typeof Worker !== 'undefined' && typeof URL.createObjectURL === 'function') {
    try {
      url = URL.createObjectURL(new Blob([SOURCE], { type: 'text/javascript' }));
      worker = new Worker(url);
    } catch {
      worker = null;
    }
  }
  if (!worker) {
    if (url) URL.revokeObjectURL(url);
    const t = window.setInterval(fn, ms);
    return () => window.clearInterval(t);
  }
  const w = worker;
  w.onmessage = () => fn();
  w.postMessage(ms);
  return () => {
    w.terminate();
    URL.revokeObjectURL(url);
  };
}
