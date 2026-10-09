import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { LogOut, ShieldCheck, Cpu, Smartphone } from 'lucide-react';

export const Profile: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Profile & Settings</h2>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>OffSet node credentials and device preferences</div>
      </div>

      {/* User Card */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          width: '54px',
          height: '54px',
          borderRadius: '50%',
          background: 'var(--primary-gradient)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '22px',
          fontWeight: 800,
          color: '#ffffff'
        }}>
          {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
        </div>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 700 }}>
            {user?.username ? user.username.toUpperCase() : 'AUTHENTICATED USER'}
          </div>
          <div style={{ fontSize: '13px', color: '#818cf8', fontWeight: 600 }}>
            {user?.vpa || 'Not configured'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Bearer JWT Authentication Active
          </div>
        </div>
      </div>

      {/* Prototype Device Status */}
      <div className="card">
        <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>Device Configuration</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
            <Smartphone size={16} color="#94a3b8" />
            <span style={{ color: 'var(--text-secondary)', flex: 1 }}>Client Platform</span>
            <strong>Capacitor / Android Ready</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
            <Cpu size={16} color="#94a3b8" />
            <span style={{ color: 'var(--text-secondary)', flex: 1 }}>Crypto Engine</span>
            <strong>RSA-2048 + AES-GCM</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
            <ShieldCheck size={16} color="#10b981" />
            <span style={{ color: 'var(--text-secondary)', flex: 1 }}>Replay Protection</span>
            <strong style={{ color: '#34d399' }}>Atomic Nonce</strong>
          </div>
        </div>
      </div>

      {/* Logout Action */}
      <button
        onClick={handleLogout}
        className="btn btn-danger"
        style={{ width: '100%', marginTop: '8px' }}
      >
        <LogOut size={18} />
        <span>Sign Out</span>
      </button>

      <div style={{ textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
        OffSet Research Prototype • Day 1-2 Mobile Foundation
      </div>
    </div>
  );
};
