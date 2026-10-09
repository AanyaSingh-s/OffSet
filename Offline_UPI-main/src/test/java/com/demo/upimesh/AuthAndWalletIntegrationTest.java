package com.demo.upimesh;

import com.demo.upimesh.dto.AuthDtos.LoginRequest;
import com.demo.upimesh.dto.AuthDtos.RegisterRequest;
import com.demo.upimesh.model.OfflineWalletRepository;
import com.demo.upimesh.model.UserRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class AuthAndWalletIntegrationTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;
    @Autowired private UserRepository userRepo;
    @Autowired private OfflineWalletRepository walletRepo;

    @Test
    void testRegistrationAndLoginFlow() throws Exception {
        RegisterRequest registerReq = new RegisterRequest(
                "rahul", "secret123", "Rahul Sharma", "rahul@offset"
        );

        MvcResult regResult = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.token").isString())
                .andExpect(jsonPath("$.username").value("rahul"))
                .andExpect(jsonPath("$.vpa").value("rahul@offset"))
                .andReturn();

        String regJson = regResult.getResponse().getContentAsString();
        JsonNode regNode = objectMapper.readTree(regJson);
        String token = regNode.get("token").asText();
        assertNotNull(token);

        // Verify duplicate username rejection
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerReq)))
                .andExpect(status().isBadRequest());

        // Verify login
        LoginRequest loginReq = new LoginRequest("rahul", "secret123");
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(loginReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").isString())
                .andExpect(jsonPath("$.username").value("rahul"));

        // Verify invalid login
        LoginRequest badLogin = new LoginRequest("rahul", "wrongpassword");
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(badLogin)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void testSeededAliceLoginAndWalletAccess() throws Exception {
        // Alice is seeded in DemoService
        LoginRequest loginReq = new LoginRequest("alice", "password123");
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(loginReq)))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode loginNode = objectMapper.readTree(loginResult.getResponse().getContentAsString());
        String token = loginNode.get("token").asText();

        // Access wallet without token -> 401
        mockMvc.perform(get("/api/wallet"))
                .andExpect(status().isUnauthorized());

        // Access wallet with token -> 200
        mockMvc.perform(get("/api/wallet")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.owner").value("alice"))
                .andExpect(jsonPath("$.balance").value(1000.00))
                .andExpect(jsonPath("$.transactionLimit").value(2000.00))
                .andExpect(jsonPath("$.dailyLimit").value(10000.00));
    }

    @Test
    void testWalletFundingAndLimitsValidation() throws Exception {
        // Log in as Bob
        LoginRequest loginReq = new LoginRequest("bob", "password123");
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(loginReq)))
                .andExpect(status().isOk())
                .andReturn();

        String token = objectMapper.readTree(loginResult.getResponse().getContentAsString()).get("token").asText();

        // 1. Funding with zero or negative amount -> 400
        mockMvc.perform(post("/api/wallet/fund")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": -50.00}"))
                .andExpect(status().isBadRequest());

        // 2. Funding exceeding transaction limit (₹2000) -> 400
        mockMvc.perform(post("/api/wallet/fund")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 2500.00}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value(org.hamcrest.Matchers.containsString("exceeds transaction limit")));

        // 3. Valid funding of ₹500
        BigDecimal bobBeforeBalance = walletRepo.findByOwner("bob").orElseThrow().getBalance();
        mockMvc.perform(post("/api/wallet/fund")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 500.00}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.fundedAmount").value(500.00))
                .andExpect(jsonPath("$.newBalance").value(bobBeforeBalance.add(new BigDecimal("500.00")).doubleValue()))
                .andExpect(jsonPath("$.gatewayTransactionId").value(org.hamcrest.Matchers.startsWith("mock_pay_")));

        // 4. Check /api/wallet/limits
        mockMvc.perform(get("/api/wallet/limits")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.owner").value("bob"))
                .andExpect(jsonPath("$.dailyUsed").value(500.00))
                .andExpect(jsonPath("$.dailyRemaining").value(9500.00));
    }
}
