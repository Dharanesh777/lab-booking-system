import { Navigate, NavLink, Route, Routes, Outlet } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Book from './pages/Book.jsx';
import MyBookings from './pages/MyBookings.jsx';
import Approvals from './pages/Approvals.jsx';
import BlockLab from './pages/BlockLab.jsx';
import AdminLabs from './pages/AdminLabs.jsx';
import Admins from './pages/Admins.jsx';

// role omitted = any logged-in user
function Shell({ role }) {
  const { user, logout } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/dashboard" replace />;
  const admin = user.role === 'admin';
  const links = admin
    ? [['/dashboard', 'Dashboard'], ['/admin/approvals', 'Approvals'], ['/admin/block', 'Block lab'], ['/admin/labs', 'Labs'], ['/admin/admins', 'Admins']]
    : [['/dashboard', 'Dashboard'], ['/book', 'Book a lab'], ['/my-bookings', 'My bookings']];
  return (
    <>
      <header className="nav">
        <strong>PSG Tech · Lab Slots{admin ? ' · Admin' : ''}</strong>
        <nav>
          {links.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
          <button className="linkbtn" onClick={logout}>Log out</button>
        </nav>
      </header>
      <main className="page"><Outlet /></main>
    </>
  );
}

export default function App() {
  const { user } = useAuth();
  const home = user ? '/dashboard' : '/login';
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={home} replace /> : <Login />} />
      <Route element={<Shell />}>
        <Route path="/dashboard" element={<Dashboard />} />
      </Route>
      <Route element={<Shell role="student" />}>
        <Route path="/book" element={<Book />} />
        <Route path="/my-bookings" element={<MyBookings />} />
      </Route>
      <Route element={<Shell role="admin" />}>
        <Route path="/admin/approvals" element={<Approvals />} />
        <Route path="/admin/block" element={<BlockLab />} />
        <Route path="/admin/labs" element={<AdminLabs />} />
        <Route path="/admin/admins" element={<Admins />} />
      </Route>
      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  );
}
