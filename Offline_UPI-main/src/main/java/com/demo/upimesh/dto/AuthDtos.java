package com.demo.upimesh.dto;

import com.demo.upimesh.model.OfflineWallet;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public class AuthDtos {

    public static class RegisterRequest {
        @NotBlank(message = "Username cannot be blank")
        @Size(min = 3, max = 50, message = "Username must be between 3 and 50 characters")
        private String username;

        @NotBlank(message = "Password cannot be blank")
        @Size(min = 4, max = 100, message = "Password must be at least 4 characters")
        private String password;

        private String fullName;
        private String vpa;

        public RegisterRequest() {}

        public RegisterRequest(String username, String password, String fullName, String vpa) {
            this.username = username;
            this.password = password;
            this.fullName = fullName;
            this.vpa = vpa;
        }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }

        public String getFullName() { return fullName; }
        public void setFullName(String fullName) { this.fullName = fullName; }

        public String getVpa() { return vpa; }
        public void setVpa(String vpa) { this.vpa = vpa; }
    }

    public static class LoginRequest {
        @NotBlank(message = "Username cannot be blank")
        private String username;

        @NotBlank(message = "Password cannot be blank")
        private String password;

        public LoginRequest() {}

        public LoginRequest(String username, String password) {
            this.username = username;
            this.password = password;
        }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }

    public static class AuthResponse {
        private String token;
        private String type = "Bearer";
        private String username;
        private String vpa;
        private String message;

        public AuthResponse() {}

        public AuthResponse(String token, String username, String vpa, String message) {
            this.token = token;
            this.type = "Bearer";
            this.username = username;
            this.vpa = vpa;
            this.message = message;
        }

        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }

        public String getType() { return type; }
        public void setType(String type) { this.type = type; }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getVpa() { return vpa; }
        public void setVpa(String vpa) { this.vpa = vpa; }

        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static class FundWalletRequest {
        @NotNull(message = "Funding amount is required")
        @DecimalMin(value = "0.01", message = "Funding amount must be greater than zero")
        private BigDecimal amount;

        public FundWalletRequest() {}

        public FundWalletRequest(BigDecimal amount) {
            this.amount = amount;
        }

        public BigDecimal getAmount() { return amount; }
        public void setAmount(BigDecimal amount) { this.amount = amount; }
    }

    public static class FundWalletResponse {
        private boolean success;
        private String message;
        private String gatewayTransactionId;
        private BigDecimal fundedAmount;
        private BigDecimal newBalance;
        private Long walletVersion;
        private OfflineWallet wallet;

        public FundWalletResponse() {}

        public FundWalletResponse(boolean success, String message, String gatewayTransactionId,
                                  BigDecimal fundedAmount, BigDecimal newBalance,
                                  Long walletVersion, OfflineWallet wallet) {
            this.success = success;
            this.message = message;
            this.gatewayTransactionId = gatewayTransactionId;
            this.fundedAmount = fundedAmount;
            this.newBalance = newBalance;
            this.walletVersion = walletVersion;
            this.wallet = wallet;
        }

        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }

        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }

        public String getGatewayTransactionId() { return gatewayTransactionId; }
        public void setGatewayTransactionId(String gatewayTransactionId) { this.gatewayTransactionId = gatewayTransactionId; }

        public BigDecimal getFundedAmount() { return fundedAmount; }
        public void setFundedAmount(BigDecimal fundedAmount) { this.fundedAmount = fundedAmount; }

        public BigDecimal getNewBalance() { return newBalance; }
        public void setNewBalance(BigDecimal newBalance) { this.newBalance = newBalance; }

        public Long getWalletVersion() { return walletVersion; }
        public void setWalletVersion(Long walletVersion) { this.walletVersion = walletVersion; }

        public OfflineWallet getWallet() { return wallet; }
        public void setWallet(OfflineWallet wallet) { this.wallet = wallet; }
    }

    public static class WalletLimitsResponse {
        private String owner;
        private BigDecimal transactionLimit;
        private BigDecimal dailyLimit;
        private BigDecimal dailyUsed;
        private BigDecimal dailyRemaining;
        private BigDecimal balance;
        private Long walletVersion;

        public WalletLimitsResponse() {}

        public WalletLimitsResponse(String owner, BigDecimal transactionLimit, BigDecimal dailyLimit,
                                    BigDecimal dailyUsed, BigDecimal dailyRemaining,
                                    BigDecimal balance, Long walletVersion) {
            this.owner = owner;
            this.transactionLimit = transactionLimit;
            this.dailyLimit = dailyLimit;
            this.dailyUsed = dailyUsed;
            this.dailyRemaining = dailyRemaining;
            this.balance = balance;
            this.walletVersion = walletVersion;
        }

        public String getOwner() { return owner; }
        public void setOwner(String owner) { this.owner = owner; }

        public BigDecimal getTransactionLimit() { return transactionLimit; }
        public void setTransactionLimit(BigDecimal transactionLimit) { this.transactionLimit = transactionLimit; }

        public BigDecimal getDailyLimit() { return dailyLimit; }
        public void setDailyLimit(BigDecimal dailyLimit) { this.dailyLimit = dailyLimit; }

        public BigDecimal getDailyUsed() { return dailyUsed; }
        public void setDailyUsed(BigDecimal dailyUsed) { this.dailyUsed = dailyUsed; }

        public BigDecimal getDailyRemaining() { return dailyRemaining; }
        public void setDailyRemaining(BigDecimal dailyRemaining) { this.dailyRemaining = dailyRemaining; }

        public BigDecimal getBalance() { return balance; }
        public void setBalance(BigDecimal balance) { this.balance = balance; }

        public Long getWalletVersion() { return walletVersion; }
        public void setWalletVersion(Long walletVersion) { this.walletVersion = walletVersion; }
    }
}
