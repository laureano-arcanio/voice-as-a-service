import { ActionIcon, Menu, TextInput, type TextInputProps, Tooltip } from '@mantine/core';
import { IconBraces } from '@tabler/icons-react';
import { useRef } from 'react';
import { TEMPLATE_VARS } from './draft';

/** Menu para insertar una variable ({{secrets.X}}, {{call.from}}...) donde esta el cursor. */
export function TemplateMenu({ secrets, onInsert }: { secrets: string[]; onInsert: (v: string) => void }) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <Tooltip label="Insertar una variable" withArrow>
          <ActionIcon variant="subtle" color="gray" aria-label="Insertar una variable">
            <IconBraces size={16} />
          </ActionIcon>
        </Tooltip>
      </Menu.Target>
      <Menu.Dropdown mah={360} style={{ overflowY: 'auto' }}>
        <Menu.Label>Secretos del agente</Menu.Label>
        {secrets.map((s) => (
          <Menu.Item key={s} className="mono" onClick={() => onInsert(`{{secrets.${s}}}`)}>
            {`{{secrets.${s}}}`}
          </Menu.Item>
        ))}
        <Menu.Item onClick={() => onInsert('{{secrets.NOMBRE}}')}>Otro secreto…</Menu.Item>
        {TEMPLATE_VARS.map((g) => (
          <div key={g.group}>
            <Menu.Divider />
            <Menu.Label>{g.group}</Menu.Label>
            {g.items.map((v) => (
              <Menu.Item
                key={v.value}
                onClick={() => onInsert(v.value)}
                rightSection={<span className="mono">{v.value}</span>}
              >
                {v.label}
              </Menu.Item>
            ))}
          </div>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}

/** Campo de texto para un valor fijo, con el menu de variables a la derecha. */
export function TemplateInput({
  value,
  onChange,
  secrets,
  ...props
}: Omit<TextInputProps, 'value' | 'onChange'> & {
  value: string;
  onChange: (v: string) => void;
  secrets: string[];
}) {
  const ref = useRef<HTMLInputElement>(null);
  const insert = (v: string) => {
    const el = ref.current;
    const at = el?.selectionStart ?? value.length;
    const end = el?.selectionEnd ?? at;
    onChange(value.slice(0, at) + v + value.slice(end));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(at + v.length, at + v.length);
    });
  };
  return (
    <TextInput
      ref={ref}
      {...props}
      classNames={{ input: 'mono' }}
      value={value}
      onChange={(e) => onChange(e.currentTarget.value)}
      rightSection={<TemplateMenu secrets={secrets} onInsert={insert} />}
    />
  );
}
