import {
  Autocomplete,
  type AutocompleteProps,
  type ComboboxProps,
  MultiSelect,
  type MultiSelectProps,
  Select,
  type SelectProps,
  TagsInput,
  type TagsInputProps,
} from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';

/** Alto de la lista: 220 px es el máximo de Mantine, más aire para el borde del teclado. */
const ROOM = 240;

type Side = 'bottom-start' | 'top-start';

/**
 * Combobox dentro de un Modal, donde el campo puede quedar cerca del borde de abajo.
 *
 * Mantine 8 elige el lado de la lista en cada cuadro y lo cambia cuando cambia el espacio que hay: en
 * un celular el teclado achica la pantalla y el modal se mueve, y la lista salta de arriba a abajo
 * sin parar, como vibrando (mantine#8255; en 8.x no tiene arreglo, `preventPositionChangeWhenVisible`
 * congela la pagina). Acá el lado se elige con el espacio visible de verdad (`visualViewport`, que
 * descuenta el teclado), se vuelve a medir una sola vez cuando el teclado termina de abrirse, y no
 * cambia más mientras la lista está abierta.
 *
 * Se usan igual que los de Mantine: `ModalSelect`, `ModalMultiSelect` y `ModalAutocomplete`.
 */
function useModalDropdown() {
  const [field, setField] = useState<HTMLInputElement | null>(null);
  const [side, setSide] = useState<Side>('bottom-start');
  const [opened, setOpened] = useState(false);

  const measure = useCallback(() => {
    const box = field?.getBoundingClientRect();
    if (!box) return;
    const view = window.visualViewport;
    // Borde de abajo de lo que se ve: en el celular, arriba del teclado.
    const visibleBottom = view ? view.offsetTop + view.height : window.innerHeight;
    // Si abajo del campo no entra la lista, va para arriba.
    setSide(visibleBottom - box.bottom < ROOM ? 'top-start' : 'bottom-start');
  }, [field]);

  // El teclado tarda en abrirse y mientras tanto el alto visible cambia cuadro a cuadro: se mide de
  // nuevo cuando se queda quieto. Una sola corrección por apertura, no un salto por cuadro.
  useEffect(() => {
    if (!opened) return;
    const view = window.visualViewport;
    // Sin visualViewport (navegadores viejos, tests) vale la medida que ya se hizo al abrir.
    if (!view) return;
    let timer = 0;
    const onResize = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(measure, 150);
    };
    view.addEventListener('resize', onResize);
    return () => {
      window.clearTimeout(timer);
      view.removeEventListener('resize', onResize);
    };
  }, [opened, measure]);

  return {
    field: setField,
    side,
    onOpen: (after?: () => void) => {
      measure();
      setOpened(true);
      after?.();
    },
    onClose: (after?: () => void) => {
      setOpened(false);
      after?.();
    },
  };
}

/** Sin flip: el lado ya está elegido y Mantine no lo vuelve a decidir mientras la lista está abierta. */
function withSide(comboboxProps: Partial<ComboboxProps> | undefined, side: Side): Partial<ComboboxProps> {
  return { ...comboboxProps, position: side, middlewares: { ...comboboxProps?.middlewares, flip: false } };
}

export function ModalSelect({ comboboxProps, onDropdownOpen, onDropdownClose, ...props }: SelectProps) {
  const { field, side, onOpen, onClose } = useModalDropdown();
  return (
    <Select
      ref={field}
      {...props}
      comboboxProps={withSide(comboboxProps, side)}
      onDropdownOpen={() => onOpen(onDropdownOpen)}
      onDropdownClose={() => onClose(onDropdownClose)}
    />
  );
}

export function ModalMultiSelect({ comboboxProps, onDropdownOpen, onDropdownClose, ...props }: MultiSelectProps) {
  const { field, side, onOpen, onClose } = useModalDropdown();
  return (
    <MultiSelect
      ref={field}
      {...props}
      comboboxProps={withSide(comboboxProps, side)}
      onDropdownOpen={() => onOpen(onDropdownOpen)}
      onDropdownClose={() => onClose(onDropdownClose)}
    />
  );
}

export function ModalAutocomplete({
  comboboxProps,
  onDropdownOpen,
  onDropdownClose,
  ...props
}: AutocompleteProps) {
  const { field, side, onOpen, onClose } = useModalDropdown();
  return (
    <Autocomplete
      ref={field}
      {...props}
      comboboxProps={withSide(comboboxProps, side)}
      onDropdownOpen={() => onOpen(onDropdownOpen)}
      onDropdownClose={() => onClose(onDropdownClose)}
    />
  );
}

export function ModalTagsInput({ comboboxProps, onDropdownOpen, onDropdownClose, ...props }: TagsInputProps) {
  const { field, side, onOpen, onClose } = useModalDropdown();
  return (
    <TagsInput
      ref={field}
      {...props}
      comboboxProps={withSide(comboboxProps, side)}
      onDropdownOpen={() => onOpen(onDropdownOpen)}
      onDropdownClose={() => onClose(onDropdownClose)}
    />
  );
}
