import { createContext, useContext, useState, useCallback, useEffect } from 'react';

/* ---------- helpers ---------- */
export const PERIODS = {
  1: '08:30 - 09:20', 2: '09:20 - 10:10', 3: '10:30 - 11:20', 4: '11:20 - 12:10',
  5: '13:40 - 14:30', 6: '14:30 - 15:20', 7: '15:30 - 16:20', 8: '16:20 - 17:10',
};
export const fmtLong = (s) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};

export const toISO = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };

const parse = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };

export const fmtDate = (s) =>
  parse(s).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

export const fmtDay = (s) => parse(s).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });

export function fmtHours(hours = []) {
  const h = [...hours].sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < h.length; ) {
    let j = i;
    while (j + 1 < h.length && h[j + 1] === h[j] + 1) j++;
    out.push(j > i ? `${h[i]}-${h[j]}` : `${h[i]}`);
    i = j + 1;
  }
  return (h.length > 1 ? 'Hours ' : 'Hour ') + out.join(', ');
}

export function errText(err) {
  if (err?.status === 409 && err.data?.conflicts?.length) {
    const c = err.data.conflicts.map((x) => `${fmtDay(x.date)} hour ${x.hour}`).join(', ');
    return `${err.message} Already taken: ${c}.`;
  }
  return err?.message || 'Something went wrong. Please try again.';
}

/* ---------- toast ---------- */
const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [t, setT] = useState(null);
  const show = useCallback((msg, kind = 'ok') => setT({ msg, kind, id: Date.now() }), []);
  useEffect(() => {
    if (!t) return;
    const id = setTimeout(() => setT(null), 4000);
    return () => clearTimeout(id);
  }, [t]);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {t && <div className={`toast ${t.kind}`} role="status">{t.msg}</div>}
    </ToastCtx.Provider>
  );
}

/* ---------- small components ---------- */
export function StatusBadge({ status }) {
  const map = {
    pending: ['Waiting', 'warn'],
    approved: ['Confirmed', 'ok'],
    completed: ['Completed', 'ok'],
    cancelled: ['Cancelled', 'bad'],
    rejected: ['Rejected', 'bad'],
  };
  const [label, cls] = map[status] || [status, 'warn'];
  return <span className={`badge ${cls}`}>{label}</span>;
}

export const Loading = () => <p className="muted center-text">Loading…</p>;
export const Empty = ({ children }) => <p className="muted empty">{children}</p>;
export const ErrorNote = ({ children }) => (children ? <p className="error" role="alert">{children}</p> : null);

export function Modal({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

/** Confirm dialog. Pass `reasonLabel` to ask for a reason (set reasonRequired to force it). */
export function Confirm({ title, text, confirmLabel, reasonLabel, reasonRequired, danger, onConfirm, onClose }) {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const go = async () => {
    if (reasonLabel && reasonRequired && !reason.trim()) return setErr('Please write a reason.');
    setBusy(true); setErr('');
    try { await onConfirm(reason.trim()); onClose(); }
    catch (e) { setErr(errText(e)); setBusy(false); }
  };
  return (
    <Modal title={title} onClose={onClose}>
      {text && <p className="muted">{text}</p>}
      {reasonLabel && (
        <label className="field">
          <span>{reasonLabel}</span>
          <input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
      )}
      <ErrorNote>{err}</ErrorNote>
      <div className="row end">
        <button className="btn ghost" onClick={onClose} disabled={busy}>Go back</button>
        <button className={`btn ${danger ? 'danger' : ''}`} onClick={go} disabled={busy}>
          {busy ? 'Please wait…' : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
