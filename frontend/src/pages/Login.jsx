import { useState } from 'react';
import { useAuth } from '../auth.jsx';
import { ErrorNote, errText } from '../ui.jsx';

export default function Login() {
  const { login, register, logout } = useAuth();
  const [role, setRole] = useState('student');
  const [mode, setMode] = useState('login');
  const [f, setF] = useState({ name: '', roll_no: '', phone: '', email: '', password: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const signup = mode === 'signup' && role === 'student';

  const submit = async (e) => {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      const u = signup ? await register(f) : await login(f.email, f.password);
      if (u.role !== role) {
        logout();
        setErr(role === 'admin' ? 'This is a student account. Choose "Student" above.' : 'This is an admin account. Choose "Admin" above.');
      }
    } catch (e2) { setErr(errText(e2)); }
    setBusy(false);
  };

  return (
    <>
      <header className="nav">
        <strong>PSG Tech · Lab Slots</strong>
        <span>CSE / AI Wing</span>
      </header>
      <main className="page">
        <form className="card login" onSubmit={submit}>
          <h1>{signup ? 'Create account' : 'Log in'}</h1>
          <div className="tabs">
            {['student', 'admin'].map((r) => (
              <button type="button" key={r} className={`btn ${role === r ? '' : 'ghost'}`}
                onClick={() => { setRole(r); setMode('login'); setErr(''); }}>
                {r === 'student' ? 'Student' : 'Admin'}
              </button>
            ))}
          </div>
          <div className="stack">
            {signup && (
              <>
                <label className="field"><span>Full name</span><input required value={f.name} onChange={set('name')} autoComplete="name" /></label>
                <label className="field"><span>Roll number</span><input required value={f.roll_no} onChange={set('roll_no')} placeholder="e.g. 23N001" /></label>
                <label className="field"><span>Mobile number</span><input required inputMode="numeric" maxLength={10} value={f.phone} onChange={set('phone')} placeholder="10 digits" autoComplete="tel" /></label>
              </>
            )}
            <label className="field"><span>College email</span><input required type="email" value={f.email} onChange={set('email')} placeholder={role === 'student' ? '23n001@psgtech.ac.in' : ''} autoComplete="username" /></label>
            <label className="field">
              <span>Password {signup && <small>(8+ characters, with a letter and a number)</small>}</span>
              <input required type="password" value={f.password} onChange={set('password')} autoComplete={signup ? 'new-password' : 'current-password'} />
            </label>
            <ErrorNote>{err}</ErrorNote>
            <button className="btn" disabled={busy}>{busy ? 'Please wait…' : signup ? 'Create account' : 'Log in'}</button>
          </div>
          {role === 'student' && (
            <p className="hint mt">
              {signup ? 'Already have an account? ' : 'New student? '}
              <button type="button" className="link" onClick={() => { setMode(signup ? 'login' : 'signup'); setErr(''); }}>
                {signup ? 'Log in' : 'Create an account'}
              </button>
            </p>
          )}
        </form>
      </main>
    </>
  );
}
