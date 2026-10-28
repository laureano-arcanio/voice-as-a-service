import { useRef } from 'react';

const LETTERS: Record<string, string> = {
  '1': '',
  '2': 'ABC',
  '3': 'DEF',
  '4': 'GHI',
  '5': 'JKL',
  '6': 'MNO',
  '7': 'PQRS',
  '8': 'TUV',
  '9': 'WXYZ',
  '0': '+',
  '#': '',
  '+': '',
};

const LONG_PRESS_MS = 500;

/**
 * Teclado de 12 teclas. Para marcar, la última fila es `+ 0` (mantener el 0 también pone +); en la llamada
 * (tonos), `0 #`. Sin `*`: en Anura corta la otra llamada de la cuenta (AGENTS.md).
 */
export function Keypad({
  keys,
  onKey,
  disabled,
}: {
  keys: readonly string[];
  onKey: (key: string) => void;
  disabled?: boolean;
}) {
  const timer = useRef<number | null>(null);
  const longPressed = useRef(false);

  const down = (k: string) => {
    longPressed.current = false;
    if (k !== '0' || !keys.includes('+')) return;
    timer.current = window.setTimeout(() => {
      longPressed.current = true;
      onKey('+');
    }, LONG_PRESS_MS);
  };
  const up = () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  };

  return (
    <div className="tel-keypad" role="group" aria-label="Teclado">
      {keys.map((k, i) =>
        k ? (
          <button
            key={k}
            type="button"
            className="tel-key"
            disabled={disabled}
            aria-label={k === '+' ? 'Más' : k === '#' ? 'Numeral' : k}
            onPointerDown={() => down(k)}
            onPointerUp={up}
            onPointerLeave={up}
            onClick={() => {
              if (longPressed.current) return;
              onKey(k);
            }}
          >
            <span className="tel-key-digit">{k}</span>
            <span className="tel-key-letters">{keys.includes('+') && k === '0' ? '' : LETTERS[k]}</span>
          </button>
        ) : (
          <span key={`empty-${i}`} />
        ),
      )}
    </div>
  );
}
