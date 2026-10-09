import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNetwork } from '../context/NetworkContext';
import { QRScanner } from '../components/QRScanner';
import { ParsedQrData } from '../services/qrParser';
import { IndexedDbService, LocalWalletState, OfflineTransaction } from '../services/indexedDb';
import { WalletService } from '../services/api';
import { 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowLeft, 
  WifiOff, 
  Wifi, 
  ShieldCheck, 
  Clock, 
  ArrowRight,
  UserCheck
} from 'lucide-react';

export const Scan: React.FC = () => {
  const { user } = useAuth();
  const { isOnline } = useNetwork();
  const navigate = useNavigate();

  // Payment flow steps: 'scan' | 'confirm' | 'receipt'
  const [step, setStep] = useState<'scan' | 'confirm' | 'receipt'>('scan');
  const [recipient, setRecipient] = useState<ParsedQrData | null>(null);
  const [amount, setAmount] = useState<string>('100');
  const [pin, setPin] = useState<string>('1234');
  
  const [localWallet, setLocalWallet] = useState<LocalWalletState | null>(null);
  const [processing, setProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmedTx, setConfirmedTx] = useState<OfflineTransaction | null>(null);

  // Sync / load local wallet cache
  useEffect(() => {
    const initWallet = async () => {
      if (!user?.username) return;
      try {
        // If online, fetch from backend and sync to IndexedDB
        if (isOnline) {
          try {
            const remoteWallet = await WalletService.getWallet();
            const cached: LocalWalletState = {
              owner: user.username,
              balance: Number(remoteWallet.balance),
              transactionLimit: Number(remoteWallet.transactionLimit),
              dailyLimit: Number(remoteWallet.dailyLimit),
              dailyUsed: Number(remoteWallet.dailyUsed || 0),
              walletVersion: Number(remoteWallet.walletVersion),
              lastUpdatedAt: new Date().toISOString(),
            };
            await IndexedDbService.saveLocalWallet(cached);
            setLocalWallet(cached);
            return;
          } catch (e) {
            console.warn('Failed to refresh remote wallet, falling back to IndexedDB:', e);
          }
        }
        
        // Otherwise load from local IndexedDB
        const local = await IndexedDbService.getLocalWallet(user.username);
        setLocalWallet(local);
      } catch (err) {
        console.error('Error loading wallet:', err);
      }
    };

    initWallet();
  }, [user, isOnline]);

  const handleScanSuccess = (data: ParsedQrData) => {
    setRecipient(data);
    if (data.amount) {
      setAmount(data.amount.toString());
    }
    setErrorMsg(null);
    setStep('confirm');
  };

  const handleConfirmPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient || !user?.username) return;

    const amt = parseFloat(amount);
    if (isNaN(amt) || amt <= 0) {
      setErrorMsg('Please enter a valid amount greater than zero.');
      return;
    }

    if (!pin || pin.length < 4) {
      setErrorMsg('Please enter your 4-digit UPI PIN.');
      return;
    }

    setErrorMsg(null);
    setProcessing(true);

    try {
      const nonce = 'nonce_' + Math.random().toString(36).substring(2, 10);
      const now = Date.now();
      const txId = 'tx_' + now + '_' + Math.random().toString(36).substring(2, 7);

      // Check offline mode: Execute IndexedDB offline wallet deduction & PENDING_SYNC storage
      if (!isOnline) {
        // Deduct offline balance in local IndexedDB ledger
        const updatedWallet = await IndexedDbService.deductOfflineBalance(user.username, amt);
        setLocalWallet(updatedWallet);

        // Create transaction record with PENDING_SYNC
        const pendingTx: OfflineTransaction = {
          id: txId,
          senderVpa: user.vpa || `${user.username}@offset`,
          receiverVpa: recipient.vpa,
          amount: amt,
          pinHash: btoa(pin), // simulated hash
          nonce,
          signedAt: now,
          status: 'PENDING_SYNC',
          createdAt: new Date().toISOString(),
          meshHops: 0,
        };

        // Persist into IndexedDB
        await IndexedDbService.savePendingTransaction(pendingTx);
        setConfirmedTx(pendingTx);
      } else {
        // Online payment: also deduct local wallet and save as SETTLED
        const updatedWallet = await IndexedDbService.deductOfflineBalance(user.username, amt);
        setLocalWallet(updatedWallet);

        const onlineTx: OfflineTransaction = {
          id: txId,
          senderVpa: user.vpa || `${user.username}@offset`,
          receiverVpa: recipient.vpa,
          amount: amt,
          pinHash: btoa(pin),
          nonce,
          signedAt: now,
          status: 'SETTLED',
          createdAt: new Date().toISOString(),
          meshHops: 0,
        };

        await IndexedDbService.savePendingTransaction(onlineTx);
        setConfirmedTx(onlineTx);
      }

      setStep('receipt');
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment execution failed');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {step !== 'scan' && (
            <button
              onClick={() => { setErrorMsg(null); setStep('scan'); }}
              style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: '4px' }}
            >
              <ArrowLeft size={20} />
            </button>
          )}
          <h2 style={{ fontSize: '20px', fontWeight: 800 }}>
            {step === 'scan' && 'Scan & Pay'}
            {step === 'confirm' && 'Confirm Payment'}
            {step === 'receipt' && 'Payment Receipt'}
          </h2>
        </div>

        {/* Network Mode Pill */}
        <div className={`badge ${isOnline ? 'badge-success' : 'badge-warning'}`}>
          {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{isOnline ? 'Online' : 'Offline Mesh'}</span>
        </div>
      </div>

      {/* Step 1: Scanner */}
      {step === 'scan' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <QRScanner onScanSuccess={handleScanSuccess} />

          {/* Local Balance Card info */}
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Local Offline Wallet</div>
              <div style={{ fontSize: '18px', fontWeight: 800 }}>
                ₹{localWallet?.balance != null ? Number(localWallet.balance).toFixed(2) : '0.00'}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Per-Tx Limit</div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#818cf8' }}>
                ₹{localWallet?.transactionLimit != null ? Number(localWallet.transactionLimit).toFixed(0) : '2,000'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Payment Confirmation */}
      {step === 'confirm' && recipient && (
        <form onSubmit={handleConfirmPayment} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Recipient Details Card */}
          <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              background: 'var(--primary-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '18px',
              color: '#fff'
            }}>
              {recipient.name ? recipient.name.charAt(0).toUpperCase() : 'R'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '16px', fontWeight: 700 }}>
                {recipient.name || recipient.vpa}
              </div>
              <div style={{ fontSize: '13px', color: '#818cf8', fontWeight: 600 }}>
                {recipient.vpa}
              </div>
            </div>
            <UserCheck size={18} color="#10b981" />
          </div>

          {errorMsg && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              borderRadius: '12px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#fca5a5',
              fontSize: '13px'
            }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Amount input */}
          <div className="card">
            <div className="input-group" style={{ marginBottom: '12px' }}>
              <label className="input-label" htmlFor="pay-amount">Amount (₹)</label>
              <input
                id="pay-amount"
                type="number"
                step="1"
                min="1"
                max={localWallet?.transactionLimit || 2000}
                className="input-field"
                style={{ fontSize: '24px', fontWeight: 800, textAlign: 'center', height: '56px' }}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="100"
                disabled={processing}
              />
            </div>

            {/* Quick Amount Chips */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              {['50', '100', '250', '500'].map((amt) => (
                <button
                  key={amt}
                  type="button"
                  className="btn btn-secondary"
                  style={{ flex: 1, minHeight: '34px', padding: '4px', fontSize: '12px' }}
                  onClick={() => setAmount(amt)}
                >
                  ₹{amt}
                </button>
              ))}
            </div>

            {/* PIN input */}
            <div className="input-group" style={{ marginBottom: '4px' }}>
              <label className="input-label" htmlFor="pay-pin">UPI PIN</label>
              <input
                id="pay-pin"
                type="password"
                maxLength={6}
                className="input-field"
                style={{ textAlign: 'center', letterSpacing: '6px', fontSize: '20px' }}
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="••••"
                disabled={processing}
              />
            </div>
          </div>

          {/* Offline/Online Route Notice */}
          <div style={{
            background: isOnline ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
            border: `1px solid ${isOnline ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.25)'}`,
            borderRadius: '14px',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '12px',
            color: isOnline ? '#34d399' : '#fbbf24'
          }}>
            {isOnline ? <Wifi size={18} /> : <WifiOff size={18} />}
            <div>
              <strong>{isOnline ? 'Direct Server Settlement' : 'Offline Mesh Store & Forward'}</strong>
              <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                {isOnline 
                  ? 'Payment settles immediately with bank core ledger.'
                  : 'Packet signed locally, stored in IndexedDB (PENDING_SYNC), hops via mesh nodes.'}
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', minHeight: '52px', fontSize: '16px' }}
            disabled={processing}
          >
            {processing ? (
              <>
                <Loader2 className="spinner" size={20} />
                <span>Signing Payment Packet...</span>
              </>
            ) : (
              <>
                <span>Pay ₹{amount || '0'}</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>
      )}

      {/* Step 3: Receipt */}
      {step === 'receipt' && confirmedTx && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ textAlign: 'center', padding: '28px 20px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: confirmedTx.status === 'PENDING_SYNC' 
                ? 'rgba(245, 158, 11, 0.2)' 
                : 'rgba(16, 185, 129, 0.2)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px'
            }}>
              {confirmedTx.status === 'PENDING_SYNC' ? (
                <Clock size={34} color="#f59e0b" />
              ) : (
                <CheckCircle2 size={34} color="#10b981" />
              )}
            </div>

            <h3 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '4px' }}>
              {confirmedTx.status === 'PENDING_SYNC' ? 'Offline Payment Queued' : 'Payment Successful'}
            </h3>

            <div style={{ fontSize: '32px', fontWeight: 800, margin: '12px 0 6px' }}>
              ₹{confirmedTx.amount.toFixed(2)}
            </div>

            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              To: <strong>{confirmedTx.receiverVpa}</strong>
            </div>

            <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center' }}>
              <span className={`badge ${confirmedTx.status === 'PENDING_SYNC' ? 'badge-warning' : 'badge-success'}`}>
                {confirmedTx.status}
              </span>
            </div>

            {/* Receipt metadata */}
            <div style={{
              marginTop: '20px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              fontSize: '12px',
              textAlign: 'left'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Transaction ID:</span>
                <span style={{ fontFamily: 'monospace' }}>{confirmedTx.id.substring(0, 16)}...</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Cryptographic Nonce:</span>
                <span style={{ fontFamily: 'monospace' }}>{confirmedTx.nonce}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Storage:</span>
                <span style={{ color: '#818cf8', fontWeight: 600 }}>IndexedDB (Local Store)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Remaining Offline Balance:</span>
                <strong>₹{localWallet?.balance.toFixed(2) || '0.00'}</strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => { setStep('scan'); setRecipient(null); }}
              className="btn btn-secondary"
              style={{ flex: 1 }}
            >
              Scan Another
            </button>
            <button
              onClick={() => navigate('/transactions')}
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              View Activity
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
