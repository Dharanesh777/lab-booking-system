import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Confirm, Empty, ErrorNote, Loading, Modal, PERIODS, errText, fmtDate, fmtHours, fmtLong, toISO, useToast } from '../ui.jsx';

function Detail({ label, children }) {
  return (
    <div className="detail">
      <span>{label}</span>
      <b>{children || '—'}</b>
    </div>
  );
}

export default function Approvals() {
  const toast = useToast();
  const [pending, setPending] = useState(null);
  const [approved, setApproved] = useState(null);
  const [err, setErr] = useState('');
  const [open, setOpen] = useState(null);   // booking shown in the pop-up
  const [dlg, setDlg] = useState(null);     // {kind:'reject'|'cancel', b}
  const [busy, setBusy] = useState(false);
  const [popErr, setPopErr] = useState('');

  const load = async () => {
    try {
      const [p, a] = await Promise.all([
        api('/admin/pending'),
        api('/admin/bookings', { params: { status: 'approved', type: 'student', from_date: toISO(new Date()) } }),
      ]);
      setPending(p); setApproved(a);
    } catch (e) { setErr(errText(e)); setPending((x) => x || []); setApproved((x) => x || []); }
  };
  useEffect(() => { load(); }, []);

  const openBooking = (b) => { setPopErr(''); setOpen(b); };

  const approve = async () => {
    setBusy(true); setPopErr('');
    try {
      await api(`/admin/bookings/${open._id}/approve`, { method: 'POST' });
      toast(`Approved ${open.student?.name}'s request.`);
      setOpen(null); load();
    } catch (e) { setPopErr(errText(e)); }
    setBusy(false);
  };

  if (!pending || !approved) return <Loading />;
  const who = (b) => `${b.student?.name} · ${b.student?.roll_no}`;
  const what = (b) => `${b.lab_id} · ${fmtDate(b.start_date)} · ${fmtHours(b.hours)}`;
  const isPending = open?.status === 'pending';

  return (
    <>
      <h1>Approvals</h1>
      <ErrorNote>{err}</ErrorNote>

      <section className="card">
        <h2>Waiting for approval ({pending.length})</h2>
        {!pending.length ? <Empty>You're all caught up. No requests are waiting.</Empty> : pending.map((b) => (
          <button className="rowbtn" key={b._id} onClick={() => openBooking(b)}>
            <span className="info"><b>{who(b)}</b><small>{what(b)}</small></span>
            <span className="open">View details ›</span>
          </button>
        ))}
        {!!pending.length && <p className="muted tip">Tap a request to see the full details and approve or reject it.</p>}
      </section>

      <section className="card">
        <h2>Approved bookings</h2>
        <p className="muted tip" style={{ marginTop: 0 }}>Tap one to cancel it, for example for a sudden placement drive.</p>
        {!approved.length ? <Empty>No upcoming approved bookings.</Empty> : approved.map((b) => (
          <button className="rowbtn" key={b._id} onClick={() => openBooking(b)}>
            <span className="info"><b>{who(b)}</b><small>{what(b)}</small></span>
            <span className="open">View details ›</span>
          </button>
        ))}
      </section>

      {open && !dlg && (
        <Modal title={isPending ? 'Booking request' : 'Approved booking'} onClose={() => setOpen(null)}>
          <div className="details">
            <Detail label="Student">{open.student?.name}</Detail>
            <Detail label="Roll number">{open.student?.roll_no}</Detail>
            <Detail label="Mobile">{open.student?.phone && <a href={`tel:${open.student.phone}`}>{open.student.phone}</a>}</Detail>
            <Detail label="Email">{open.student?.email}</Detail>
            <Detail label="Lab">{open.lab_id}</Detail>
            <Detail label="Date">{fmtLong(open.start_date)}</Detail>
            <Detail label="Hours">
              {[...open.hours].sort((a, b) => a - b).map((h) => <span className="hr" key={h}>Hour {h} <small>({PERIODS[h]})</small></span>)}
            </Detail>
            <Detail label="Faculty in charge">{open.faculty}</Detail>
            <Detail label="Reason">{open.reason}</Detail>
          </div>
          <ErrorNote>{popErr}</ErrorNote>
          {isPending ? (
            <div className="actions">
              <button className="btn big" onClick={approve} disabled={busy}>{busy ? 'Approving…' : 'Approve'}</button>
              <button className="btn ghost big" onClick={() => setDlg({ kind: 'reject', b: open })} disabled={busy}>Reject</button>
            </div>
          ) : (
            <div className="actions">
              <button className="btn danger big" onClick={() => setDlg({ kind: 'cancel', b: open })}>Cancel this booking</button>
              <button className="btn ghost big" onClick={() => setOpen(null)}>Close</button>
            </div>
          )}
        </Modal>
      )}

      {dlg?.kind === 'reject' && (
        <Confirm title="Reject this request?" danger confirmLabel="Reject" text={`${who(dlg.b)} · ${what(dlg.b)}`}
          reasonLabel="Reason (the student will see this)" onClose={() => setDlg(null)}
          onConfirm={async (reason) => {
            await api(`/admin/bookings/${dlg.b._id}/reject`, { method: 'POST', params: { reason } });
            toast('Request rejected.'); setOpen(null); load();
          }} />
      )}
      {dlg?.kind === 'cancel' && (
        <Confirm title="Cancel this booking?" danger confirmLabel="Cancel booking" text={`${who(dlg.b)} · ${what(dlg.b)}`}
          reasonLabel="Reason (the student will see this)" reasonRequired onClose={() => setDlg(null)}
          onConfirm={async (reason) => {
            await api(`/admin/bookings/${dlg.b._id}/cancel`, { method: 'POST', params: { reason } });
            toast('Booking cancelled.'); setOpen(null); load();
          }} />
      )}
    </>
  );
}
