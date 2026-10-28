// El teléfono del equipo como app de teléfono de Android (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16): favoritos,
// recientes, contactos con su ficha, búsqueda y teclado para marcar, con la llamada y la entrante a pantalla
// completa. Llama, atiende y vuelve a entrar con el CallProvider del panel: misma API y mismas reglas.
import { ActionIcon, Alert, Loader, Menu, Switch, Text, Tooltip } from '@mantine/core';
import {
  IconArrowLeft,
  IconBackspace,
  IconCheck,
  IconClock,
  IconCopy,
  IconDialpad,
  IconLogout,
  IconPhone,
  IconSearch,
  IconStar,
  IconStarFilled,
  IconUserPlus,
  IconUsers,
  IconX,
} from '@tabler/icons-react';
import { type ReactNode, useMemo, useState } from 'react';
import type { CallSummary, Contact, PhoneNumber } from '@/api/types';
import { usePageTitle } from '@/branding/context';
import { useCurrentUser, useLogout } from '@/features/auth/api';
import { useFeatureLock, usePlanFeatures } from '@/features/billing/features';
import { useBlockedNumbers, useContact, useContacts, useOptouts } from '@/features/contacts/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { useContactCalls, useMyCalls } from '@/features/phone/api';
import { SaveContactModal } from '@/features/phone/CallBar';
import { type CallTarget, useDirectCall, usePresence } from '@/features/phone/context';
import { storedFrom } from '@/features/phone/storage';
import { E164_RE, formatDate, formatDuration } from '@/lib/format';
import { notifyError } from '@/lib/notify';
import { type Favorite, useFavorites } from './favorites';
import { IncomingScreen, InCallScreen } from './InCall';
import { callDirection, groupByDay, timeLabel, withLetters } from './calls';
import { Keypad } from './Keypad';
import { DIAL_KEYS } from './keys';
import { Avatar, DirectionIcon } from './parts';

type Tab = 'favorites' | 'recents' | 'contacts';
const RECENTS = 50;

function numberLabel(n: PhoneNumber): string {
  return n.label ? `${n.label} · ${n.e164}` : n.e164;
}

function clean(phone: string): string {
  return phone.trim().replace(/[\s()\-.]/g, '');
}

/** Lo que el teléfono necesita para llamar: el número de salida, bajas y bloqueados, y `place` con sus motivos. */
function usePhone() {
  const me = useCurrentUser();
  const c = useDirectCall();
  const numbers = usePhoneNumbers();
  const optouts = useOptouts();
  const blockedNumbers = useBlockedNumbers();
  const [chosen, setChosen] = useState<string | null>(() => storedFrom.get(me.id));

  const own = (numbers.data ?? []).filter((n) => n.client_id === me.client_id);
  const from = own.find((n) => n.id === chosen) ?? own[0] ?? null;
  const optedOut = useMemo(() => {
    const m = new Map<string, string>();
    for (const o of optouts.data ?? []) if (o.channel !== 'whatsapp') m.set(o.phone, o.created_at);
    return m;
  }, [optouts.data]);
  const blocked = useMemo(
    () => new Set((blockedNumbers.data ?? []).map((b) => b.phone)),
    [blockedNumbers.data],
  );

  const pickFrom = (id: string) => {
    setChosen(id);
    storedFrom.set(me.id, id);
  };

  /** Por qué no se puede llamar a ese teléfono ahora (o null). */
  const reason = (phone?: string | null): string | null =>
    c.disabledReason ??
    (phone && blocked.has(phone)
      ? 'El número está bloqueado: se desbloquea en el panel, Contactos.'
      : c.busy
        ? 'Ya estás en una llamada.'
        : !from
          ? 'Hace falta un número asignado a tu cuenta para llamar.'
          : null);

  const place = (t: CallTarget) => {
    const why = reason(t.phone);
    if (why) return notifyError(new Error(why), 'No se puede llamar');
    void c.call({ ...t, fromLabel: from ? numberLabel(from) : null }, from?.id ?? null);
  };

  return { me, numbers, own, from, pickFrom, optedOut, blocked, reason, place };
}

type PhoneCtx = ReturnType<typeof usePhone>;

