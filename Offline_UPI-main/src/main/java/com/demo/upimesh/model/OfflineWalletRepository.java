package com.demo.upimesh.model;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface OfflineWalletRepository extends JpaRepository<OfflineWallet, Long> {
    Optional<OfflineWallet> findByOwner(String owner);
    boolean existsByOwner(String owner);
}
