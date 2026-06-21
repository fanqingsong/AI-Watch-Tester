"use client";

import { createContext, useContext, type ReactNode } from "react";

interface LocalUser {
  id: string;
  email: string;
}

interface AuthCtx {
  user: LocalUser;
  loading: boolean;
}

const LOCAL_USER: LocalUser = {
  id: "local-user",
  email: "local@awt.dev",
};

const AuthContext = createContext<AuthCtx>({
  user: LOCAL_USER,
  loading: false,
});

/** Local mode: no authentication. Always provides the single built-in local user. */
export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <AuthContext.Provider value={{ user: LOCAL_USER, loading: false }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
