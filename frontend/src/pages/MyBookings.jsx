import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Confirm, Empty, ErrorNote, Loading, StatusBadge, errText, fmtDate, fmtHours, useToast } from '../ui.jsx';

function Row({ b, past, onCancel }) {
  const status = past && b.status === 'approved' ? 'completed' : b.status;
  const note = b.note && (b.status === 'rejected' ? `Rejected: ${b.note}` : b.status === 'cancelled' ? `Cancelled: ${b.note}` : '');
  return (
    <div className="item">
      <div className="info">
        <b>{b.lab_id} · {fmtDate(b.start_date)} · {fmtHours(b.hours)}</b>
        <small>{note || `${b.reason}${b.faculty ? ` · ${b.faculty}` : ''}`}</small>
      </div>
      <StatusBadge status={status} />
      {onCancel && <button className="btn ghost small" onClick={() => onCancel(b)}>Cancel</button>}
    </div>
  );
}

export default function MyBookings() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [target, setTarget] = useState(null);

  const load = () => api('/students/me/bookings').then(setData).catch((e) => { setErr(errText(e)); setData({ waiting: [], confirmed: [], past: [] }); });
  useEffect(() => { load(); }, []);

  if (!data) return <Loading />;
  const sections = [['Waiting for approval', data.waiting, false, true, 'Nothing waiting. Book a lab to send a request.'],
    ['Confirmed', data.confirmed, false, true, 'No confirmed bookings yet.'],
    ['Past', data.past, true, false, 'Your past bookings will show here.']];

  return (
    <>
      <h1>My bookings</h1>
      <ErrorNote>{err}</ErrorNote>
      {sections.map(([title, list, past, canCancel, empty]) => (
        <section className="card" key={title}>
          <h2>{title}</h2>
          {!list.length ? <Empty>{empty}</Empty> : list.map((b) => (
            <Row key={b._id} b={b} past={past} onCancel={canCancel ? setTarget : null} />
          ))}
        </section>
      ))}
      {target && (
        <Confirm title="Cancel this booking?" danger confirmLabel="Yes, cancel it"
          text={`${target.lab_id} · ${fmtDate(target.start_date)} · ${fmtHours(target.hours)}`}
          onClose={() => setTarget(null)}
          onConfirm={async () => { await api(`/bookings/${target._id}/cancel`, { method: 'POST' }); toast('Booking cancelled.'); load(); }} />
      )}
    </>
  );
}
