import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from './api.js';

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user')); } catch { return null; }
  });

  const save = (res) => {
    localStorage.setItem('token', res.access_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  };

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    navigate('/login');
  }, [navigate]);

  useEffect(() => {
    const onExpired = () => logout();
    window.addEventListener('auth-expired', onExpired);
    return () => window.removeEventListener('auth-expired', onExpired);
  }, [logout]);

  const login = async (email, password) =>
    save(await api('/auth/login', { method: 'POST', body: { email, password } }));
  const register = async (form) =>
    save(await api('/auth/register', { method: 'POST', body: form }));

  return <AuthCtx.Provider value={{ user, login, register, logout }}>{children}</AuthCtx.Provider>;
}
