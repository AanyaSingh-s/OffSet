package com.demo.upimesh.controller;

import com.demo.upimesh.dto.AuthDtos.FundWalletRequest;
import com.demo.upimesh.dto.AuthDtos.FundWalletResponse;
import com.demo.upimesh.dto.AuthDtos.WalletLimitsResponse;
import com.demo.upimesh.model.OfflineWallet;
import com.demo.upimesh.service.WalletService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;
import java.util.Map;

@RestController
@RequestMapping("/api/wallet")
public class WalletController {

    private final WalletService walletService;

    public WalletController(WalletService walletService) {
        this.walletService = walletService;
    }

    @GetMapping
    public ResponseEntity<OfflineWallet> getWallet(Principal principal) {
        if (principal == null) {
            return ResponseEntity.status(401).build();
        }
        OfflineWallet wallet = walletService.getWallet(principal.getName());
        return ResponseEntity.ok(wallet);
    }

    @PostMapping("/fund")
    public ResponseEntity<?> fundWallet(@Valid @RequestBody FundWalletRequest req, Principal principal) {
        if (principal == null) {
            return ResponseEntity.status(401).body(Map.of("error", "Authentication required"));
        }
        try {
            FundWalletResponse response = walletService.fundWallet(principal.getName(), req.getAmount());
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/limits")
    public ResponseEntity<?> getLimits(Principal principal) {
        if (principal == null) {
            return ResponseEntity.status(401).build();
        }
        WalletLimitsResponse limits = walletService.getLimits(principal.getName());
        return ResponseEntity.ok(limits);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> handleIllegalArgument(IllegalArgumentException ex) {
        return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
    }
}
