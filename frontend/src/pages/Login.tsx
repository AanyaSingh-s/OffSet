import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Radio, AlertCircle, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';

export const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. Please check credentials or backend status.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoFill = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setErrorMsg(null);
  };

  return (
    <div className="mobile-app-container" style={{ justifyContent: 'center', padding: '24px' }}>
      {/* OffSet Brand Header */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '20px',
          background: 'var(--primary-gradient)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 24px rgba(99, 102, 241, 0.45)',
          marginBottom: '16px'
        }}>
          <Radio size={34} color="#ffffff" />
        </div>
        <h1 style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.5px', marginBottom: '6px' }}>
          OffSet
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.4 }}>
          Offline-First Payment Mesh Prototype
        </p>
      </div>

      {/* Error State Banner */}
      {errorMsg && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: '14px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          color: '#fca5a5',
          fontSize: '13px'
        }}>
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Login Card */}
      <div className="card" style={{ background: 'var(--bg-surface)' }}>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label" htmlFor="username">
              Username or VPA
            </label>
            <input
              id="username"
              type="text"
              className="input-field"
              placeholder="e.g. alice"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoCapitalize="none"
              autoComplete="username"
              disabled={isSubmitting}
            />
          </div>

          <div className="input-group" style={{ marginBottom: '24px' }}>
            <label className="input-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input-field"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={isSubmitting}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="spinner" size={20} />
                <span>Authenticating...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {/* Demo Fast Login Pills */}
        <div style={{ marginTop: '24px', paddingTop: '18px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px', textAlign: 'center' }}>
            Quick fill demo accounts (password: password123):
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ minHeight: '36px', padding: '6px 14px', fontSize: '13px' }}
              onClick={() => handleDemoFill('alice', 'password123')}
            >
              Alice
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ minHeight: '36px', padding: '6px 14px', fontSize: '13px' }}
              onClick={() => handleDemoFill('bob', 'password123')}
            >
              Bob
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ minHeight: '36px', padding: '6px 14px', fontSize: '13px' }}
              onClick={() => handleDemoFill('carol', 'password123')}
            >
              Carol
            </button>
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
        <ShieldCheck size={14} color="#6366f1" />
        <span>End-to-End Hybrid Cryptography</span>
      </div>
    </div>
  );
};
