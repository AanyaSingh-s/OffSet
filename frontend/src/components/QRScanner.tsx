import React, { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Camera, Image, Keyboard, AlertCircle, RefreshCw } from 'lucide-react';
import { parseQrPayload, ParsedQrData } from '../services/qrParser';

interface QRScannerProps {
  onScanSuccess: (data: ParsedQrData) => void;
}

export const QRScanner: React.FC<QRScannerProps> = ({ onScanSuccess }) => {
  const [activeTab, setActiveTab] = useState<'camera' | 'manual' | 'upload'>('camera');
  const [manualVpa, setManualVpa] = useState('');
  const [manualName, setManualName] = useState('');
  const [scannerError, setScannerError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const html5QrCodeRef = useRef<Html5Qrcode | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const startScanner = async () => {
    setScannerError(null);
    try {
      if (!html5QrCodeRef.current) {
        html5QrCodeRef.current = new Html5Qrcode('qr-reader-container');
      }

      await html5QrCodeRef.current.start(
        { facingMode: 'environment' },
        {
          fps: 10,
          qrbox: { width: 220, height: 220 },
        },
        (decodedText) => {
          const parsed = parseQrPayload(decodedText);
          if (parsed) {
            stopScanner();
            onScanSuccess(parsed);
          } else {
            setScannerError(`Unsupported QR code: ${decodedText}`);
          }
        },
        () => {
          // ignore scan frame errors
        }
      );
      setIsScanning(true);
    } catch (err: any) {
      console.warn('Camera initiation failed:', err);
      setScannerError('Camera unavailable or permission denied. Use Manual Entry or Image Upload.');
      setIsScanning(false);
    }
  };

  const stopScanner = async () => {
    if (html5QrCodeRef.current && isScanning) {
      try {
        await html5QrCodeRef.current.stop();
        html5QrCodeRef.current.clear();
      } catch (e) {
        console.warn('Error stopping scanner:', e);
      }
      setIsScanning(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'camera') {
      startScanner();
    } else {
      stopScanner();
    }

    return () => {
      stopScanner();
    };
  }, [activeTab]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const qrScanner = new Html5Qrcode('qr-reader-temp');
      const decoded = await qrScanner.scanFile(file, true);
      const parsed = parseQrPayload(decoded);
      if (parsed) {
        onScanSuccess(parsed);
      } else {
        setScannerError(`Recognized text but not a valid UPI QR: ${decoded}`);
      }
      qrScanner.clear();
    } catch (err: any) {
      setScannerError('Could not decode QR code from the uploaded image.');
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualVpa.trim()) {
      setScannerError('Please enter a recipient VPA (e.g. bob@demo)');
      return;
    }
    const parsed = parseQrPayload(manualVpa.trim());
    if (parsed) {
      onScanSuccess({
        ...parsed,
        name: manualName.trim() || parsed.name,
      });
    } else {
      setScannerError('Invalid UPI VPA format. Must contain "@" (e.g. bob@demo)');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      {/* Tabs */}
      <div style={{
        display: 'flex',
        background: 'var(--bg-surface)',
        padding: '4px',
        borderRadius: '14px',
        border: '1px solid var(--border-subtle)',
        gap: '4px'
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('camera')}
          style={{
            flex: 1,
            minHeight: '36px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === 'camera' ? 'var(--primary-gradient)' : 'transparent',
            color: activeTab === 'camera' ? '#fff' : 'var(--text-secondary)',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            cursor: 'pointer'
          }}
        >
          <Camera size={14} />
          <span>Camera</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('manual')}
          style={{
            flex: 1,
            minHeight: '36px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === 'manual' ? 'var(--primary-gradient)' : 'transparent',
            color: activeTab === 'manual' ? '#fff' : 'var(--text-secondary)',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            cursor: 'pointer'
          }}
        >
          <Keyboard size={14} />
          <span>Manual</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('upload');
            fileInputRef.current?.click();
          }}
          style={{
            flex: 1,
            minHeight: '36px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === 'upload' ? 'var(--primary-gradient)' : 'transparent',
            color: activeTab === 'upload' ? '#fff' : 'var(--text-secondary)',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            cursor: 'pointer'
          }}
        >
          <Image size={14} />
          <span>Gallery</span>
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileUpload}
      />
      <div id="qr-reader-temp" style={{ display: 'none' }}></div>

      {scannerError && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: '12px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#fca5a5',
          fontSize: '12px'
        }}>
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{scannerError}</span>
        </div>
      )}

      {/* Tab: Camera */}
      {activeTab === 'camera' && (
        <div style={{ position: 'relative', width: '100%', borderRadius: '20px', overflow: 'hidden', background: '#000', minHeight: '260px' }}>
          <div id="qr-reader-container" style={{ width: '100%' }}></div>
          {!isScanning && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '20px',
              textAlign: 'center'
            }}>
              <Camera size={36} color="#818cf8" />
              <div style={{ fontSize: '13px', color: '#cbd5e1' }}>Point camera at any UPI QR code</div>
              <button
                type="button"
                onClick={startScanner}
                className="btn btn-secondary"
                style={{ minHeight: '36px', padding: '6px 14px', fontSize: '12px' }}
              >
                <RefreshCw size={14} />
                <span>Retry Camera</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab: Manual VPA */}
      {activeTab === 'manual' && (
        <form onSubmit={handleManualSubmit} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="input-group" style={{ marginBottom: 0 }}>
            <label className="input-label" htmlFor="manual-vpa">Recipient VPA / UPI ID</label>
            <input
              id="manual-vpa"
              type="text"
              className="input-field"
              placeholder="e.g. bob@demo or carol@demo"
              value={manualVpa}
              onChange={(e) => setManualVpa(e.target.value)}
            />
          </div>

          <div className="input-group" style={{ marginBottom: 0 }}>
            <label className="input-label" htmlFor="manual-name">Recipient Name (Optional)</label>
            <input
              id="manual-name"
              type="text"
              className="input-field"
              placeholder="e.g. Bob"
              value={manualName}
              onChange={(e) => setManualName(e.target.value)}
            />
          </div>

          {/* Quick Demo Payees */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, minHeight: '32px', padding: '4px', fontSize: '11px' }}
              onClick={() => { setManualVpa('bob@demo'); setManualName('Bob'); }}
            >
              bob@demo
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, minHeight: '32px', padding: '4px', fontSize: '11px' }}
              onClick={() => { setManualVpa('alice@demo'); setManualName('Alice'); }}
            >
              alice@demo
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, minHeight: '32px', padding: '4px', fontSize: '11px' }}
              onClick={() => { setManualVpa('carol@demo'); setManualName('Carol'); }}
            >
              carol@demo
            </button>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '6px' }}>
            Proceed to Payment
          </button>
        </form>
      )}

      {/* Tab: Upload Gallery */}
      {activeTab === 'upload' && (
        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <Image size={36} color="#818cf8" style={{ margin: '0 auto 12px' }} />
          <div style={{ fontSize: '14px', fontWeight: 600 }}>Select QR Image from Gallery</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '6px 0 16px' }}>
            Supports screenshots and photo captures of standard UPI QR codes
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            style={{ width: '100%' }}
          >
            Browse Files
          </button>
        </div>
      )}
    </div>
  );
};
