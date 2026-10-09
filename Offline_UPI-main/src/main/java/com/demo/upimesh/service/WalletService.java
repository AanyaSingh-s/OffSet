package com.demo.upimesh.service;

import com.demo.upimesh.dto.AuthDtos.FundWalletResponse;
import com.demo.upimesh.dto.AuthDtos.WalletLimitsResponse;
import com.demo.upimesh.model.OfflineWallet;
import com.demo.upimesh.model.OfflineWalletRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Service
public class WalletService {

    private static final Logger log = LoggerFactory.getLogger(WalletService.class);

    private final OfflineWalletRepository walletRepository;

    public WalletService(OfflineWalletRepository walletRepository) {
        this.walletRepository = walletRepository;
    }

    @Transactional
    public OfflineWallet getOrCreateWallet(String owner) {
        return walletRepository.findByOwner(owner)
                .orElseGet(() -> {
                    OfflineWallet wallet = new OfflineWallet(
                            owner,
                            BigDecimal.ZERO.setScale(2),
                            new BigDecimal("2000.00"),
                            new BigDecimal("10000.00")
                    );
                    log.info("Initialized default offline wallet for owner: {}", owner);
                    return walletRepository.save(wallet);
                });
    }

    @Transactional(readOnly = true)
    public OfflineWallet getWallet(String owner) {
        return getOrCreateWallet(owner);
    }

    @Transactional
    public FundWalletResponse fundWallet(String owner, BigDecimal amount) {
        if (owner == null || owner.trim().isEmpty()) {
            throw new IllegalArgumentException("Authenticated user ownership required");
        }

        // 1. Validation: positive funding amount
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Funding amount must be greater than zero");
        }

        OfflineWallet wallet = getOrCreateWallet(owner);

        // 2. Validation: transaction limit
        if (amount.compareTo(wallet.getTransactionLimit()) > 0) {
            throw new IllegalArgumentException(
                    String.format("Funding amount ₹%.2f exceeds transaction limit of ₹%.2f",
                            amount, wallet.getTransactionLimit())
            );
        }

        // 3. Validation: daily limit
        BigDecimal newDailyUsed = wallet.getDailyUsed().add(amount);
        if (newDailyUsed.compareTo(wallet.getDailyLimit()) > 0) {
            BigDecimal remaining = wallet.getDailyLimit().subtract(wallet.getDailyUsed());
            if (remaining.compareTo(BigDecimal.ZERO) < 0) remaining = BigDecimal.ZERO;
            throw new IllegalArgumentException(
                    String.format("Funding amount ₹%.2f exceeds remaining daily limit of ₹%.2f",
                            amount, remaining)
            );
        }

        // 4. Mock gateway operation (simulates successful payment gateway response)
        String mockGatewayTxId = "mock_pay_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

        // 5. Update wallet
        wallet.setBalance(wallet.getBalance().add(amount));
        wallet.setDailyUsed(newDailyUsed);
        wallet.setWalletVersion(wallet.getWalletVersion() + 1);
        wallet.setUpdatedAt(Instant.now());
        OfflineWallet savedWallet = walletRepository.save(wallet);

        log.info("Wallet funded successfully: owner={}, amount=₹{}, newBalance=₹{}, version={}, gatewayTxId={}",
                owner, amount, savedWallet.getBalance(), savedWallet.getWalletVersion(), mockGatewayTxId);

        return new FundWalletResponse(
                true,
                "Wallet funded successfully via mock payment gateway",
                mockGatewayTxId,
                amount,
                savedWallet.getBalance(),
                savedWallet.getWalletVersion(),
                savedWallet
        );
    }

    @Transactional(readOnly = true)
    public WalletLimitsResponse getLimits(String owner) {
        OfflineWallet wallet = getOrCreateWallet(owner);
        BigDecimal remaining = wallet.getDailyLimit().subtract(wallet.getDailyUsed());
        if (remaining.compareTo(BigDecimal.ZERO) < 0) {
            remaining = BigDecimal.ZERO.setScale(2);
        }

        return new WalletLimitsResponse(
                wallet.getOwner(),
                wallet.getTransactionLimit(),
                wallet.getDailyLimit(),
                wallet.getDailyUsed(),
                remaining,
                wallet.getBalance(),
                wallet.getWalletVersion()
        );
    }
}
