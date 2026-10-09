import React from 'react';
import { Outlet } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Radio, Wifi, WifiOff } from 'lucide-react';
import { useNetwork } from '../context/NetworkContext';

export const MobileLayout: React.FC = () => {
  const { isOnline, toggleSimulatedOffline, isSimulatedOffline } = useNetwork();

  return (
    <div className="mobile-app-container">
      {/* Top Mobile Bar */}
      <header className="app-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '10px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(99, 102, 241, 0.4)'
          }}>
            <Radio size={18} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.3px', lineHeight: 1.1 }}>
              OffSet
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600 }}>
              Offline Mesh
            </div>
          </div>
        </div>

        {/* Network Detection Status Pill with Toggle */}
        <button
          onClick={toggleSimulatedOffline}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer'
          }}
          title={isSimulatedOffline ? "Click to disable offline simulation" : "Click to simulate offline mesh mode"}
        >
          <div className={`badge ${isOnline ? 'badge-success' : 'badge-warning'}`} style={{ gap: '6px' }}>
            {isOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
            <span>{isOnline ? 'ONLINE' : 'OFFLINE (MESH)'}</span>
          </div>
        </button>
      </header>

      {/* Main Screen Outlet */}
      <main className="app-content">
        <Outlet />
      </main>

      {/* Bottom Android Navigation */}
      <BottomNav />
    </div>
  );
};
