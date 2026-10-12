package com.demo.upimesh.controller;

import com.demo.upimesh.model.Account;
import com.demo.upimesh.model.AccountRepository;
import com.demo.upimesh.model.Transaction;
import com.demo.upimesh.model.TransactionRepository;
import com.demo.upimesh.service.IdempotencyService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Day 7: OffSet Automatic Synchronization Controller
 * Accepts synced offline transactions from mobile clients,
 * applies idempotent duplicate checking, risk evaluation, and ledger updates.
 *
 * Supported Response States:
 *   - SUCCESS
 *   - DUPLICATE
 *   - FAILED
 *   - FRAUD_FLAGGED
 */
@RestController
@RequestMapping("/api/sync")
public class SyncController {

    private static final Logger log = LoggerFactory.getLogger(SyncController.class);

    @Autowired private AccountRepository accountRepo;
    @Autowired private TransactionRepository txRepo;
    @Autowired private IdempotencyService idempotency;

    public static class SyncTransactionRequest {
        public String transactionId;
        public String sender;
        public String receiver;
        public BigDecimal amount;
        public String nonce;
        public String createdAt;
        public String pin;
    }

    public static class SyncTransactionResponse {
        public String status; // SUCCESS, DUPLICATE, FAILED, FRAUD_FLAGGED
        public String transactionId;
        public String message;
        public Long ledgerTransactionId;

        public SyncTransactionResponse() {}

        public SyncTransactionResponse(String status, String transactionId, String message, Long ledgerTransactionId) {
            this.status = status;
            this.transactionId = transactionId;
            this.message = message;
            this.ledgerTransactionId = ledgerTransactionId;
        }
    }

    @PostMapping("/transaction")
    @Transactional
    public ResponseEntity<SyncTransactionResponse> syncTransaction(@RequestBody SyncTransactionRequest req) {
        log.info("Received sync request: txId={}, sender={}, receiver={}, amount={}",
                req.transactionId, req.sender, req.receiver, req.amount);

        if (req.transactionId == null || req.transactionId.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(
                    new SyncTransactionResponse("FAILED", req.transactionId, "Missing transactionId", null)
            );
        }

        // 1. Idempotency Gate (Guarantees at-most-once settlement)
        String idempotencyKey = "sync_" + req.transactionId;
        if (!idempotency.claim(idempotencyKey)) {
            log.info("DUPLICATE transaction {} dropped by idempotency cache", req.transactionId);
            return ResponseEntity.ok(
                    new SyncTransactionResponse("DUPLICATE", req.transactionId, "Transaction already settled", null)
            );
        }

        // 2. Fraud / Risk Evaluation Check
        if (req.receiver != null && (req.receiver.contains("fraud") || req.receiver.contains("scam") || req.receiver.contains("flagged"))) {
            log.warn("FRAUD_FLAGGED: Suspicious payee pattern in transaction {}", req.transactionId);
            return ResponseEntity.ok(
                    new SyncTransactionResponse("FRAUD_FLAGGED", req.transactionId, "Transaction blocked by OffSet Risk Service", null)
            );
        }

        if (req.amount != null && req.amount.compareTo(new BigDecimal("20000.00")) > 0) {
            log.warn("FRAUD_FLAGGED: Exceeds absolute offline threshold {}", req.transactionId);
            return ResponseEntity.ok(
                    new SyncTransactionResponse("FRAUD_FLAGGED", req.transactionId, "Amount exceeds security threshold", null)
            );
        }

        // 3. Validation
        if (req.amount == null || req.amount.compareTo(BigDecimal.ZERO) <= 0) {
            return ResponseEntity.ok(
                    new SyncTransactionResponse("FAILED", req.transactionId, "Amount must be positive", null)
            );
        }

        Account senderAccount = accountRepo.findById(req.sender).orElse(null);
        if (senderAccount == null) {
            // In demo/prototype, create sender account with default balance if first time
            senderAccount = accountRepo.save(new Account(req.sender, req.sender, new BigDecimal("5000.00")));
        }

        Account receiverAccount = accountRepo.findById(req.receiver).orElse(null);
        if (receiverAccount == null) {
            // Auto-provision receiver account in demo ledger
            receiverAccount = accountRepo.save(new Account(req.receiver, req.receiver, BigDecimal.ZERO));
        }

        // 4. Ledger Balance Check
        if (senderAccount.getBalance().compareTo(req.amount) < 0) {
            log.warn("FAILED: Insufficient core ledger balance for sender {}", req.sender);
            return ResponseEntity.ok(
                    new SyncTransactionResponse("FAILED", req.transactionId, "Insufficient account balance in core ledger", null)
            );
        }

        // 5. Atomic Settlement
        senderAccount.setBalance(senderAccount.getBalance().subtract(req.amount));
        receiverAccount.setBalance(receiverAccount.getBalance().add(req.amount));
        accountRepo.save(senderAccount);
        accountRepo.save(receiverAccount);

        Transaction ledgerTx = new Transaction();
        ledgerTx.setPacketHash(req.nonce != null ? req.nonce : req.transactionId);
        ledgerTx.setSenderVpa(req.sender);
        ledgerTx.setReceiverVpa(req.receiver);
        ledgerTx.setAmount(req.amount);
        ledgerTx.setSignedAt(Instant.now());
        ledgerTx.setSettledAt(Instant.now());
        ledgerTx.setBridgeNodeId("mobile_sync_client");
        ledgerTx.setHopCount(0);
        ledgerTx.setStatus(Transaction.Status.SETTLED);
        Transaction savedTx = txRepo.save(ledgerTx);

        log.info("SUCCESS: Synced and settled offline transaction {} (ledgerTxId={})",
                req.transactionId, savedTx.getId());

        return ResponseEntity.ok(
                new SyncTransactionResponse("SUCCESS", req.transactionId, "Transaction settled successfully", savedTx.getId())
        );
    }

    @PostMapping("/batch")
    @Transactional
    public ResponseEntity<List<SyncTransactionResponse>> syncBatch(@RequestBody List<SyncTransactionRequest> batch) {
        List<SyncTransactionResponse> results = new ArrayList<>();
        for (SyncTransactionRequest req : batch) {
            ResponseEntity<SyncTransactionResponse> res = syncTransaction(req);
            results.add(res.getBody());
        }
        return ResponseEntity.ok(results);
    }
}
