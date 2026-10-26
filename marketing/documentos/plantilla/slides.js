// Navegación de una presentación (plantilla/slides.css): una diapositiva por pantalla, escalada a la ventana.
// Teclas: → ↓ espacio PageDown y clic avanzan; ← ↑ PageUp retroceden; Home y End; F o doble clic, pantalla completa.
// El número de diapositiva va en el hash (#5) para poder volver a ella. Al imprimir no interviene (media print).
(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll("section.slide"));
  if (!slides.length) return;
  document.body.classList.remove("no-js");
  slides.forEach(function (s, j) { s.querySelectorAll(".foot .n").forEach(function (n) { n.dataset.n = j + 1; n.dataset.total = slides.length; }); });
  var hint = document.querySelector(".hint");
  if (hint) setTimeout(function () { hint.classList.add("off"); }, 5000);
  var i = Math.min(Math.max(parseInt(location.hash.slice(1), 10) || 1, 1), slides.length) - 1;

  function fit() {
    var w = slides[0].offsetWidth || 1920, h = slides[0].offsetHeight || 1080;
    var k = Math.min(window.innerWidth / w, window.innerHeight / h);
    slides.forEach(function (s) { s.style.transform = "translate(-50%, -50%) scale(" + k + ")"; });
  }
  function show(n) {
    i = Math.min(Math.max(n, 0), slides.length - 1);
    slides.forEach(function (s, j) { s.classList.toggle("current", j === i); });
    history.replaceState(null, "", "#" + (i + 1));
    fit();
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === " " || e.key === "PageDown") { e.preventDefault(); show(i + 1); }
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "PageUp") { e.preventDefault(); show(i - 1); }
    else if (e.key === "Home") show(0);
    else if (e.key === "End") show(slides.length - 1);
    else if (e.key === "f" || e.key === "F") toggleFull();
  });
  document.addEventListener("click", function (e) { if (e.target.closest("a")) return; show(i + 1); });
  document.addEventListener("dblclick", toggleFull);
  window.addEventListener("resize", fit);
  window.addEventListener("hashchange", function () { show((parseInt(location.hash.slice(1), 10) || 1) - 1); });
  function toggleFull() {
    if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
  }
  show(i);
})();
