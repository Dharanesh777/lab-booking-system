import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Confirm, Empty, ErrorNote, Loading, errText, fmtDay, fmtHours, toISO, useToast } from '../ui.jsx';

export default function BlockLab() {
  const toast = useToast();
  const today = toISO(new Date());
  const [labs, setLabs] = useState(null);
  const [blocks, setBlocks] = useState(null);
  const [f, setF] = useState({ lab_id: '', start_date: today, end_date: today, reason: '' });
  const [hours, setHours] = useState([]);
  const [override, setOverride] = useState(false);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState(null);

  const loadBlocks = () => api('/admin/blocks', { params: { from_date: today } }).then(setBlocks).catch((e) => { setErr(errText(e)); setBlocks([]); });
  useEffect(() => {
    api('/admin/labs').then((l) => { const a = l.filter((x) => x.active); setLabs(a); if (a[0]) setF((s) => ({ ...s, lab_id: a[0]._id })); }).catch((e) => { setErr(errText(e)); setLabs([]); });
    loadBlocks();
  }, []); // eslint-disable-line

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const toggle = (h) => setHours((p) => (p.includes(h) ? p.filter((x) => x !== h) : [...p, h]));

  const submit = async (e) => {
    e.preventDefault(); setErr('');
    if (!hours.length) return setErr('Pick at least one hour.');
    if (f.end_date < f.start_date) return setErr('The "To" date cannot be before the "From" date.');
    setBusy(true);
    try {
      const res = await api('/admin/blocks', { method: 'POST', body: { ...f, hours, override } });
      const n = res.affected?.length || 0;
      toast(n ? `Lab blocked. ${n} booking${n > 1 ? 's' : ''} cancelled and students notified.` : 'Lab blocked.');
      setHours([]); setF({ ...f, reason: '' }); setOverride(false); loadBlocks();
    } catch (e2) {
      setErr(e2.status === 409 ? `${errText(e2)} Tick the box below to cancel those bookings.` : errText(e2));
    }
    setBusy(false);
  };

  if (!labs || !blocks) return <Loading />;
  return (
    <>
      <h1>Block a lab</h1>
      <form className="card" onSubmit={submit}>
        <h2>Pick a date range (one day up to a whole semester)</h2>
        <div className="grid">
          <label className="field"><span>Lab</span>
            <select required value={f.lab_id} onChange={set('lab_id')}>
              {labs.map((l) => <option key={l._id} value={l._id}>{l._id} · {l.name}</option>)}
            </select>
          </label>
          <label className="field"><span>From</span><input type="date" required min={today} value={f.start_date} onChange={set('start_date')} /></label>
          <label className="field"><span>To</span><input type="date" required min={f.start_date} value={f.end_date} onChange={set('end_date')} /></label>
        </div>
        <p className="muted" style={{ marginBottom: '.5rem' }}>Hours to block</p>
        <div className="chips">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((h) => (
            <button type="button" key={h} className={`chip ${hours.includes(h) ? 'on' : ''}`} onClick={() => toggle(h)}>{h}</button>
          ))}
          <button type="button" className="chip" onClick={() => setHours(hours.length === 8 ? [] : [1, 2, 3, 4, 5, 6, 7, 8])}>
            {hours.length === 8 ? 'Clear all' : 'Select all'}
          </button>
        </div>
        <label className="field mt"><span>Reason</span><input required value={f.reason} onChange={set('reason')} placeholder="e.g. Semester lab exams" /></label>
        <label className="check">
          <input type="checkbox" checked={override} onChange={(e) => setOverride(e.target.checked)} />
          Cancel existing bookings in this range (sudden placement)
        </label>
        <p className="muted" style={{ margin: '0 0 1rem' }}>Sundays are skipped. If ticked, affected students are cancelled and notified.</p>
        <ErrorNote>{err}</ErrorNote>
        <div className="mt"><button className="btn" disabled={busy}>{busy ? 'Blocking…' : 'Block lab'}</button></div>
      </form>

      <section className="card">
        <h2>Active blocks</h2>
        {!blocks.length ? <Empty>No labs are blocked right now.</Empty> : blocks.map((b) => (
          <div className="item" key={b._id}>
            <div className="info">
              <b>{b.lab_id} · {b.start_date === b.end_date ? fmtDay(b.start_date) : `${fmtDay(b.start_date)} to ${fmtDay(b.end_date)}`} · {fmtHours(b.hours)}</b>
              <small>{b.reason}</small>
            </div>
            <button className="btn ghost small" onClick={() => setTarget(b)}>Cancel block</button>
          </div>
        ))}
      </section>

      {target && (
        <Confirm title="Cancel this block?" danger confirmLabel="Cancel block" text="The lab becomes available for booking again."
          reasonLabel="Reason" reasonRequired onClose={() => setTarget(null)}
          onConfirm={async (reason) => { await api(`/admin/bookings/${target._id}/cancel`, { method: 'POST', params: { reason } }); toast('Block cancelled.'); loadBlocks(); }} />
      )}
    </>
  );
}
