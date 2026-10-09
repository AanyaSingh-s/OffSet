package com.demo.upimesh.controller;

import com.demo.upimesh.dto.AuthDtos.AuthResponse;
import com.demo.upimesh.dto.AuthDtos.LoginRequest;
import com.demo.upimesh.dto.AuthDtos.RegisterRequest;
import com.demo.upimesh.model.Account;
import com.demo.upimesh.model.AccountRepository;
import com.demo.upimesh.model.User;
import com.demo.upimesh.model.UserRepository;
import com.demo.upimesh.security.JwtUtil;
import com.demo.upimesh.service.WalletService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserRepository userRepository;
    private final AccountRepository accountRepository;
    private final WalletService walletService;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthController(UserRepository userRepository,
                          AccountRepository accountRepository,
                          WalletService walletService,
                          PasswordEncoder passwordEncoder,
                          JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.accountRepository = accountRepository;
        this.walletService = walletService;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody RegisterRequest req) {
        if (userRepository.existsByUsername(req.getUsername())) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username already taken: " + req.getUsername()));
        }

        String vpa = (req.getVpa() != null && !req.getVpa().trim().isEmpty())
                ? req.getVpa().trim()
                : req.getUsername().trim() + "@offset";

        if (userRepository.existsByVpa(vpa)) {
            return ResponseEntity.badRequest().body(Map.of("error", "VPA already registered: " + vpa));
        }

        User user = new User(
                req.getUsername().trim(),
                passwordEncoder.encode(req.getPassword()),
                req.getFullName() != null ? req.getFullName().trim() : req.getUsername().trim(),
                vpa
        );
        userRepository.save(user);

        // Ensure matching ledger Account exists for this VPA
        if (accountRepository.findById(vpa).isEmpty()) {
            accountRepository.save(new Account(
                    vpa,
                    user.getFullName(),
                    BigDecimal.ZERO.setScale(2)
            ));
        }

        // Initialize OfflineWallet for the user
        walletService.getOrCreateWallet(user.getUsername());

        String token = jwtUtil.generateToken(user.getUsername(), user.getVpa());
        return ResponseEntity.status(HttpStatus.CREATED).body(
                new AuthResponse(token, user.getUsername(), user.getVpa(), "User registered successfully")
        );
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest req) {
        var userOpt = userRepository.findByUsername(req.getUsername().trim());
        if (userOpt.isEmpty() || !passwordEncoder.matches(req.getPassword(), userOpt.get().getPassword())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(
                    Map.of("error", "Invalid username or password")
            );
        }

        User user = userOpt.get();
        String token = jwtUtil.generateToken(user.getUsername(), user.getVpa());
        return ResponseEntity.ok(
                new AuthResponse(token, user.getUsername(), user.getVpa(), "Login successful")
        );
    }
}
