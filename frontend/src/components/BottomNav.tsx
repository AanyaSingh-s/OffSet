import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Wallet, QrCode, ArrowLeftRight, User } from 'lucide-react';

export const BottomNav: React.FC = () => {
  return (
    <nav className="bottom-nav">
      <NavLink
        to="/"
        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        end
      >
        <Home size={22} />
        <span>Home</span>
      </NavLink>

      <NavLink
        to="/wallet"
        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
      >
        <Wallet size={22} />
        <span>Wallet</span>
      </NavLink>

      <NavLink
        to="/scan"
        className="nav-item scan-fab"
        aria-label="Scan QR"
      >
        <QrCode size={26} />
        <span>Scan</span>
      </NavLink>

      <NavLink
        to="/transactions"
        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
      >
        <ArrowLeftRight size={22} />
        <span>Activity</span>
      </NavLink>

      <NavLink
        to="/profile"
        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
      >
        <User size={22} />
        <span>Profile</span>
      </NavLink>
    </nav>
  );
};
