import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { addDays, toISO, useToast, ErrorNote, errText, Loading, Empty } from '../ui.jsx';

export default function Book() {
  const { user } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const today = new Date();
  const [date, setDate] = useState(toISO(today));
  const [labs, setLabs] = useState(null);
  const [labId, setLabId] = useState('');
  const [slots, setSlots] = useState(null);
  const [picked, setPicked] = useState([]);
  const [f, setF] = useState({ name: user.name || '', phone: user.phone || '', faculty: '', reason: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  useEffect(() => {
    api('/labs').then((l) => { setLabs(l); if (l[0]) setLabId(l[0]._id); }).catch((e) => { setLabs([]); setErr(errText(e)); });
  }, []);

  const loadSlots = () => {
    if (!labId || !date) return;
    setSlots(null); setPicked([]);
    api(`/labs/${labId}/availability`, { params: { date } })
      .then(setSlots).catch((e) => { setSlots([]); setErr(errText(e)); });
  };
  useEffect(loadSlots, [labId, date]); // eslint-disable-line

  const toggle = (h) => setPicked((p) => (p.includes(h) ? p.filter((x) => x !== h) : [...p, h]));

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    if (!picked.length) return setErr('Pick at least one hour above.');
    if (!/^[6-9]\d{9}$/.test(f.phone)) return setErr('Enter a 10-digit mobile number.');
    setBusy(true);
    try {
      await api('/bookings', { method: 'POST', body: { lab_id: labId, date, hours: picked, ...f } });
      toast('Request sent. The admin will review it.');
      nav('/my-bookings');
    } catch (e2) { setErr(errText(e2)); if (e2.status === 409) loadSlots(); }
    setBusy(false);
  };

  return (
    <>
      <h1>Book a lab</h1>
      <form onSubmit={submit}>
        <section className="card">
          <h2>1 · Choose a date and lab</h2>
          <label className="field" style={{ maxWidth: 260, marginBottom: '1rem' }}>
            <span>Date <small>(today up to 7 days ahead)</small></span>
            <input type="date" required value={date} min={toISO(today)} max={toISO(addDays(today, 7))} onChange={(e) => setDate(e.target.value)} />
          </label>
          {!labs ? <Loading /> : !labs.length ? <Empty>No labs are open for booking right now.</Empty> : (
            <div className="labs">
              {labs.map((l) => (
                <button type="button" key={l._id} className={`lab ${labId === l._id ? 'on' : ''}`} onClick={() => setLabId(l._id)}>
                  <b>{l.name}</b>
                  <span>{l.capacity} seats{l.location ? ` · ${l.location}` : ''}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <h2>2 · Pick your hours <small className="muted">(crossed out = already booked)</small></h2>
          {!slots ? <Loading /> : (
            <div className="chips">
              {slots.map((s) => (
                <button type="button" key={s.hour} disabled={!s.available} title={s.time}
                  className={`chip ${picked.includes(s.hour) ? 'on' : ''}`} onClick={() => toggle(s.hour)}>
                  <b>{s.hour}</b><small>{s.time.split(' - ')[0]}</small>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <h2>3 · Your details</h2>
          <div className="grid">
            <label className="field"><span>Name</span><input required value={f.name} onChange={set('name')} /></label>
            <label className="field"><span>Roll number</span><input readOnly value={user.roll_no || ''} /></label>
            <label className="field"><span>Mobile number</span><input required inputMode="numeric" maxLength={10} value={f.phone} onChange={set('phone')} /></label>
            <label className="field"><span>College email</span><input readOnly value={user.email} /></label>
            <label className="field"><span>Faculty in charge</span><input required value={f.faculty} onChange={set('faculty')} placeholder="e.g. Dr. Kumar" /></label>
            <label className="field"><span>Reason</span><input required value={f.reason} onChange={set('reason')} placeholder="e.g. Project work" /></label>
          </div>
          <ErrorNote>{err}</ErrorNote>
          <div className="row mt">
            <button className="btn" disabled={busy || !labId}>{busy ? 'Sending…' : 'Send request'}</button>
            <span className="muted">Goes to the admin. You can track it under My bookings.</span>
          </div>
        </section>
      </form>
    </>
  );
}
