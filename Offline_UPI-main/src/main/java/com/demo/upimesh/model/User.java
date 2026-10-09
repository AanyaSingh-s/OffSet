package com.demo.upimesh.model;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * User credentials and identity for the OffSet system.
 */
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String username;

    @Column(nullable = false)
    private String password;

    private String fullName;

    @Column(nullable = false, unique = true)
    private String vpa;

    @Column(nullable = false)
    private Instant createdAt;

    public User() {}

    public User(String username, String password, String fullName, String vpa) {
        this.username = username;
        this.password = password;
        this.fullName = fullName;
        this.vpa = vpa;
        this.createdAt = Instant.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }

    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }

    public String getVpa() { return vpa; }
    public void setVpa(String vpa) { this.vpa = vpa; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
