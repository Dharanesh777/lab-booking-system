import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import {
  addDays, toISO, fmtLong, fmtDate, fmtDay, fmtHours,
  useToast, errText, ErrorNote, Loading, Empty, Modal, Confirm,
} from '../ui.jsx';

const LABEL = { free: 'Free', pending: 'Waiting', booked: 'Booked' };
const parseISO = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };

function Cell({ lab, cell, last, isAdmin, onOpen }) {
  const past = cell.past;
  const cls = `cell ${past ? 'past' : cell.status}${last ? ' last' : ''}`;
  const text = past ? 'Past' : LABEL[cell.status];
  const clickable = !past && (isAdmin || cell.status !== 'booked');   // students cannot click red
  const b = cell.booking;
  const hover = !past && isAdmin && cell.status === 'booked' && b && (
    <span className="hov">
      <b>{b.name}</b>{b.roll_no ? ` · ${b.roll_no}` : ''}<br />
      {b.reason}{b.faculty ? ` · ${b.faculty}` : ''}<br />
      Click for details
    </span>
  );
  if (!clickable) return <span className={cls}>{text}</span>;
  return (
    <button type="button" className={cls} onClick={() => onOpen(lab, cell)}
      aria-label={`${lab.name}, hour ${cell.hour}, ${text}`}>
      {text}{hover}
    </button>
  );
}

/* admin: details of a red slot, with cancel */
function BookedModal({ lab, cell, date, onClose, onChanged }) {
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const b = cell.booking;
  const block = b.type === 'admin_block';

  const cancel = async (reason) => {
    await api(`/admin/bookings/${b.id}/cancel`, { method: 'POST', params: { reason } });
    toast(block ? 'Block cancelled.' : 'Booking cancelled. The student is notified.');
    onChanged();
  };

  if (confirm) {
    return (
      <Confirm
        title={block ? 'Cancel this whole block?' : 'Cancel this booking?'}
        text={block
          ? `This frees ${fmtDay(b.start_date)} to ${fmtDay(b.end_date)}, every blocked hour.`
          : `This cancels ${b.name}'s whole booking (${fmtHours(b.hours)}) on ${fmtDate(b.start_date)}.`}
        reasonLabel="Reason (sent to the student)" reasonRequired danger
        confirmLabel={block ? 'Cancel block' : 'Cancel booking'}
        onConfirm={cancel} onClose={() => setConfirm(false)} />
    );
  }
  return (
    <Modal title={block ? 'Blocked by admin' : 'Booked'} onClose={onClose}>
      <div className="details">
        <div className="detail"><span>Lab</span><b>{lab.name}</b></div>
        <div className="detail"><span>Slot</span><b>{fmtDate(date)} · hour {cell.hour}</b></div>
        {block ? (
          <>
            <div className="detail"><span>Blocked</span><b>{fmtDay(b.start_date)} to {fmtDay(b.end_date)} · {fmtHours(b.hours)}</b></div>
            <div className="detail"><span>Reason</span><b>{b.reason}</b></div>
            <div className="detail"><span>Blocked by</span><b>{b.decided_by}</b></div>
          </>
        ) : (
          <>
            <div className="detail"><span>Name</span><b>{b.name}</b></div>
            <div className="detail"><span>Roll number</span><b>{b.roll_no}</b></div>
            <div className="detail"><span>Phone</span><b><a href={`tel:${b.phone}`}>{b.phone}</a></b></div>
            <div className="detail"><span>Email</span><b>{b.email}</b></div>
            <div className="detail"><span>Faculty</span><b>{b.faculty}</b></div>
            <div className="detail"><span>Reason</span><b>{b.reason}</b></div>
            <div className="detail"><span>Hours booked</span><b>{fmtHours(b.hours)}</b></div>
          </>
        )}
      </div>
      <div className="actions">
        <button className="btn danger" onClick={() => setConfirm(true)}>
          {block ? 'Cancel whole block' : 'Cancel booking'}
        </button>
        <button className="btn ghost" onClick={onClose}>Close</button>
      </div>
    </Modal>
  );
}

/* admin: requests behind an orange slot, approve or reject right here */
function PendingModal({ lab, cell, date, onClose, onChanged }) {
  const toast = useToast();
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [rejecting, setRejecting] = useState(null);

  const approve = async (r) => {
    setBusy(r.id); setErr('');
    try {
      await api(`/admin/bookings/${r.id}/approve`, { method: 'POST' });
      toast(`Approved ${r.name}. The student is notified.`);
      onChanged();
    } catch (e) { setErr(errText(e)); setBusy(''); }
  };
  const reject = async (reason) => {
    await api(`/admin/bookings/${rejecting.id}/reject`, { method: 'POST', params: { reason } });
    toast(`Rejected ${rejecting.name}.`);
    onChanged();
  };

  if (rejecting) {
    return (
      <Confirm title={`Reject ${rejecting.name}?`} reasonLabel="Reason (optional, sent to the student)"
        danger confirmLabel="Reject" onConfirm={reject} onClose={() => setRejecting(null)} />
    );
  }
  return (
    <Modal title="Waiting for approval" onClose={onClose}>
      <p className="muted">{lab.name} · {fmtDate(date)} · hour {cell.hour}</p>
      {cell.requests.map((r) => (
        <div className="item" key={r.id}>
          <div className="info">
            <b>{r.name} · {r.roll_no}</b>
            <small>{r.reason} · {r.faculty}{r.hours ? ` · ${fmtHours(r.hours)}` : ''}</small>
          </div>
          <div className="row">
            <button className="btn small" disabled={!!busy} onClick={() => approve(r)}>
              {busy === r.id ? 'Approving…' : 'Approve'}
            </button>
            <button className="btn ghost small" disabled={!!busy} onClick={() => setRejecting(r)}>Reject</button>
          </div>
        </div>
      ))}
      <ErrorNote>{err}</ErrorNote>
      <div className="row end"><button className="btn ghost" onClick={onClose}>Close</button></div>
    </Modal>
  );
}

