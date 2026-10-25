import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { Empty, ErrorNote, Loading, errText, useToast } from '../ui.jsx';

export default function Admins() {
  const { user } = useAuth();
  const toast = useToast();
  const [list, setList] = useState(null);
  const [f, setF] = useState({ name: '', email: '', password: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api('/admin/admins').then(setList).catch((e) => { setErr(errText(e)); setList([]); });
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault(); setBusy(true); setErr('');
    try { await api('/admin/admins', { method: 'POST', body: f }); toast('Admin added.'); setF({ name: '', email: '', password: '' }); load(); }
    catch (e2) { setErr(errText(e2)); }
    setBusy(false);
  };
  const toggle = async (a) => {
    setErr('');
    try { await api(`/admin/admins/${a._id}/${a.active ? 'disable' : 'enable'}`, { method: 'POST' }); toast(a.active ? 'Admin disabled.' : 'Admin enabled.'); load(); }
    catch (e) { setErr(errText(e)); }
  };

  if (!list) return <Loading />;
  return (
    <>
      <h1>Admins</h1>
      <form className="card" onSubmit={add}>
        <h2>Add an admin</h2>
        <div className="grid">
          <label className="field"><span>Name</span><input required value={f.name} onChange={set('name')} /></label>
          <label className="field"><span>Email</span><input required type="email" value={f.email} onChange={set('email')} /></label>
          <label className="field"><span>Password <small>(8+ characters, letter and number)</small></span><input required type="password" value={f.password} onChange={set('password')} autoComplete="new-password" /></label>
        </div>
        <ErrorNote>{err}</ErrorNote>
        <div className="mt"><button className="btn" disabled={busy}>{busy ? 'Adding…' : 'Add admin'}</button></div>
      </form>
      <section className="card">
        <h2>All admins</h2>
        {!list.length ? <Empty>No admins found.</Empty> : list.map((a) => (
          <div className="item" key={a._id}>
            <div className="info"><b>{a.name}{a._id === user._id ? ' (you)' : ''}</b><small>{a.email}</small></div>
            <span className={`badge ${a.active ? 'ok' : 'bad'}`}>{a.active ? 'Active' : 'Disabled'}</span>
            {a._id !== user._id && <button className="btn ghost small" onClick={() => toggle(a)}>{a.active ? 'Disable' : 'Enable'}</button>}
          </div>
        ))}
      </section>
    </>
  );
}
