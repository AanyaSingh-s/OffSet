/**
 * Day 5: OffSet IndexedDB Storage Layer
 * Database: offsetDB
 * Stores:
 *   - wallet (stores local offline wallet balances and limits)
 *   - transactions (stores offline payments in PENDING_SYNC, SYNCING, SUCCESS, FAILED, FRAUD_FLAGGED)
 *
 * All functions are decoupled from React UI components.
 */

export type TransactionStatus =
  | 'PENDING_SYNC'
  | 'SYNCING'
  | 'SUCCESS'
  | 'FAILED'
  | 'FRAUD_FLAGGED';

export interface OffSetTransaction {
  transactionId: string;
  sender: string;
  receiver: string;
  amount: number;
  nonce: string;
  createdAt: string;
  status: TransactionStatus;
  syncAttempts: number;
  lastSyncAttempt: string | null;
}

export interface LocalWallet {
  owner: string;
  balance: number;
  transactionLimit: number;
  dailyLimit: number;
  dailyUsed: number;
  walletVersion: number;
  lastUpdatedAt: string;
}

export const DB_NAME = 'offsetDB';
export const DB_VERSION = 1;
export const STORE_WALLET = 'wallet';
export const STORE_TRANSACTIONS = 'transactions';

/**
 * Initializes and returns the offsetDB IndexedDB database instance.
 */
export function initDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    // Allows IndexedDB in browser or fake-indexeddb in test environments
    const idb = typeof indexedDB !== 'undefined' ? indexedDB : (globalThis as any).indexedDB;
    if (!idb) {
      return reject(new Error('IndexedDB is not supported in this environment'));
    }

    const request = idb.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // 1. Transactions Store
      if (!db.objectStoreNames.contains(STORE_TRANSACTIONS)) {
        const txStore = db.createObjectStore(STORE_TRANSACTIONS, { keyPath: 'transactionId' });
        txStore.createIndex('status', 'status', { unique: false });
        txStore.createIndex('sender', 'sender', { unique: false });
        txStore.createIndex('createdAt', 'createdAt', { unique: false });
      }

      // 2. Wallet Store
      if (!db.objectStoreNames.contains(STORE_WALLET)) {
        db.createObjectStore(STORE_WALLET, { keyPath: 'owner' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Saves or updates a transaction in offsetDB.
 */
export async function saveTransaction(tx: OffSetTransaction): Promise<void> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_TRANSACTIONS], 'readwrite');
    const store = transaction.objectStore(STORE_TRANSACTIONS);
    const req = store.put(tx);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieves a single transaction by its transactionId.
 */
export async function getTransaction(transactionId: string): Promise<OffSetTransaction | null> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_TRANSACTIONS], 'readonly');
    const store = transaction.objectStore(STORE_TRANSACTIONS);
    const req = store.get(transactionId);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieves all transactions currently in PENDING_SYNC status.
 */
export async function getPendingTransactions(): Promise<OffSetTransaction[]> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_TRANSACTIONS], 'readonly');
    const store = transaction.objectStore(STORE_TRANSACTIONS);
    const req = store.getAll();
    req.onsuccess = () => {
      const all: OffSetTransaction[] = req.result || [];
      const pending = all.filter((tx) => tx.status === 'PENDING_SYNC');
      resolve(pending);
    };
    req.onerror = () => reject(req.error);
  });
}

/**
 * Updates specific fields of an existing transaction.
 */
export async function updateTransaction(
  transactionId: string,
  updates: Partial<OffSetTransaction>
): Promise<void> {
  const existing = await getTransaction(transactionId);
  if (!existing) {
    throw new Error(`Transaction ${transactionId} not found`);
  }

  const updated: OffSetTransaction = {
    ...existing,
    ...updates,
    transactionId: existing.transactionId, // immutable key
  };

  await saveTransaction(updated);
}

/**
 * Deletes a transaction from offsetDB by transactionId.
 */
export async function deleteTransaction(transactionId: string): Promise<void> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_TRANSACTIONS], 'readwrite');
    const store = transaction.objectStore(STORE_TRANSACTIONS);
    const req = store.delete(transactionId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieves all transactions sorted by createdAt descending.
 */
export async function getTransactionHistory(userVpaOrSender?: string): Promise<OffSetTransaction[]> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_TRANSACTIONS], 'readonly');
    const store = transaction.objectStore(STORE_TRANSACTIONS);
    const req = store.getAll();
    req.onsuccess = () => {
      let results: OffSetTransaction[] = req.result || [];
      if (userVpaOrSender) {
        results = results.filter(
          (tx) => tx.sender === userVpaOrSender || tx.receiver === userVpaOrSender
        );
      }
      results.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      resolve(results);
    };
    req.onerror = () => reject(req.error);
  });
}

// -------------------------------------------------------------------------
// Reusable Local Wallet Storage Functions
// -------------------------------------------------------------------------

/**
 * Saves or updates a local wallet in offsetDB.
 */
export async function saveWallet(wallet: LocalWallet): Promise<void> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_WALLET], 'readwrite');
    const store = transaction.objectStore(STORE_WALLET);
    const req = store.put(wallet);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieves a local wallet by owner username/identifier.
 */
export async function getWallet(owner: string): Promise<LocalWallet | null> {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_WALLET], 'readonly');
    const store = transaction.objectStore(STORE_WALLET);
    const req = store.get(owner);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Deducts amount from the local wallet in offsetDB after enforcing balance checks.
 */
export async function deductWalletBalance(owner: string, amount: number): Promise<LocalWallet> {
  const current = await getWallet(owner);
  if (!current) {
    throw new Error('Local offline wallet not initialized. Connect online to load wallet.');
  }

  if (amount <= 0) {
    throw new Error('Deduction amount must be positive');
  }

  if (current.balance < amount) {
    throw new Error(`Insufficient balance: ₹${current.balance.toFixed(2)} available, requested ₹${amount.toFixed(2)}`);
  }

  const updated: LocalWallet = {
    ...current,
    balance: parseFloat((current.balance - amount).toFixed(2)),
    dailyUsed: parseFloat((current.dailyUsed + amount).toFixed(2)),
    walletVersion: current.walletVersion + 1,
    lastUpdatedAt: new Date().toISOString(),
  };

  await saveWallet(updated);
  return updated;
}
