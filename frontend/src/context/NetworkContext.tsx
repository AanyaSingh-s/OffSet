import React, { createContext, useContext, useState, useEffect } from 'react';

interface NetworkContextType {
  isOnline: boolean;
  toggleSimulatedOffline: () => void;
  isSimulatedOffline: boolean;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

export const NetworkProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [actualOnline, setActualOnline] = useState<boolean>(navigator.onLine);
  const [isSimulatedOffline, setIsSimulatedOffline] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => setActualOnline(true);
    const handleOffline = () => setActualOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const isOnline = actualOnline && !isSimulatedOffline;

  const toggleSimulatedOffline = () => {
    setIsSimulatedOffline(prev => !prev);
  };

  return (
    <NetworkContext.Provider
      value={{
        isOnline,
        toggleSimulatedOffline,
        isSimulatedOffline,
      }}
    >
      {children}
    </NetworkContext.Provider>
  );
};

export const useNetwork = (): NetworkContextType => {
  const context = useContext(NetworkContext);
  if (!context) {
    throw new Error('useNetwork must be used within a NetworkProvider');
  }
  return context;
};
