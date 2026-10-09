/**
 * QR Code Parser for UPI and OffSet Payloads.
 * Supports:
 *   1. Standard UPI URI: upi://pay?pa=receiver@bank&pn=Receiver%20Name&am=100&cu=INR
 *   2. JSON payloads: {"vpa":"bob@demo","name":"Bob","amount":100}
 *   3. Plain VPA strings: bob@demo
 */

export interface ParsedQrData {
  vpa: string;
  name?: string;
  amount?: number;
  note?: string;
}

export function parseQrPayload(raw: string): ParsedQrData | null {
  if (!raw || !raw.trim()) return null;
  const cleaned = raw.trim();

  // 1. Try standard UPI URI scheme (upi://pay?...)
  if (cleaned.toLowerCase().startsWith('upi://pay')) {
    try {
      const url = new URL(cleaned);
      const params = url.searchParams;
      const pa = params.get('pa');
      if (pa) {
        const pn = params.get('pn');
        const am = params.get('am');
        const tn = params.get('tn');
        return {
          vpa: pa.trim(),
          name: pn ? decodeURIComponent(pn) : undefined,
          amount: am ? parseFloat(am) : undefined,
          note: tn ? decodeURIComponent(tn) : undefined,
        };
      }
    } catch {
      // Fallback regex in case URL constructor fails on custom schemes
      const paMatch = cleaned.match(/[?&]pa=([^&]+)/i);
      if (paMatch) {
        const pa = decodeURIComponent(paMatch[1]);
        const pnMatch = cleaned.match(/[?&]pn=([^&]+)/i);
        const amMatch = cleaned.match(/[?&]am=([^&]+)/i);
        return {
          vpa: pa,
          name: pnMatch ? decodeURIComponent(pnMatch[1]) : undefined,
          amount: amMatch ? parseFloat(amMatch[1]) : undefined,
        };
      }
    }
  }

  // 2. Try JSON payload
  if (cleaned.startsWith('{') && cleaned.endsWith('}')) {
    try {
      const parsed = JSON.parse(cleaned);
      if (parsed.vpa || parsed.pa) {
        return {
          vpa: parsed.vpa || parsed.pa,
          name: parsed.name || parsed.pn,
          amount: parsed.amount || parsed.am ? Number(parsed.amount || parsed.am) : undefined,
          note: parsed.note || parsed.tn,
        };
      }
    } catch {
      // Ignore JSON error and proceed to VPA check
    }
  }

  // 3. Fallback: Check if it's a valid VPA pattern (e.g. user@bank)
  if (cleaned.includes('@') && !cleaned.includes(' ')) {
    return {
      vpa: cleaned,
      name: cleaned.split('@')[0],
    };
  }

  return null;
}
