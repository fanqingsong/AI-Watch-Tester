"use client";

import { createContext, useContext, type ReactNode } from "react";

interface LocalUser {
  id: string;
  email: string;
}

interface AuthCtx {
  user: LocalUser | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>({
  user: { id: "local-user", email: "local@awt.dev" },
  loading: false,
  signOut: async () => {},
});

const LOCAL_USER: LocalUser = {
  id: "local-user",
  email: "local@awt.dev",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  // Local mode: no authentication, always return the default local user
  const signOut = async () => {
    // No-op in local mode
  };

  return (
    <AuthContext.Provider value={{ user: LOCAL_USER, loading: false, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
