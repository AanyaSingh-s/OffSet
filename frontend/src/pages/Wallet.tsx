import React, { useEffect, useState } from 'react';
import { WalletService } from '../services/api';
import { Wallet as WalletIcon, CheckCircle2, AlertCircle, Loader2, ArrowDownCircle } from 'lucide-react';

export const Wallet: React.FC = () => {
  const [wallet, setWallet] = useState<any>(null);
  const [limits, setLimits] = useState<any>(null);
  const [, setLoading] = useState(true);
  
  // Funding state
  const [fundAmount, setFundAmount] = useState('500');
  const [funding, setFunding] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadWalletDetails = async () => {
    try {
      setLoading(true);
      const [walletData, limitsData] = await Promise.all([
        WalletService.getWallet(),
        WalletService.getLimits(),
      ]);
      setWallet(walletData);
      setLimits(limitsData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch wallet info');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWalletDetails();
  }, []);

  const handleFund = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountNum = parseFloat(fundAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setErrorMsg('Please enter a valid positive amount.');
      return;
    }

    setErrorMsg(null);
    setSuccessMsg(null);
    setFunding(true);

    try {
      const res = await WalletService.fund(amountNum);
      setSuccessMsg(`Funded ₹${amountNum.toFixed(2)} via Mock Gateway (${res.gatewayTransactionId})`);
      await loadWalletDetails();
    } catch (err: any) {
      setErrorMsg(err.message || 'Funding failed');
    } finally {
      setFunding(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '12px',
          background: 'rgba(99, 102, 241, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <WalletIcon size={20} color="#818cf8" />
        </div>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.3px' }}>Offline Wallet</h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Manage local offline balance and limits</div>
        </div>
      </div>

      {/* Balance Card */}
      <div className="card-gradient">
        <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.7)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: '8px' }}>
          Available Offline Balance
        </div>
        <div style={{ fontSize: '38px', fontWeight: 800, letterSpacing: '-0.5px', marginBottom: '14px' }}>
          ₹{wallet?.balance != null ? Number(wallet.balance).toFixed(2) : '0.00'}
        </div>
        <div style={{ fontSize: '11px', color: '#94a3b8' }}>
          Wallet Version {wallet?.walletVersion || 1} • Owner: {wallet?.owner || 'Authenticated User'}
        </div>
      </div>

      {/* Limits Overview */}
      <div className="card">
        <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px' }}>Enforced Safety Limits</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Per-Transaction Limit:</span>
            <strong>₹{limits?.transactionLimit != null ? Number(limits.transactionLimit).toFixed(2) : '2,000.00'}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Daily Maximum Limit:</span>
            <strong>₹{limits?.dailyLimit != null ? Number(limits.dailyLimit).toFixed(2) : '10,000.00'}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Daily Used / Spent:</span>
            <strong style={{ color: '#fbbf24' }}>₹{limits?.dailyUsed != null ? Number(limits.dailyUsed).toFixed(2) : '0.00'}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Remaining Today:</span>
            <strong style={{ color: '#34d399' }}>₹{limits?.dailyRemaining != null ? Number(limits.dailyRemaining).toFixed(2) : '10,000.00'}</strong>
          </div>
        </div>
      </div>

      {/* Funding Section */}
      <div className="card">
        <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '6px' }}>Mock Gateway Funding</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Load funds into your offline wallet for zero-network payments
        </p>

        {successMsg && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '12px',
            padding: '10px 14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#6ee7b7',
            fontSize: '13px'
          }}>
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {errorMsg && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '12px',
            padding: '10px 14px',
            marginBottom: '16px',
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

        <form onSubmit={handleFund}>
          <div className="input-group">
            <label className="input-label" htmlFor="fund-amount">Amount (₹)</label>
            <input
              id="fund-amount"
              type="number"
              step="1"
              min="1"
              max="2000"
              className="input-field"
              value={fundAmount}
              onChange={(e) => setFundAmount(e.target.value)}
              placeholder="e.g. 500"
              disabled={funding}
            />
          </div>

          {/* Quick amount shortcuts */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '18px' }}>
            {['200', '500', '1000', '2000'].map((amt) => (
              <button
                key={amt}
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1, minHeight: '36px', padding: '6px', fontSize: '13px' }}
                onClick={() => setFundAmount(amt)}
              >
                +₹{amt}
              </button>
            ))}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={funding}
          >
            {funding ? (
              <>
                <Loader2 className="spinner" size={18} />
                <span>Simulating Gateway...</span>
              </>
            ) : (
              <>
                <ArrowDownCircle size={18} />
                <span>Fund via Mock Gateway</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