function CallIcon({ phone, label, onCall }: { phone: string; label: string; onCall: () => void }) {
  return (
    <ActionIcon
      variant="subtle"
      size="lg"
      radius="xl"
      aria-label={`Llamar a ${label}`}
      onClick={(e) => {
        e.stopPropagation();
        onCall();
      }}
      data-phone={phone}
    >
      <IconPhone size={20} />
    </ActionIcon>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="tel-empty">{children}</p>;
}

// ---- Favoritos ----

function FavoritesTab({
  favs,
  ctx,
  open,
}: {
  favs: Favorite[];
  ctx: PhoneCtx;
  open: (id: string) => void;
}) {
  if (!favs.length)
    return (
      <Empty>
        Sin favoritos todavía. Abrí un contacto y tocá la estrella para tenerlo acá, a un toque de llamarlo.
      </Empty>
    );
  return (
    <div className="tel-favs" role="list" aria-label="Favoritos">
      {favs.map((f) => (
        <div key={f.id} role="listitem" className="tel-fav">
          <button
            type="button"
            className="tel-fav-main"
            aria-label={`Llamar a ${f.name || f.phone}`}
            onClick={() => ctx.place({ contactId: f.id, phone: f.phone, name: f.name })}
          >
            <Avatar name={f.name} size="lg" />
            <span className="tel-fav-name">{f.name || f.phone}</span>
          </button>
          <button
            type="button"
            className="tel-link"
            aria-label={`Ver ${f.name || f.phone}`}
            onClick={() => open(f.id)}
          >
            Ver
          </button>
        </div>
      ))}
    </div>
  );
}

// ---- Recientes ----

function RecentRow({
  c,
  ctx,
  open,
  save,
}: {
  c: CallSummary;
  ctx: PhoneCtx;
  open: (id: string) => void;
  save: (phone: string) => void;
}) {
  const name = (c.contact_name as string | null | undefined) || null;
  const label = name || c.phone || 'Número privado';
  const { missed } = callDirection(c);
  return (
    <div className="tel-row" role="listitem">
      <button
        type="button"
        className="tel-row-main"
        onClick={() => (c.contact_id ? open(c.contact_id) : c.phone ? save(c.phone) : undefined)}
        aria-label={c.contact_id ? `Ver ${label}` : `Guardar ${label} como contacto`}
      >
        <Avatar name={name} />
        <span className="tel-row-text">
          <span className="tel-row-title" data-missed={missed || undefined}>
            {label}
          </span>
          <span className="tel-row-sub">
            <DirectionIcon c={c} />
            {timeLabel(c.created_at)}
            {c.duration_seconds ? ` · ${formatDuration(c.duration_seconds)}` : ''}
            {name && c.phone ? ` · ${c.phone}` : ''}
          </span>
        </span>
      </button>
      {!c.contact_id && c.phone && (
        <ActionIcon
          variant="subtle"
          color="gray"
          size="lg"
          radius="xl"
          aria-label={`Guardar ${c.phone} como contacto`}
          onClick={() => save(c.phone!)}
        >
          <IconUserPlus size={20} />
        </ActionIcon>
      )}
      {c.phone && (
        <CallIcon
          phone={c.phone}
          label={label}
          onCall={() => ctx.place({ contactId: c.contact_id ?? null, phone: c.phone, name })}
        />
      )}
    </div>
  );
}

function RecentsTab({ ctx, open }: { ctx: PhoneCtx; open: (id: string) => void }) {
  const calls = useMyCalls(ctx.me.id, RECENTS);
  const [saving, setSaving] = useState<string | null>(null);
  const items = useMemo(
    () => (calls.data?.items ?? []).filter((c) => c.mode !== 'whatsapp'),
    [calls.data],
  );
  if (calls.isError)
    return (
      <Empty>
        No pudimos traer tus llamadas.{' '}
        <button type="button" className="tel-link" onClick={() => void calls.refetch()}>
          Reintentar
        </button>
      </Empty>
    );
  if (calls.isPending) return <Loader className="tel-loader" />;
  if (!items.length)
    return <Empty>Todavía no hiciste ni atendiste llamadas. Marcá un número o elegí un contacto.</Empty>;
  return (
    <>
      {groupByDay(items).map((g) => (
        <section key={g.label} aria-label={g.label}>
          <h2 className="tel-section">{g.label}</h2>
          <div role="list">
            {g.items.map((c) => (
              <RecentRow key={c.id} c={c} ctx={ctx} open={open} save={setSaving} />
            ))}
          </div>
        </section>
      ))}
      {saving && <SaveContactModal phone={saving} onClose={() => setSaving(null)} />}
    </>
  );
}

// ---- Contactos y búsqueda ----

function ContactRows({
  items,
  ctx,
  open,
  letters,
}: {
  items: Contact[];
  ctx: PhoneCtx;
  open: (id: string) => void;
  letters?: boolean;
}) {
  return (
    <div role="list" aria-label="Contactos">
      {withLetters(items, (k) => k.name || k.phone).map(({ item: k, head }) => {
        const label = k.name || k.phone;
        return (
          <div key={k.id}>
            {letters && head && <h2 className="tel-section tel-letter">{head}</h2>}
            <div className="tel-row" role="listitem">
              <button type="button" className="tel-row-main" onClick={() => open(k.id)} aria-label={`Ver ${label}`}>
                <Avatar name={k.name} />
                <span className="tel-row-text">
                  <span className="tel-row-title">{label}</span>
                  {(k.name || ctx.blocked.has(k.phone) || ctx.optedOut.has(k.phone)) && (
                    <span className="tel-row-sub">
                      {k.name && <span className="mono">{k.phone}</span>}
                      {ctx.optedOut.has(k.phone) && <span className="tel-tag">No quiere llamadas</span>}
                      {ctx.blocked.has(k.phone) && <span className="tel-tag" data-red>Bloqueado</span>}
                    </span>
                  )}
                </span>
              </button>
              <CallIcon
                phone={k.phone}
                label={label}
                onCall={() => ctx.place({ contactId: k.id, phone: k.phone, name: k.name })}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ContactsTab({ ctx, open }: { ctx: PhoneCtx; open: (id: string) => void }) {
  const contacts = useContacts({ q: '', archived: 'false', offset: 0 });
  const items = useMemo(
    () =>
      [...(contacts.data?.items ?? [])].sort((a, b) =>
        (a.name || a.phone).localeCompare(b.name || b.phone, 'es'),
      ),
    [contacts.data],
  );
  const total = contacts.data?.total ?? 0;
  if (contacts.isError)
    return (
      <Empty>
        No pudimos traer tus contactos.{' '}
        <button type="button" className="tel-link" onClick={() => void contacts.refetch()}>
          Reintentar
        </button>
      </Empty>
    );
  if (contacts.isPending) return <Loader className="tel-loader" />;
  if (!items.length)
    return <Empty>Tu agenda está vacía. Guardá un número desde Recientes o cargá contactos en el panel.</Empty>;
  return (
    <>
      <ContactRows items={items} ctx={ctx} open={open} letters />
      {total > items.length && (
        <Empty>
          Se muestran {items.length} de {total}: buscá arriba para encontrar el resto.
        </Empty>
      )}
    </>
  );
}

function SearchResults({ q, ctx, open }: { q: string; ctx: PhoneCtx; open: (id: string) => void }) {
  const contacts = useContacts({ q, archived: 'false', offset: 0 });
  const items = contacts.data?.items ?? [];
  const phone = clean(q);
  const dialable = E164_RE.test(phone);
  return (
    <>
      {dialable && (
        <div className="tel-row" role="listitem">
          <button
            type="button"
            className="tel-row-main"
            onClick={() => ctx.place({ phone })}
            aria-label={`Llamar a ${phone}`}
          >
            <Avatar />
            <span className="tel-row-text">
              <span className="tel-row-title">Llamar a {phone}</span>
            </span>
          </button>
        </div>
      )}
      {contacts.isError ? (
        <Empty>No pudimos buscar. Probá de nuevo.</Empty>
      ) : contacts.isPending ? (
        <Loader className="tel-loader" />
      ) : items.length ? (
        <ContactRows items={items} ctx={ctx} open={open} />
      ) : (
        !dialable && <Empty>Ningún contacto coincide con «{q}».</Empty>
      )}
    </>
  );
}

function ContactScreen({
  id,
  ctx,
  fav,
  onBack,
}: {
  id: string;
  ctx: PhoneCtx;
  fav: ReturnType<typeof useFavorites>;
  onBack: () => void;
}) {
  const contact = useContact(id);
  const history = useContactCalls(id, 10);
  const [copied, setCopied] = useState(false);
  const k = contact.data;
  const isFav = fav.has(id);
  const out = k ? ctx.optedOut.get(k.phone) : undefined;
  const isBlocked = !!k && ctx.blocked.has(k.phone);
  const why = k ? ctx.reason(k.phone) : null;

  const copy = () => {
    if (!k) return;
    void navigator.clipboard
      ?.writeText(k.phone)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => undefined);
  };

  return (
    <div className="tel-screen">
      <header className="tel-bar">
        <ActionIcon variant="subtle" color="gray" size="lg" radius="xl" aria-label="Volver" onClick={onBack}>
          <IconArrowLeft size={22} />
        </ActionIcon>
        <span className="tel-bar-title" />
        {k && (
          <ActionIcon
            variant="subtle"
            color={isFav ? 'yellow' : 'gray'}
            size="lg"
            radius="xl"
            aria-label={isFav ? 'Quitar de favoritos' : 'Agregar a favoritos'}
            aria-pressed={isFav}
            onClick={() => fav.toggle({ id: k.id, name: k.name ?? null, phone: k.phone })}
          >
            {isFav ? <IconStarFilled size={22} /> : <IconStar size={22} />}
          </ActionIcon>
        )}
      </header>
      {contact.isError ? (
        <Empty>Este contacto ya no está en la agenda.</Empty>
      ) : !k ? (
        <Loader className="tel-loader" />
      ) : (
        <div className="tel-scroll">
          <div className="tel-contact-head">
            <Avatar name={k.name} size="xl" />
            <h1 className="tel-contact-name">{k.name || k.phone}</h1>
            {k.name && <p className="tel-muted mono">{k.phone}</p>}
          </div>
          <div className="tel-contact-actions">
            <Tooltip label={why} disabled={!why} withArrow multiline w={240}>
              <button
                type="button"
                className="tel-contact-action"
                data-disabled={!!why || undefined}
                onClick={() => ctx.place({ contactId: k.id, phone: k.phone, name: k.name })}
              >
                <span className="tel-control-icon">
                  <IconPhone size={24} />
                </span>
                Llamar
              </button>
            </Tooltip>
            <button type="button" className="tel-contact-action" onClick={copy}>
              <span className="tel-control-icon">{copied ? <IconCheck size={24} /> : <IconCopy size={24} />}</span>
              {copied ? 'Copiado' : 'Copiar número'}
            </button>
          </div>
          {out && (
            <Alert color="yellow" p="xs" mx="md" mb="sm">
              <Text size="sm">
                Pidió no recibir llamadas ({formatDate(out)}). Se puede llamar igual, con confirmación.
              </Text>
            </Alert>
          )}
          {isBlocked && (
            <Alert color="red" p="xs" mx="md" mb="sm">
              <Text size="sm">Número bloqueado: no se puede llamar. Se desbloquea en el panel, Contactos.</Text>
            </Alert>
          )}
          {k.notes && <p className="tel-notes">{k.notes}</p>}
          <h2 className="tel-section">Últimas llamadas</h2>
          {history.isPending ? (
            <Loader className="tel-loader" />
          ) : history.data?.length ? (
            <div role="list">
              {history.data.map((c) => (
                <div key={c.id} className="tel-row" role="listitem">
                  <span className="tel-row-main tel-row-static">
                    <span className="tel-row-text">
                      <span className="tel-row-title">{formatDate(c.created_at)}</span>
                      <span className="tel-row-sub">
                        <DirectionIcon c={c} />
                        {timeLabel(c.created_at)}
                        {c.duration_seconds ? ` · ${formatDuration(c.duration_seconds)}` : ''}
                        {c.mode !== 'directa' && c.answered_by !== 'team'
                          ? ` · ${c.agent_name ? `Agente ${c.agent_name}` : 'Agente'}`
                          : c.user_name
                            ? ` · ${c.user_name}`
                            : ''}
                      </span>
                    </span>
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <Empty>Sin llamadas con este contacto.</Empty>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Teclado para marcar ----

function Dialer({ ctx, onClose }: { ctx: PhoneCtx; onClose: () => void }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const phone = clean(value);
  const suggest = useContacts({ q: phone.replace(/^\+/, ''), archived: 'false', offset: 0 });
  const matches = phone.replace(/\D/g, '').length >= 3 ? (suggest.data?.items ?? []).slice(0, 3) : [];

  const submit = () => {
    if (!E164_RE.test(phone))
      return setError('Marcá con el código de país: + y entre 8 y 15 dígitos (ej. +54 9 351 555 1234).');
    setError(null);
    const contact = (suggest.data?.items ?? []).find((k) => k.phone === phone);
    ctx.place(contact ? { contactId: contact.id, phone, name: contact.name } : { phone });
  };

  return (
    <div className="tel-sheet" role="dialog" aria-label="Teclado">
      <header className="tel-bar">
        <ActionIcon variant="subtle" color="gray" size="lg" radius="xl" aria-label="Cerrar el teclado" onClick={onClose}>
          <IconX size={22} />
        </ActionIcon>
        <span className="tel-bar-title">{ctx.from ? `Desde ${numberLabel(ctx.from)}` : ''}</span>
      </header>
      <div className="tel-dial-suggest" role="list" aria-label="Contactos que coinciden">
        {matches.map((k) => (
          <button
            key={k.id}
            type="button"
            role="listitem"
            className="tel-row-main"
            onClick={() => ctx.place({ contactId: k.id, phone: k.phone, name: k.name })}
          >
            <Avatar name={k.name} />
            <span className="tel-row-text">
              <span className="tel-row-title">{k.name || k.phone}</span>
              {k.name && <span className="tel-row-sub mono">{k.phone}</span>}
            </span>
          </button>
        ))}
      </div>
      <form
        className="tel-dial"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="tel-dial-display">
          <input
            className="tel-dial-input mono"
            aria-label="Número"
            type="tel"
            inputMode="none"
            autoComplete="off"
            placeholder="+54…"
            value={value}
            onChange={(e) => {
              setValue(e.currentTarget.value);
              setError(null);
            }}
          />
          {value && (
            <ActionIcon
              variant="subtle"
              color="gray"
              size="xl"
              radius="xl"
              aria-label="Borrar"
              onClick={() => setValue((v) => v.slice(0, -1))}
              onContextMenu={(e) => {
                e.preventDefault();
                setValue('');
              }}
            >
              <IconBackspace size={24} />
            </ActionIcon>
          )}
        </div>
        {error && (
          <p className="tel-call-error" role="alert">
            {error}
          </p>
        )}
        <Keypad
          keys={DIAL_KEYS}
          onKey={(k) => {
            setError(null);
            setValue((v) => (k === '+' ? (v.startsWith('+') ? v : `+${v}`) : v + k));
          }}
        />
        <button type="submit" className="tel-round tel-answer tel-dial-call" aria-label="Llamar">
          <IconPhone size={30} />
        </button>
      </form>
    </div>
  );
}

// ---- Menú de la cuenta ----

function AccountMenu({ ctx }: { ctx: PhoneCtx }) {
  const presence = usePresence();
  const logout = useLogout();
  const me = ctx.me;
  return (
    <Menu position="bottom-end" width={280} shadow="md" closeOnItemClick={false}>
      <Menu.Target>
        <button type="button" className="tel-me" aria-label="Tu cuenta">
          <Avatar name={me.name || me.email} />
          {presence.available && <span className="tel-me-dot" aria-label="Disponible" />}
        </button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>
          <Text size="sm" fw={600} c="dark">
            {me.name || me.email}
          </Text>
          <Text size="xs" c="dimmed">
            {me.client_name}
          </Text>
        </Menu.Label>
        <Menu.Divider />
        <div className="tel-menu-row">
          <Switch
            label="Disponible para atender"
            description="Te suenan acá las llamadas de tus números."
            color="green"
            checked={presence.available}
            disabled={!!presence.disabledReason}
            onChange={(e) => presence.setAvailable(e.currentTarget.checked)}
          />
        </div>
        {ctx.own.length > 1 && (
          <>
            <Menu.Divider />
            <Menu.Label>Llamar desde</Menu.Label>
            {ctx.own.map((n) => (
              <Menu.Item
                key={n.id}
                onClick={() => ctx.pickFrom(n.id)}
                rightSection={ctx.from?.id === n.id ? <IconCheck size={16} /> : null}
                aria-checked={ctx.from?.id === n.id}
                role="menuitemradio"
              >
                {numberLabel(n)}
              </Menu.Item>
            ))}
          </>
        )}
        <Menu.Divider />
        <Menu.Item leftSection={<IconLogout size={16} />} onClick={() => logout.mutate()}>
          Cerrar sesión
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

// ---- App ----

export function PhoneApp() {
  usePageTitle('Teléfono');
  const ctx = usePhone();
  const c = useDirectCall();
  const presence = usePresence();
  const plan = usePlanFeatures();
  const lock = useFeatureLock('direct_calls');
  const fav = useFavorites(ctx.me.id);
  const [tab, setTab] = useState<Tab>(() => (fav.list.length ? 'favorites' : 'recents'));
  const [search, setSearch] = useState('');
  const [contactId, setContactId] = useState<string | null>(null);
  const [dialer, setDialer] = useState(false);

  const q = search.trim();
  const ring = presence.rings[0];

  // Lo que ocupa la pantalla: la llamada en curso, la entrante, la terminada (o con error) y si no, la app.
  let overlay: ReactNode = null;
  if (c.busy) overlay = <InCallScreen onRedial={() => undefined} />;
  else if (ring) overlay = <IncomingScreen ring={ring} more={presence.rings.length - 1} />;
  else if (c.phase === 'ended' || c.phase === 'error')
    overlay = (
      <InCallScreen
        onRedial={() => {
          const t = c.target;
          if (t?.phone) ctx.place({ contactId: t.contactId, phone: t.phone, name: t.name });
        }}
      />
    );

  if (plan.isPending) return <Loader className="tel-loader" />;
  if (lock.locked)
    return (
      <div className="tel-app">
        <div className="tel-blocked">
          <IconPhone size={40} />
          <h1>Tu plan no incluye las llamadas del equipo</h1>
          <p>{lock.reason ?? 'Mejorá el plan desde el panel para llamar y atender desde acá.'}</p>
        </div>
      </div>
    );

  const open = (id: string) => {
    setContactId(id);
    setDialer(false);
  };

  return (
    <div className="tel-app">
      {contactId ? (
        <ContactScreen id={contactId} ctx={ctx} fav={fav} onBack={() => setContactId(null)} />
      ) : (
        <div className="tel-screen">
          <header className="tel-top">
            <label className="tel-search">
              {q ? (
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  radius="xl"
                  aria-label="Cerrar la búsqueda"
                  onClick={() => setSearch('')}
                >
                  <IconArrowLeft size={20} />
                </ActionIcon>
              ) : (
                <IconSearch size={20} className="tel-search-icon" />
              )}
              <input
                type="search"
                aria-label="Buscar contactos"
                placeholder="Buscar contactos"
                value={search}
                onChange={(e) => setSearch(e.currentTarget.value)}
              />
              <AccountMenu ctx={ctx} />
            </label>
          </header>
          <div className="tel-banners">
            {c.disabledReason && (
              <Alert color="yellow" p="xs">
                <Text size="sm">{c.disabledReason}</Text>
              </Alert>
            )}
            {ctx.numbers.data && !ctx.own.length && (
              <Alert color="yellow" p="xs">
                <Text size="sm">Todavía no tenés un número asignado: hace falta uno para llamar.</Text>
              </Alert>
            )}
            {c.rejoinId && !c.busy && (
              <Alert color="blue" p="xs">
                <Text size="sm" mb={6}>
                  Tenés una llamada en curso.
                </Text>
                <div className="tel-banner-actions">
                  <button
                    type="button"
                    className="tel-pill tel-pill-strong"
                    onClick={() => {
                      const id = c.rejoinId!;
                      void c.join(id).then((r) => {
                        if (!r.ok && r.problem) notifyError(new Error(r.problem.message), r.problem.title);
                      });
                    }}
                  >
                    Volver a entrar
                  </button>
                  <button type="button" className="tel-link" onClick={c.dismissRejoin}>
                    Descartar
                  </button>
                </div>
              </Alert>
            )}
          </div>
          <main className="tel-scroll">
            {q ? (
              <SearchResults q={q} ctx={ctx} open={open} />
            ) : tab === 'favorites' ? (
              <FavoritesTab favs={fav.list} ctx={ctx} open={open} />
            ) : tab === 'recents' ? (
              <RecentsTab ctx={ctx} open={open} />
            ) : (
              <ContactsTab ctx={ctx} open={open} />
            )}
          </main>
          <button type="button" className="tel-fab" aria-label="Abrir el teclado" onClick={() => setDialer(true)}>
            <IconDialpad size={26} />
          </button>
          <nav className="tel-nav" aria-label="Secciones">
            {(
              [
                ['favorites', 'Favoritos', <IconStar key="i" size={22} />],
                ['recents', 'Recientes', <IconClock key="i" size={22} />],
                ['contacts', 'Contactos', <IconUsers key="i" size={22} />],
              ] as const
            ).map(([key, label, icon]) => (
              <button
                key={key}
                type="button"
                className="tel-nav-item"
                aria-current={tab === key && !q ? 'page' : undefined}
                onClick={() => {
                  setTab(key);
                  setSearch('');
                }}
              >
                <span className="tel-nav-icon">{icon}</span>
                {label}
              </button>
            ))}
          </nav>
        </div>
      )}
      {dialer && <Dialer ctx={ctx} onClose={() => setDialer(false)} />}
      {overlay}
    </div>
  );
}
