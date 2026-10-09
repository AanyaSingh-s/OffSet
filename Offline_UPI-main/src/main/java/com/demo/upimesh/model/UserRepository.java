package com.demo.upimesh.model;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);
    boolean existsByUsername(String username);
    boolean existsByVpa(String vpa);
    Optional<User> findByVpa(String vpa);
}