/* one timetable row: lab name, then one cell per hour */
function LabRow({ lab, periods, isAdmin, onOpen }) {
  return (
    <>
      <div className="labname">{lab.name}</div>
      {periods.map((p, i) => {
        const cell = lab.cells.find((c) => c.hour === p.hour);
        return cell ? (
          <Cell key={p.hour} lab={lab} cell={cell} last={i >= periods.length - 2} isAdmin={isAdmin} onOpen={onOpen} />
        ) : <span key={p.hour} className="cell past">–</span>;
      })}
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const isAdmin = user.role === 'admin';
  const nav = useNavigate();
  const today = new Date();
  const min = toISO(today);
  const max = toISO(addDays(today, 7));      // students can look 7 days ahead, same as booking
  const [date, setDate] = useState(min);
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [pop, setPop] = useState(null);

  const load = useCallback(() => {
    api('/dashboard', { params: { date } })
      .then((d) => { setData(d); setErr(''); })
      .catch((e) => setErr(errText(e)));
  }, [date]);

  // load on date change, then refresh every 30 seconds so the colours stay current
  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  const go = (n) => setDate(toISO(addDays(parseISO(date), n)));
  const canPrev = isAdmin || date > min;
  const canNext = isAdmin || date < max;

  const open = (lab, cell) => {
    const q = `?lab=${encodeURIComponent(lab.id)}&date=${date}&hour=${cell.hour}`;
    if (cell.status === 'free') return nav((isAdmin ? '/admin/block' : '/book') + q);
    if (cell.status === 'pending') return isAdmin ? setPop({ lab, cell }) : nav('/book' + q);
    if (cell.status === 'booked' && isAdmin) setPop({ lab, cell });
  };
  const changed = () => { setPop(null); load(); };

  return (
    <>
      <h1>Lab timetable</h1>
      <section className="card">
        <div className="row dash-bar">
          <button className="btn ghost small" onClick={() => go(-1)} disabled={!canPrev} aria-label="Previous day">‹</button>
          <b className="dash-date">{fmtLong(date)}</b>
          <button className="btn ghost small" onClick={() => go(1)} disabled={!canNext} aria-label="Next day">›</button>
          <input type="date" aria-label="Pick a date" style={{ maxWidth: 200 }} value={date}
            min={isAdmin ? undefined : min} max={isAdmin ? undefined : max}
            onChange={(e) => e.target.value && setDate(e.target.value)} />
        </div>

        <div className="legend">
          <span><i className="sw" style={{ background: '#CDEBD8' }} />Free</span>
          <span><i className="sw" style={{ background: '#FFD6A0' }} />Waiting for approval</span>
          <span><i className="sw" style={{ background: '#F4B6B6' }} />Booked</span>
          <span><i className="sw" style={{ background: 'var(--soft)' }} />Past hour</span>
        </div>

        <ErrorNote>{err}</ErrorNote>
        {!data ? <Loading /> : !data.labs.length ? <Empty>No labs are open right now.</Empty> : (
          <div className="tt-wrap">
            <div className="tt" style={{ '--cols': data.periods.length }}>
              <div className="corner">Lab / Hour</div>
              {data.periods.map((p) => (
                <div className="per" key={p.hour}><b>{p.hour}</b><small>{p.time.split(' - ')[0]}</small></div>
              ))}
              {data.labs.map((lab) => (
                <LabRow key={lab.id} lab={lab} periods={data.periods} isAdmin={isAdmin} onOpen={open} />
              ))}
            </div>
          </div>
        )}
        <p className="muted tip">
          {isAdmin
            ? 'Green: block it. Orange: approve or reject. Red: hover to see who, click for details and Cancel.'
            : 'Green or orange: click to request that hour. Red: already booked.'}
        </p>
      </section>

      {pop && pop.cell.status === 'pending' &&
        <PendingModal lab={pop.lab} cell={pop.cell} date={date} onClose={() => setPop(null)} onChanged={changed} />}
      {pop && pop.cell.status === 'booked' &&
        <BookedModal lab={pop.lab} cell={pop.cell} date={date} onClose={() => setPop(null)} onChanged={changed} />}
    </>
  );
}
