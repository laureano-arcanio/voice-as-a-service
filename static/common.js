// Helpers compartidos por dashboard.html y call.html.
const STATUS = {
  pendiente: ['Pendiente', 'badge'],
  sonando: ['Sonando', 'badge info'],
  en_curso: ['En curso', 'badge info'],
  finalizada: ['Finalizada', 'badge ok'],
  fallida: ['Fallida', 'badge bad'],
};
const MODE = {
  saliente: ['Saliente', 'badge'],
  entrante: ['Entrante', 'badge'],
  prueba: ['Prueba', 'badge warn'],
  api: ['API (texto)', 'badge'],
};
const WORKFLOW = {
  active: ['Incompleto', 'badge warn'],
  completed: ['Completo', 'badge ok'],
};

function esc(s) {
  return s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function fmtDur(s) {
  if (!s) return '–';
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('es-AR') + ' ' + d.toLocaleTimeString('es-AR', {hour: '2-digit', minute: '2-digit'});
}
function badge(map, key) {
  const [label, cls] = map[key] || [key || '–', 'badge'];
  return `<span class="${cls}">${label}</span>`;
}
function demoBadge(v) {
  if (v === true) return '<span class="badge ok">Sí</span>';
  if (v === false) return '<span class="badge">No</span>';
  return '–';
}
