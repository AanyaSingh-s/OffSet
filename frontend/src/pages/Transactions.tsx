import React, { useEffect, useState } from 'react';
import { TransactionService } from '../services/api';
import { 
  getTransactionHistory, 
  getPendingTransactions, 
  OffSetTransaction 
} from '../services/indexedDb';
import { useNetwork } from '../context/NetworkContext';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeftRight, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  ShieldAlert, 
  RotateCcw 
} from 'lucide-react';

export const Transactions: React.FC = () => {
  const { isOnline } = useNetwork();
  const { user } = useAuth();
  const [remoteTransactions, setRemoteTransactions] = useState<any[]>([]);
  const [localTransactions, setLocalTransactions] = useState<OffSetTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAllTransactions = async () => {
    setLoading(true);
    try {
      // 1. Fetch local offsetDB transactions
      const local = await getTransactionHistory();
      setLocalTransactions(local);

      // 2. Fetch server settled transactions if online
      if (isOnline) {
        try {
          const remote = await TransactionService.list();
          setRemoteTransactions(remote);
        } catch (e) {
          console.warn('Backend unavailable, showing offsetDB store:', e);
        }
      }
    } catch (err) {
      console.error('Failed to load transactions from offsetDB:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllTransactions();
  }, [isOnline, user]);

  const totalPending = localTransactions.filter((t) => t.status === 'PENDING_SYNC').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING_SYNC':
        return (
          <span className="badge badge-warning" style={{ fontSize: '10px', padding: '2px 8px' }}>
            <Clock size={10} />
            <span>PENDING SYNC</span>
          </span>
        );
      case 'SYNCING':
        return (
          <span className="badge badge-purple" style={{ fontSize: '10px', padding: '2px 8px' }}>
            <RotateCcw size={10} className="spinner" />
            <span>SYNCING</span>
          </span>
        );
      case 'SUCCESS':
      case 'SETTLED':
        return (
          <span className="badge badge-success" style={{ fontSize: '10px', padding: '2px 8px' }}>
            <CheckCircle2 size={10} />
            <span>SUCCESS</span>
          </span>
        );
      case 'FRAUD_FLAGGED':
        return (
          <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.4)', fontSize: '10px', padding: '2px 8px' }}>
            <ShieldAlert size={10} />
            <span>FRAUD FLAGGED</span>
          </span>
        );
      case 'FAILED':
      default:
        return (
          <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', fontSize: '10px', padding: '2px 8px' }}>
            <AlertTriangle size={10} />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Activity & Ledger</h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            offsetDB local store & server ledger
          </div>
        </div>

        <button
          onClick={loadAllTransactions}
          style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', padding: '6px' }}
          title="Refresh transactions"
        >
          <RefreshCw size={18} className={loading ? 'spinner' : ''} />
        </button>
      </div>

      {/* Pending Sync Alert Box */}
      {totalPending > 0 && (
        <div className="card" style={{
          background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(30, 27, 75, 0.6) 100%)',
          border: '1px solid rgba(245, 158, 11, 0.35)',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} color="#fbbf24" />
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#fef08a' }}>
                {totalPending} Offline Payment(s) Stored Locally
              </span>
            </div>
            <span className="badge badge-warning">offsetDB</span>
          </div>

          <p style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: 1.3 }}>
            Stored securely in IndexedDB with nonces. Kept in PENDING_SYNC state until future synchronization.
          </p>
        </div>
      )}

      {/* Section 1: Local IndexedDB Transactions */}
      {localTransactions.length > 0 && (
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: '8px' }}>
            Local offsetDB Transactions ({localTransactions.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {localTransactions.map((tx) => (
              <div 
                key={tx.transactionId} 
                className="card" 
                style={{ 
                  padding: '14px 16px', 
                  borderLeft: tx.status === 'PENDING_SYNC' ? '4px solid #f59e0b' : '4px solid #10b981' 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700 }}>
                      To: {tx.receiver}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      From: {tx.sender}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '16px', fontWeight: 800 }}>
                      ₹{tx.amount.toFixed(2)}
                    </div>
                    {getStatusBadge(tx.status)}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                  <span>Nonce: {tx.nonce}</span>
                  <span>{new Date(tx.createdAt).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 2: Server Ledger Transactions */}
      {remoteTransactions.length > 0 && (
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: '8px' }}>
            Server Settled Ledger ({remoteTransactions.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {remoteTransactions.map((tx, idx) => (
              <div key={tx.id || idx} className="card" style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 700 }}>
                      To: {tx.receiverVpa}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      From: {tx.senderVpa}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '16px', fontWeight: 800 }}>
                      ₹{tx.amount != null ? Number(tx.amount).toFixed(2) : '0.00'}
                    </div>
                    {getStatusBadge(tx.status)}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                  <span>Bridge: {tx.bridgeNodeId || 'online'} ({tx.hopCount || 0} hops)</span>
                  <span>{tx.settledAt ? new Date(tx.settledAt).toLocaleTimeString() : 'Settled'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {localTransactions.length === 0 && remoteTransactions.length === 0 && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-muted)' }}>
          <ArrowLeftRight size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>No transactions yet</div>
          <div style={{ fontSize: '12px', marginTop: '4px' }}>
            Perform an offline or online payment to record transactions in offsetDB.
          </div>
        </div>
      )}
    </div>
  );
};
