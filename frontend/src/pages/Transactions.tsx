import React, { useEffect, useState } from 'react';
import { TransactionService } from '../services/api';
import { IndexedDbService, OfflineTransaction } from '../services/indexedDb';
import { useNetwork } from '../context/NetworkContext';
import { 
  ArrowLeftRight, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  UploadCloud, 
  WifiOff, 
  Radio 
} from 'lucide-react';

export const Transactions: React.FC = () => {
  const { isOnline } = useNetwork();
  const [remoteTransactions, setRemoteTransactions] = useState<any[]>([]);
  const [pendingTransactions, setPendingTransactions] = useState<OfflineTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadAllTransactions = async () => {
    setLoading(true);
    setSyncMessage(null);
    try {
      // 1. Fetch local offline IndexedDB pending transactions
      const localPending = await IndexedDbService.getPendingTransactions();
      setPendingTransactions(localPending);

      // 2. Fetch server settled transactions if online
      if (isOnline) {
        try {
          const remote = await TransactionService.list();
          setRemoteTransactions(remote);
        } catch (e) {
          console.warn('Backend unavailable, showing offline store:', e);
        }
      }
    } catch (err) {
      console.error('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllTransactions();
  }, [isOnline]);

  const handleSimulateSync = async () => {
    if (pendingTransactions.length === 0) return;
    setSyncing(true);
    setSyncMessage(null);

    try {
      // Simulate network sync to backend
      for (const tx of pendingTransactions) {
        if (tx.status === 'PENDING_SYNC') {
          // In full sync, this hits /api/bridge/ingest or settlement
          // For now, update status to SETTLED in IndexedDB
          await IndexedDbService.savePendingTransaction({
            ...tx,
            status: 'SETTLED',
            meshHops: (tx.meshHops || 0) + 1,
          });
        }
      }

      setSyncMessage(`Successfully synchronized ${pendingTransactions.length} offline payment(s) to ledger!`);
      await loadAllTransactions();
    } catch (e: any) {
      setSyncMessage(`Sync failed: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const totalPending = pendingTransactions.filter(t => t.status === 'PENDING_SYNC').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800 }}>Activity & Ledger</h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            IndexedDB offline store & settled transactions
          </div>
        </div>

        <button
          onClick={loadAllTransactions}
          style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', padding: '6px' }}
          title="Refresh"
        >
          <RefreshCw size={18} className={loading ? 'spinner' : ''} />
        </button>
      </div>

      {/* Sync Status Banner */}
      {totalPending > 0 && (
        <div className="card" style={{
          background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(30, 27, 75, 0.6) 100%)',
          border: '1px solid rgba(245, 158, 11, 0.35)',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} color="#fbbf24" />
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#fef08a' }}>
                {totalPending} Offline Payment(s) in PENDING_SYNC
              </span>
            </div>
            <span className="badge badge-warning">Local Store</span>
          </div>

          <p style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: 1.3 }}>
            Stored locally in IndexedDB with cryptographic nonces. Ready to hop via Bluetooth mesh or upload when network is detected.
          </p>

          <button
            onClick={handleSimulateSync}
            disabled={syncing}
            className="btn btn-primary"
            style={{ minHeight: '38px', padding: '8px 14px', fontSize: '13px', alignSelf: 'flex-start' }}
          >
            <UploadCloud size={16} />
            <span>{syncing ? 'Synchronizing...' : 'Upload & Sync Now'}</span>
          </button>
        </div>
      )}

      {syncMessage && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          borderRadius: '12px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#6ee7b7',
          fontSize: '13px'
        }}>
          <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
          <span>{syncMessage}</span>
        </div>
      )}

      {/* Section 1: Local IndexedDB Transactions */}
      {pendingTransactions.length > 0 && (
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: '8px' }}>
            IndexedDB Offline Store ({pendingTransactions.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {pendingTransactions.map((tx) => (
              <div key={tx.id} className="card" style={{ padding: '14px 16px', borderLeft: tx.status === 'PENDING_SYNC' ? '4px solid #f59e0b' : '4px solid #10b981' }}>
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
                      ₹{tx.amount.toFixed(2)}
                    </div>
                    <span className={`badge ${tx.status === 'PENDING_SYNC' ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                      {tx.status === 'PENDING_SYNC' ? <Clock size={10} /> : <CheckCircle2 size={10} />}
                      <span>{tx.status}</span>
                    </span>
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

      {/* Section 2: Settled Server Ledger Transactions */}
      <div>
        <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: '8px' }}>
          Server Ledger Transactions ({remoteTransactions.length})
        </div>

        {remoteTransactions.length === 0 && pendingTransactions.length === 0 && !loading ? (
          <div className="card" style={{ textAlign: 'center', padding: '36px 20px', color: 'var(--text-muted)' }}>
            <ArrowLeftRight size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>No transactions recorded</div>
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              Make an offline or online payment to view activity here.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {remoteTransactions.map((tx, idx) => {
              const isSettled = tx.status === 'SETTLED';
              return (
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
                      <span className={`badge ${isSettled ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                        {isSettled ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
                        <span>{tx.status}</span>
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                    <span>Bridge: {tx.bridgeNodeId || 'online'} ({tx.hopCount || 0} hops)</span>
                    <span>{tx.settledAt ? new Date(tx.settledAt).toLocaleTimeString() : 'Settled'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
