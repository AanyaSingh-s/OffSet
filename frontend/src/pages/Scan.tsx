import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNetwork } from '../context/NetworkContext';
import { QRScanner } from '../components/QRScanner';
import { ParsedQrData } from '../services/qrParser';
import { getWallet, saveWallet, LocalWallet, OffSetTransaction } from '../services/indexedDb';
import { OfflinePaymentService, PaymentExecutionResult } from '../services/offlinePaymentService';
import { WalletService } from '../services/api';
import { 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowLeft, 
  WifiOff, 
  Wifi, 
  Clock, 
  ArrowRight,
  UserCheck,
  ShieldCheck
} from 'lucide-react';

export const Scan: React.FC = () => {
  const { user } = useAuth();
  const { isOnline } = useNetwork();
  const navigate = useNavigate();

  // Payment flow steps: 'scan' | 'confirm' | 'receipt'
  const [step, setStep] = useState<'scan' | 'confirm' | 'receipt'>('scan');
  const [recipient, setRecipient] = useState<ParsedQrData | null>(null);
  const [amount, setAmount] = useState<string>('500');
  const [pin, setPin] = useState<string>('1234');
  
  const [localWallet, setLocalWallet] = useState<LocalWallet | null>(null);
  const [processing, setProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [paymentResult, setPaymentResult] = useState<PaymentExecutionResult | null>(null);

  // Sync / load local wallet cache from offsetDB or backend
  const loadWallet = async () => {
    if (!user?.username) return;
    try {
      if (isOnline) {
        try {
          const remoteWallet = await WalletService.getWallet();
          const cached: LocalWallet = {
            owner: user.username,
            balance: Number(remoteWallet.balance),
            transactionLimit: Number(remoteWallet.transactionLimit),
            dailyLimit: Number(remoteWallet.dailyLimit),
            dailyUsed: Number(remoteWallet.dailyUsed || 0),
            walletVersion: Number(remoteWallet.walletVersion),
            lastUpdatedAt: new Date().toISOString(),
          };
          await saveWallet(cached);
          setLocalWallet(cached);
          return;
        } catch (e) {
          console.warn('Backend unavailable, loading local wallet from offsetDB:', e);
        }
      }

      // If offline or remote fetch failed, read directly from offsetDB
      const local = await getWallet(user.username);
      if (local) {
        setLocalWallet(local);
      } else {
        // Initialize default local wallet if not yet present
        const initial: LocalWallet = {
          owner: user.username,
          balance: 1000.0,
          transactionLimit: 2000.0,
          dailyLimit: 10000.0,
          dailyUsed: 0.0,
          walletVersion: 1,
          lastUpdatedAt: new Date().toISOString(),
        };
        await saveWallet(initial);
        setLocalWallet(initial);
      }
    } catch (err) {
      console.error('Error loading wallet from offsetDB:', err);
    }
  };

  useEffect(() => {
    loadWallet();
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

    setErrorMsg(null);
    setProcessing(true);

    try {
      const result = await OfflinePaymentService.processPayment({
        user: { username: user.username, vpa: user.vpa },
        recipientVpa: recipient.vpa,
        recipientName: recipient.name,
        amount: amt,
        pin,
        isOnline,
      });

      if (result.updatedWallet) {
        setLocalWallet(result.updatedWallet);
      }
      setPaymentResult(result);
      setStep('receipt');
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment failed');
    } finally {
      setProcessing(false);
    }
  };

  const tx: OffSetTransaction | undefined = paymentResult?.transaction;

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
          <span>{isOnline ? 'ONLINE' : 'OFFLINE (MESH)'}</span>
        </div>
      </div>

      {/* Step 1: Scanner */}
      {step === 'scan' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <QRScanner onScanSuccess={handleScanSuccess} />

          {/* Local Balance Card info */}
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>offsetDB Offline Balance</div>
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
                style={{ fontSize: '26px', fontWeight: 800, textAlign: 'center', height: '56px' }}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="500"
                disabled={processing}
              />
            </div>

            {/* Quick Amount Chips */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              {['100', '250', '500', '1000'].map((amt) => (
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
              <strong>{isOnline ? 'Online Server Settlement' : 'Offline Mode Active'}</strong>
              <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                {isOnline 
                  ? 'Connected to Spring Boot backend. Settles directly.'
                  : 'Zero connectivity. Payment is validated locally, balance is deducted in offsetDB, and transaction is stored in PENDING_SYNC.'}
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
                <span>Validating & Recording...</span>
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

      {/* Step 3: Exact Day 6 Receipt Display */}
      {step === 'receipt' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ textAlign: 'center', padding: '28px 20px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: paymentResult?.isOffline ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px'
            }}>
              {paymentResult?.isOffline ? (
                <Clock size={34} color="#f59e0b" />
              ) : (
                <CheckCircle2 size={34} color="#10b981" />
              )}
            </div>

            {/* Exact Required Display */}
            <h3 style={{ fontSize: '22px', fontWeight: 800, marginBottom: '6px' }}>
              {paymentResult?.isOffline ? 'Payment Recorded' : 'Online Payment Sent'}
            </h3>

            <div style={{ fontSize: '36px', fontWeight: 800, margin: '8px 0' }}>
              ₹{parseFloat(amount).toFixed(2)}
            </div>

            <div style={{ fontSize: '15px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              To: <strong style={{ color: '#fff' }}>{recipient?.name || recipient?.vpa || 'Bob'}</strong>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <span className={`badge ${paymentResult?.isOffline ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: '12px', padding: '4px 12px' }}>
                {paymentResult?.isOffline ? 'PENDING SYNC' : 'SETTLED ONLINE'}
              </span>
            </div>

            <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.4, maxWidth: '280px', margin: '0 auto 16px' }}>
              {paymentResult?.isOffline
                ? 'Offline transaction stored securely on this device.'
                : 'Payment submitted directly to Spring Boot backend.'}
            </p>

            {/* Transaction metadata */}
            {tx && (
              <div style={{
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
                  <span style={{ fontFamily: 'monospace' }}>{tx.transactionId.substring(0, 16)}...</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Nonce:</span>
                  <span style={{ fontFamily: 'monospace' }}>{tx.nonce}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Storage Engine:</span>
                  <span style={{ color: '#818cf8', fontWeight: 600 }}>offsetDB (IndexedDB)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>New Offline Balance:</span>
                  <strong>₹{localWallet?.balance.toFixed(2) || '0.00'}</strong>
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => { setStep('scan'); setRecipient(null); setPaymentResult(null); }}
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
