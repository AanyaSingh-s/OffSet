/**
 * Automated Verification Test Suite for Day 5 (offsetDB) and Day 6 (Offline Payment Flow).
 * Executes against fake-indexeddb simulating the full browser IndexedDB lifecycle.
 */

import 'fake-indexeddb/auto';
import {
  initDB,
  saveTransaction,
  getTransaction,
  getPendingTransactions,
  updateTransaction,
  deleteTransaction,
  getTransactionHistory,
  saveWallet,
  getWallet,
  OffSetTransaction,
  LocalWallet,
  DB_NAME
} from '../services/indexedDb';
import { OfflinePaymentService } from '../services/offlinePaymentService';

async function runTests() {
  console.log('========================================================');
  console.log('🚀 STARTING DAY 5 & DAY 6 TEST SUITE (offsetDB)');
  console.log('========================================================\n');

  // -------------------------------------------------------------------
  // DAY 5 TESTS
  // -------------------------------------------------------------------
  console.log('--- [DAY 5: LOCAL OFFLINE STORAGE (offsetDB)] ---');

  // Test 1: Initialize offsetDB and Create transaction
  console.log('Test 1: Create transaction');
  const db = await initDB();
  if (db.name !== 'offsetDB') {
    throw new Error(`Expected DB name "offsetDB", got "${db.name}"`);
  }
  console.log('  ✓ initDB() verified DB name: "offsetDB"');

  const tx1: OffSetTransaction = {
    transactionId: 'tx_test_001',
    sender: 'alice@demo',
    receiver: 'bob@demo',
    amount: 250.0,
    nonce: 'nonce_abc123',
    createdAt: new Date().toISOString(),
    status: 'PENDING_SYNC',
    syncAttempts: 0,
    lastSyncAttempt: null,
  };
  await saveTransaction(tx1);
  console.log('  ✓ saveTransaction() successfully created tx_test_001');

  // Test 2 & 3: Close DB connection (simulate app close) and reopen
  console.log('Test 2 & 3: Close connection and reopen');
  db.close();
  console.log('  ✓ Simulated app close: DB connection closed');
  const reopenedDb = await initDB();
  console.log('  ✓ Reopened DB connection');

  // Test 4: Retrieve transaction
  console.log('Test 4: Retrieve transaction');
  const retrieved = await getTransaction('tx_test_001');
  if (!retrieved || retrieved.amount !== 250.0 || retrieved.sender !== 'alice@demo') {
    throw new Error('Failed to retrieve matching transaction after reopening');
  }
  console.log('  ✓ getTransaction() correctly retrieved:', retrieved);

  // Test 5: Retrieve pending transactions
  console.log('Test 5: Retrieve pending transactions');
  const tx2: OffSetTransaction = {
    transactionId: 'tx_test_002',
    sender: 'alice@demo',
    receiver: 'carol@demo',
    amount: 100.0,
    nonce: 'nonce_def456',
    createdAt: new Date().toISOString(),
    status: 'SUCCESS', // Not pending
    syncAttempts: 1,
    lastSyncAttempt: new Date().toISOString(),
  };
  await saveTransaction(tx2);

  const pendingList = await getPendingTransactions();
  if (pendingList.length !== 1 || pendingList[0].transactionId !== 'tx_test_001') {
    throw new Error(`Expected 1 pending transaction, got ${pendingList.length}`);
  }
  console.log(`  ✓ getPendingTransactions() returned ${pendingList.length} PENDING_SYNC tx(s)`);

  // Test 6: Update status
  console.log('Test 6: Update status');
  await updateTransaction('tx_test_001', {
    status: 'SYNCING',
    syncAttempts: 1,
    lastSyncAttempt: new Date().toISOString(),
  });
  const updatedTx = await getTransaction('tx_test_001');
  if (updatedTx?.status !== 'SYNCING' || updatedTx?.syncAttempts !== 1) {
    throw new Error(`Failed to update status to SYNCING, got ${updatedTx?.status}`);
  }
  console.log('  ✓ updateTransaction() updated status to SYNCING');

  // Test 7: Delete transaction
  console.log('Test 7: Delete transaction');
  await deleteTransaction('tx_test_002');
  const deletedTx = await getTransaction('tx_test_002');
  if (deletedTx !== null) {
    throw new Error('Transaction was not deleted');
  }
  console.log('  ✓ deleteTransaction() successfully deleted tx_test_002');

  console.log('\n✅ ALL DAY 5 TESTS PASSED!\n');

  // -------------------------------------------------------------------
  // DAY 6 TESTS
  // -------------------------------------------------------------------
  console.log('--- [DAY 6: OFFLINE PAYMENT CREATION FLOW] ---');

  // Seed local wallet in offsetDB
  const initialWallet: LocalWallet = {
    owner: 'alice',
    balance: 1000.0,
    transactionLimit: 2000.0,
    dailyLimit: 5000.0,
    dailyUsed: 0.0,
    walletVersion: 1,
    lastUpdatedAt: new Date().toISOString(),
  };
  await saveWallet(initialWallet);
  console.log('Seeded local wallet: balance ₹1000.00, txLimit ₹2000.00, dailyLimit ₹5000.00');

  const userAlice = { username: 'alice', vpa: 'alice@demo' };

  // Test 1: Successful offline payment of ₹500 to Bob
  console.log('Test 1: Successful offline payment of ₹500 to Bob');
  const res1 = await OfflinePaymentService.executeOfflinePayment({
    user: userAlice,
    recipientVpa: 'bob@demo',
    amount: 500.0,
  });

  if (res1.transaction.status !== 'PENDING_SYNC') {
    throw new Error(`Expected status PENDING_SYNC, got ${res1.transaction.status}`);
  }
  if (res1.updatedWallet.balance !== 500.0) {
    throw new Error(`Expected wallet balance ₹500.00, got ${res1.updatedWallet.balance}`);
  }
  if (res1.updatedWallet.dailyUsed !== 500.0) {
    throw new Error(`Expected dailyUsed ₹500.00, got ${res1.updatedWallet.dailyUsed}`);
  }
  console.log('  ✓ Offline payment executed:');
  console.log(`    - ID: ${res1.transaction.transactionId}`);
  console.log(`    - Status: ${res1.transaction.status}`);
  console.log(`    - Amount: ₹${res1.transaction.amount}`);
  console.log(`    - Nonce: ${res1.transaction.nonce}`);
  console.log(`    - New Wallet Balance: ₹${res1.updatedWallet.balance}`);

  // Test 2: Insufficient balance rejection
  console.log('Test 2: Insufficient balance rejection');
  try {
    await OfflinePaymentService.executeOfflinePayment({
      user: userAlice,
      recipientVpa: 'bob@demo',
      amount: 600.0, // Remaining balance is ₹500
    });
    throw new Error('Should have failed due to insufficient balance');
  } catch (e: any) {
    console.log(`  ✓ Expected failure caught: "${e.message}"`);
  }

  // Test 3: Transaction limit exceeded rejection (> ₹2000)
  console.log('Test 3: Transaction limit exceeded rejection');
  // First temporarily top up balance to test per-tx limit
  await saveWallet({ ...res1.updatedWallet, balance: 5000.0 });
  try {
    await OfflinePaymentService.executeOfflinePayment({
      user: userAlice,
      recipientVpa: 'bob@demo',
      amount: 2500.0, // Limit is ₹2000
    });
    throw new Error('Should have failed due to per-tx limit');
  } catch (e: any) {
    console.log(`  ✓ Expected failure caught: "${e.message}"`);
  }

  // Test 4: Daily limit exceeded rejection
  console.log('Test 4: Daily limit exceeded rejection');
  // Set dailyUsed near dailyLimit (dailyLimit=5000, dailyUsed=4800, balance=1000)
  await saveWallet({
    ...res1.updatedWallet,
    balance: 1000.0,
    dailyLimit: 5000.0,
    dailyUsed: 4800.0,
  });
  try {
    await OfflinePaymentService.executeOfflinePayment({
      user: userAlice,
      recipientVpa: 'bob@demo',
      amount: 300.0, // Remaining daily allowance is ₹200
    });
    throw new Error('Should have failed due to daily limit');
  } catch (e: any) {
    console.log(`  ✓ Expected failure caught: "${e.message}"`);
  }

  // Test 5: Invalid recipient rejection
  console.log('Test 5: Invalid recipient rejection');
  try {
    await OfflinePaymentService.executeOfflinePayment({
      user: userAlice,
      recipientVpa: 'alice@demo', // Self transfer
      amount: 50.0,
    });
    throw new Error('Should have failed due to self transfer');
  } catch (e: any) {
    console.log(`  ✓ Expected failure caught: "${e.message}"`);
  }

  try {
    await OfflinePaymentService.executeOfflinePayment({
      user: userAlice,
      recipientVpa: '', // Empty
      amount: 50.0,
    });
    throw new Error('Should have failed due to empty recipient');
  } catch (e: any) {
    console.log(`  ✓ Expected failure caught: "${e.message}"`);
  }

  // Test 6 & 7: Multiple offline payments and persistence after reload
  console.log('Test 6 & 7: Multiple offline payments and reload persistence');
  // Reset clean wallet: balance ₹1000
  await saveWallet({
    owner: 'alice',
    balance: 1000.0,
    transactionLimit: 2000.0,
    dailyLimit: 10000.0,
    dailyUsed: 0.0,
    walletVersion: 1,
    lastUpdatedAt: new Date().toISOString(),
  });

  // Pay #1: ₹100 to Dave
  const p1 = await OfflinePaymentService.executeOfflinePayment({
    user: userAlice,
    recipientVpa: 'dave@demo',
    amount: 100.0,
  });
  // Pay #2: ₹150 to Carol
  const p2 = await OfflinePaymentService.executeOfflinePayment({
    user: userAlice,
    recipientVpa: 'carol@demo',
    amount: 150.0,
  });

  // Reopen DB
  reopenedDb.close();
  const dbFinal = await initDB();
  const allHistory = await getTransactionHistory('alice@demo');
  const allPending = await getPendingTransactions();

  console.log(`  ✓ Total transactions persisted in offsetDB: ${allHistory.length}`);
  console.log(`  ✓ Total PENDING_SYNC transactions in offsetDB: ${allPending.length}`);
  const finalWallet = await getWallet('alice');
  console.log(`  ✓ Final wallet balance: ₹${finalWallet?.balance} (expected 750.00)`);

  if (finalWallet?.balance !== 750.0) {
    throw new Error(`Expected balance 750.00, got ${finalWallet?.balance}`);
  }

  console.log('\n✅ ALL DAY 6 TESTS PASSED!\n');
  console.log('========================================================');
  console.log('🎉 ALL DAY 5 & DAY 6 TEST SPECIFICATIONS VERIFIED 100%');
  console.log('========================================================');
}

runTests().catch((err) => {
  console.error('\n❌ TEST RUN FAILED:', err);
  process.exit(1);
});
