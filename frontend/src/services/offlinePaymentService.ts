/**
 * Day 6: OffSet Offline Payment Service
 * Enforces all 6 offline validations and executes local offline payments.
 * Saves transactions directly to offsetDB with status PENDING_SYNC.
 */

import {
  getWallet,
  deductWalletBalance,
  saveTransaction,
  OffSetTransaction,
  LocalWallet,
} from './indexedDb';

export interface PaymentExecutionResult {
  success: boolean;
  isOffline: boolean;
  transaction?: OffSetTransaction;
  updatedWallet?: LocalWallet;
  onlineResponse?: any;
}

export interface PaymentParams {
  user: { username: string; vpa?: string } | null;
  recipientVpa: string;
  recipientName?: string;
  amount: number;
  pin?: string;
  isOnline: boolean;
}

export const OfflinePaymentService = {
  /**
   * Validates recipient address format.
   */
  isValidRecipient(recipient: string): boolean {
    if (!recipient || !recipient.trim()) return false;
    const clean = recipient.trim();
    // Valid if standard VPA (e.g. user@demo) or name without invalid characters
    return clean.length >= 3 && (clean.includes('@') || /^[a-zA-Z0-9_.-]+$/.test(clean));
  },

  /**
   * Executes offline payment with the 6 strict validations.
   * Does NOT call the backend while offline.
   * Does NOT delete the transaction from IndexedDB.
   */
  async executeOfflinePayment(params: {
    user: { username: string; vpa?: string };
    recipientVpa: string;
    amount: number;
  }): Promise<{ transaction: OffSetTransaction; updatedWallet: LocalWallet }> {
    const { user, recipientVpa, amount } = params;

    // 1. Validation: authenticated user/session
    if (!user || !user.username) {
      throw new Error('Authentication required: user session not active');
    }

    // 2. Validation: valid recipient
    if (!this.isValidRecipient(recipientVpa)) {
      throw new Error('Invalid recipient: please provide a valid UPI ID / VPA (e.g. bob@demo)');
    }

    const cleanSender = user.vpa || `${user.username}@offset`;
    const cleanRecipient = recipientVpa.trim();

    if (cleanSender.toLowerCase() === cleanRecipient.toLowerCase() ||
        user.username.toLowerCase() === cleanRecipient.toLowerCase()) {
      throw new Error('Invalid recipient: cannot transfer funds to your own account');
    }

    // 3. Validation: positive amount
    if (typeof amount !== 'number' || isNaN(amount) || amount <= 0) {
      throw new Error('Invalid amount: payment amount must be greater than zero');
    }

    // Fetch local wallet from offsetDB
    const wallet = await getWallet(user.username);
    if (!wallet) {
      throw new Error('Local offline wallet not found. Please connect online once to fund and load your wallet.');
    }

    // 4. Validation: amount <= transaction limit
    if (amount > wallet.transactionLimit) {
      throw new Error(
        `Transaction limit exceeded: maximum allowed per payment is ₹${wallet.transactionLimit.toFixed(2)} (tried ₹${amount.toFixed(2)})`
      );
    }

    // 5. Validation: amount <= remaining daily limit
    const remainingDaily = wallet.dailyLimit - wallet.dailyUsed;
    if (amount > remainingDaily) {
      throw new Error(
        `Daily limit exceeded: remaining allowance today is ₹${remainingDaily.toFixed(2)} (tried ₹${amount.toFixed(2)})`
      );
    }

    // 6. Validation: amount <= offline wallet balance
    if (amount > wallet.balance) {
      throw new Error(
        `Insufficient offline balance: available balance is ₹${wallet.balance.toFixed(2)} (tried ₹${amount.toFixed(2)})`
      );
    }

    // --- All 6 validations passed ---

    // Step 1: Generate unique transactionId
    const transactionId = `tx_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    // Step 2: Generate unique nonce
    const nonce = `nonce_${Math.random().toString(36).substring(2, 12)}`;

    // Step 3: Create timestamp
    const createdAt = new Date().toISOString();

    // Step 4: Deduct amount from local wallet
    const updatedWallet = await deductWalletBalance(user.username, amount);

    // Step 5: Create transaction
    const transaction: OffSetTransaction = {
      transactionId,
      sender: cleanSender,
      receiver: cleanRecipient,
      amount: parseFloat(amount.toFixed(2)),
      nonce,
      createdAt,
      status: 'PENDING_SYNC',
      syncAttempts: 0,
      lastSyncAttempt: null,
    };

    // Step 6: Save transaction to IndexedDB
    await saveTransaction(transaction);

    return { transaction, updatedWallet };
  },

  /**
   * Main payment router that checks network status.
   * If ONLINE: uses existing backend API and does not create an offline transaction.
   * If OFFLINE: continues locally via executeOfflinePayment.
   */
  async processPayment(params: PaymentParams): Promise<PaymentExecutionResult> {
    const { user, recipientVpa, amount, pin, isOnline } = params;

    if (!user || !user.username) {
      throw new Error('Authentication required: user session not found');
    }

    if (!isOnline) {
      // OFFLINE: Continue locally
      const { transaction, updatedWallet } = await this.executeOfflinePayment({
        user,
        recipientVpa,
        amount,
      });

      return {
        success: true,
        isOffline: true,
        transaction,
        updatedWallet,
      };
    } else {
      // ONLINE: Use existing online payment API
      const senderVpa = user.vpa || `${user.username}@offset`;
      const response = await fetch('/api/demo/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          senderVpa,
          receiverVpa: recipientVpa,
          amount,
          pin: pin || '1234',
          ttl: 5,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.message || 'Online payment failed');
      }

      const data = await response.json();
      return {
        success: true,
        isOffline: false,
        onlineResponse: data,
      };
    }
  },
};
