/**
 * IndexedDB Service for OffSet Offline Payments.
 * Stores pending offline transactions in PENDING_SYNC state
 * and maintains the cached offline wallet ledger.
 */

export interface OfflineTransaction {
  id: string;
  senderVpa: string;
  receiverVpa: string;
  amount: number;
  pinHash: string;
  nonce: string;
  signedAt: number;
  status: 'PENDING_SYNC' | 'SETTLED' | 'FAILED';
  createdAt: string;
  meshHops?: number;
}

export interface LocalWalletState {
  owner: string;
  balance: number;
  transactionLimit: number;
  dailyLimit: number;
  dailyUsed: number;
  walletVersion: number;
  lastUpdatedAt: string;
}

const DB_NAME = 'OffSetDB';
const DB_VERSION = 1;
const STORE_PENDING_TX = 'pending_transactions';
const STORE_LOCAL_WALLET = 'local_wallet';

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
      const db = (event.target as IDBOpenDBRequest).result;

      if (!db.objectStoreNames.contains(STORE_PENDING_TX)) {
        db.createObjectStore(STORE_PENDING_TX, { keyPath: 'id' });
      }

      if (!db.objectStoreNames.contains(STORE_LOCAL_WALLET)) {
        db.createObjectStore(STORE_LOCAL_WALLET, { keyPath: 'owner' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export const IndexedDbService = {
  // --- Pending Transactions ---

  async savePendingTransaction(tx: OfflineTransaction): Promise<void> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_PENDING_TX], 'readwrite');
      const store = transaction.objectStore(STORE_PENDING_TX);
      const req = store.put(tx);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },

  async getPendingTransactions(): Promise<OfflineTransaction[]> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_PENDING_TX], 'readonly');
      const store = transaction.objectStore(STORE_PENDING_TX);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  },

  async removePendingTransaction(id: string): Promise<void> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_PENDING_TX], 'readwrite');
      const store = transaction.objectStore(STORE_PENDING_TX);
      const req = store.delete(id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },

  // --- Local Offline Wallet ---

  async saveLocalWallet(wallet: LocalWalletState): Promise<void> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_LOCAL_WALLET], 'readwrite');
      const store = transaction.objectStore(STORE_LOCAL_WALLET);
      const req = store.put(wallet);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },

  async getLocalWallet(owner: string): Promise<LocalWalletState | null> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_LOCAL_WALLET], 'readonly');
      const store = transaction.objectStore(STORE_LOCAL_WALLET);
      const req = store.get(owner);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  },

  async deductOfflineBalance(owner: string, amount: number): Promise<LocalWalletState> {
    const current = await this.getLocalWallet(owner);
    if (!current) {
      throw new Error('Local offline wallet not initialized. Please connect online once to fund.');
    }

    if (current.balance < amount) {
      throw new Error(`Insufficient offline balance: ₹${current.balance.toFixed(2)} available, tried to send ₹${amount.toFixed(2)}`);
    }

    if (amount > current.transactionLimit) {
      throw new Error(`Amount ₹${amount.toFixed(2)} exceeds per-transaction limit of ₹${current.transactionLimit.toFixed(2)}`);
    }

    if (current.dailyUsed + amount > current.dailyLimit) {
      const remaining = current.dailyLimit - current.dailyUsed;
      throw new Error(`Amount exceeds daily limit. Remaining allowance today: ₹${remaining.toFixed(2)}`);
    }

    const updated: LocalWalletState = {
      ...current,
      balance: current.balance - amount,
      dailyUsed: current.dailyUsed + amount,
      walletVersion: current.walletVersion + 1,
      lastUpdatedAt: new Date().toISOString(),
    };

    await this.saveLocalWallet(updated);
    return updated;
  }
};
