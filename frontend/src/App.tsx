import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NetworkProvider } from './context/NetworkContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { MobileLayout } from './components/MobileLayout';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { Wallet } from './pages/Wallet';
import { Scan } from './pages/Scan';
import { Transactions } from './pages/Transactions';
import { Profile } from './pages/Profile';

export const App: React.FC = () => {
  return (
    <NetworkProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Authentication Route */}
            <Route path="/login" element={<Login />} />

            {/* Protected Routes wrapped in MobileLayout and Android BottomNav */}
            <Route
              element={
                <ProtectedRoute>
                  <MobileLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Home />} />
              <Route path="/wallet" element={<Wallet />} />
              <Route path="/scan" element={<Scan />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/profile" element={<Profile />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </NetworkProvider>
  );
};

export default App;
