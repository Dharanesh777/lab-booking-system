import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Confirm, Empty, ErrorNote, Loading, Modal, errText, useToast } from '../ui.jsx';

function LabForm({ lab, onSaved, onClose }) {
  const toast = useToast();
  const [f, setF] = useState({ code: lab?._id || '', name: lab?.name || '', capacity: lab?.capacity || '', department: lab?.department || 'CSE', location: lab?.location || '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr('');
    const body = { ...f, capacity: Number(f.capacity), location: f.location || null };
    try {
      if (lab) { const { code, ...rest } = body; await api(`/admin/labs/${lab._id}`, { method: 'PUT', body: rest }); }
      else await api('/admin/labs', { method: 'POST', body });
      toast(lab ? 'Lab updated.' : 'Lab added.'); onSaved(); onClose();
    } catch (e2) { setErr(errText(e2)); setBusy(false); }
  };
  return (
    <Modal title={lab ? `Edit ${lab._id}` : 'Add a lab'} onClose={onClose}>
      <form className="stack" onSubmit={save}>
        {!lab && <label className="field"><span>Lab code</span><input required value={f.code} onChange={set('code')} placeholder="e.g. LAB3" /></label>}
        <label className="field"><span>Name</span><input required value={f.name} onChange={set('name')} /></label>
        <label className="field"><span>Number of seats</span><input required type="number" min="1" value={f.capacity} onChange={set('capacity')} /></label>
        <label className="field"><span>Department</span><input required value={f.department} onChange={set('department')} /></label>
        <label className="field"><span>Location <small>(optional)</small></span><input value={f.location} onChange={set('location')} placeholder="e.g. 2nd floor, IT block" /></label>
        <ErrorNote>{err}</ErrorNote>
        <div className="row end"><button type="button" className="btn ghost" onClick={onClose}>Go back</button><button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button></div>
      </form>
    </Modal>
  );
}

export default function AdminLabs() {
  const toast = useToast();
  const [labs, setLabs] = useState(null);
  const [err, setErr] = useState('');
  const [form, setForm] = useState(null); // null | {} (new) | lab
  const [disable, setDisable] = useState(null); // {lab, force}

  const load = () => api('/admin/labs').then(setLabs).catch((e) => { setErr(errText(e)); setLabs([]); });
  useEffect(() => { load(); }, []);

  const enable = async (l) => {
    try { await api(`/admin/labs/${l._id}/enable`, { method: 'POST' }); toast(`${l.name} is open for booking.`); load(); }
    catch (e) { setErr(errText(e)); }
  };

  if (!labs) return <Loading />;
  return (
    <>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Labs</h1>
        <button className="btn" onClick={() => setForm({})}>Add a lab</button>
      </div>
      <ErrorNote>{err}</ErrorNote>
      <section className="card">
        {!labs.length ? <Empty>No labs yet. Add your first lab.</Empty> : labs.map((l) => (
          <div className="item" key={l._id}>
            <div className="info">
              <b>{l._id} · {l.name}</b>
              <small>{l.capacity} seats · {l.department}{l.location ? ` · ${l.location}` : ''}</small>
            </div>
            <span className={`badge ${l.active ? 'ok' : 'bad'}`}>{l.active ? 'Open' : 'Disabled'}</span>
            <div className="row">
              <button className="btn ghost small" onClick={() => setForm(l)}>Edit</button>
              {l.active
                ? <button className="btn ghost small" onClick={() => setDisable({ lab: l, force: false })}>Disable</button>
                : <button className="btn small" onClick={() => enable(l)}>Enable</button>}
            </div>
          </div>
        ))}
      </section>

      {form && <LabForm lab={form._id ? form : null} onSaved={load} onClose={() => setForm(null)} />}
      {disable && (
        <Confirm title={`Disable ${disable.lab.name}?`} danger confirmLabel={disable.force ? 'Disable anyway' : 'Disable'}
          text="Students will not be able to book this lab until you enable it again."
          onClose={() => setDisable(null)}
          onConfirm={async () => {
            try { await api(`/admin/labs/${disable.lab._id}/disable`, { method: 'POST', params: { force: disable.force ? 'true' : '' } }); toast('Lab disabled.'); load(); }
            catch (e) {
              if (!disable.force) setDisable({ ...disable, force: true });
              throw e;
            }
          }} />
      )}
    </>
  );
}
