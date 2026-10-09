import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { WalletService } from '../services/api';
import { Link } from 'react-router-dom';
import { 
  QrCode, 
  ArrowUpRight, 
  ArrowDownLeft, 
  RefreshCw, 
  WifiOff, 
  ShieldCheck, 
  Sparkles 
} from 'lucide-react';

export const Home: React.FC = () => {
  const { user } = useAuth();
  const [wallet, setWallet] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchWalletData = async () => {
    try {
      setLoading(true);
      const data = await WalletService.getWallet();
      setWallet(data);
    } catch (err) {
      console.error('Failed to load wallet:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWalletData();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Greeting Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Welcome back,
          </div>
          <h2 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.3px' }}>
            {user?.username ? user.username.toUpperCase() : 'USER'}
          </h2>
          <div style={{ fontSize: '12px', color: '#818cf8', fontWeight: 600 }}>
            {user?.vpa}
          </div>
        </div>

        <div className="badge badge-purple" style={{ padding: '6px 12px' }}>
          <Sparkles size={14} />
          <span>v{wallet?.walletVersion || '1.0'}</span>
        </div>
      </div>

      {/* Main Balance Card */}
      <div className="card-gradient">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'rgba(255, 255, 255, 0.7)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
            Offline Wallet Balance
          </span>
          <button 
            onClick={fetchWalletData}
            style={{ background: 'none', border: 'none', color: '#a5b4fc', cursor: 'pointer', padding: '4px' }}
            title="Refresh balance"
          >
            <RefreshCw size={16} className={loading ? 'spinner' : ''} />
          </button>
        </div>

        <div style={{ fontSize: '36px', fontWeight: 800, letterSpacing: '-0.5px', marginBottom: '8px' }}>
          ₹{wallet?.balance != null ? Number(wallet.balance).toFixed(2) : '0.00'}
        </div>

        <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#cbd5e1' }}>
          <div>
            Tx Limit: <strong style={{ color: '#fff' }}>₹{wallet?.transactionLimit != null ? Number(wallet.transactionLimit).toFixed(0) : '2,000'}</strong>
          </div>
          <div>
            Daily Limit: <strong style={{ color: '#fff' }}>₹{wallet?.dailyLimit != null ? Number(wallet.dailyLimit).toFixed(0) : '10,000'}</strong>
          </div>
        </div>
      </div>

      {/* Quick Action Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        <Link 
          to="/scan" 
          className="btn btn-secondary" 
          style={{ flexDirection: 'column', height: '80px', padding: '10px 4px', fontSize: '12px', gap: '8px' }}
        >
          <div style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '8px', borderRadius: '12px' }}>
            <QrCode size={20} color="#818cf8" />
          </div>
          <span>Scan & Pay</span>
        </Link>

        <Link 
          to="/wallet" 
          className="btn btn-secondary" 
          style={{ flexDirection: 'column', height: '80px', padding: '10px 4px', fontSize: '12px', gap: '8px' }}
        >
          <div style={{ background: 'rgba(16, 185, 129, 0.2)', padding: '8px', borderRadius: '12px' }}>
            <ArrowDownLeft size={20} color="#34d399" />
          </div>
          <span>Fund Wallet</span>
        </Link>

        <Link 
          to="/transactions" 
          className="btn btn-secondary" 
          style={{ flexDirection: 'column', height: '80px', padding: '10px 4px', fontSize: '12px', gap: '8px' }}
        >
          <div style={{ background: 'rgba(245, 158, 11, 0.2)', padding: '8px', borderRadius: '12px' }}>
            <ArrowUpRight size={20} color="#fbbf24" />
          </div>
          <span>Activity</span>
        </Link>
      </div>

      {/* Offline Status Card */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '14px',
          background: 'rgba(16, 185, 129, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <WifiOff size={22} color="#10b981" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '14px', fontWeight: 700 }}>Mesh Network Ready</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Transactions sign locally and hop via mesh to bridge nodes
          </div>
        </div>
        <div className="badge badge-success">0 Sync</div>
      </div>

      {/* Security Note */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '14px',
        padding: '12px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '12px',
        color: 'var(--text-muted)'
      }}>
        <ShieldCheck size={16} color="#6366f1" />
        <span>Hybrid RSA-2048 + AES-GCM replay-protected ledger</span>
      </div>
    </div>
  );
};
