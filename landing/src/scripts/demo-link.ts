// "Hacé una demo" del nav: lleva al widget de llamada y lo sacude para que se note.
// En mobile el widget queda abajo del título, así que se lo sube al tope; en desktop está
// al lado del título y solo se mueve si no se ve entero.

const SHAKE = "animate-shake";

export function goToDemo(e: MouseEvent) {
  const target = document.getElementById("llamada");
  if (!target) return;
  e.preventDefault();

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stacked = matchMedia("(width <= 900px)").matches;
  target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: stacked ? "start" : "nearest" });
  target.focus({ preventScroll: true });
  if (reduce) return;

  afterScroll(() => {
    target.classList.remove(SHAKE);
    void target.offsetWidth; // reinicia la animación si se vuelve a tocar
    target.classList.add(SHAKE);
    target.addEventListener("animationend", () => target.classList.remove(SHAKE), { once: true });
  });
}

// Espera a que el scroll se quede quieto (scrollend no está en todos los Safari, y si no hay
// scroll no se dispara nunca).
function afterScroll(done: () => void) {
  let last = scrollY;
  let still = 0;
  const tick = () => {
    still = scrollY === last ? still + 1 : 0;
    last = scrollY;
    if (still >= 6) done();
    else requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
