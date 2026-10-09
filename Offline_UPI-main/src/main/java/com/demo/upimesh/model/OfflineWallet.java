package com.demo.upimesh.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

/**
 * OfflineWallet entity tracking offline balance and limits for an authenticated user.
 */
@Entity
@Table(name = "offline_wallets")
public class OfflineWallet {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Owner identifier (user's username or identifier)
    @Column(nullable = false, unique = true)
    private String owner;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal balance;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal transactionLimit;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal dailyLimit;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal dailyUsed;

    @Column(nullable = false)
    private Long walletVersion;

    @Column(nullable = false)
    private Instant updatedAt;

    public OfflineWallet() {}

    public OfflineWallet(String owner, BigDecimal balance, BigDecimal transactionLimit, BigDecimal dailyLimit) {
        this.owner = owner;
        this.balance = balance != null ? balance : BigDecimal.ZERO.setScale(2);
        this.transactionLimit = transactionLimit != null ? transactionLimit : new BigDecimal("2000.00");
        this.dailyLimit = dailyLimit != null ? dailyLimit : new BigDecimal("10000.00");
        this.dailyUsed = BigDecimal.ZERO.setScale(2);
        this.walletVersion = 1L;
        this.updatedAt = Instant.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getOwner() { return owner; }
    public void setOwner(String owner) { this.owner = owner; }

    public BigDecimal getBalance() { return balance; }
    public void setBalance(BigDecimal balance) { this.balance = balance; }

    public BigDecimal getTransactionLimit() { return transactionLimit; }
    public void setTransactionLimit(BigDecimal transactionLimit) { this.transactionLimit = transactionLimit; }

    public BigDecimal getDailyLimit() { return dailyLimit; }
    public void setDailyLimit(BigDecimal dailyLimit) { this.dailyLimit = dailyLimit; }

    public BigDecimal getDailyUsed() { return dailyUsed; }
    public void setDailyUsed(BigDecimal dailyUsed) { this.dailyUsed = dailyUsed; }

    public Long getWalletVersion() { return walletVersion; }
    public void setWalletVersion(Long walletVersion) { this.walletVersion = walletVersion; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
