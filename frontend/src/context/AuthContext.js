import React, { createContext, useContext, useState, useEffect } from "react";
import { mockUser } from "../mock";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("sp_user");
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch (e) {
        localStorage.removeItem("sp_user");
      }
    }
    setLoading(false);
  }, []);

  // Mock login — accepts admin / admin
  const login = async (username, password) => {
    await new Promise((r) => setTimeout(r, 500));
    if (username === "admin" && password === "admin") {
      const u = { ...mockUser, token: "mock-jwt-token" };
      localStorage.setItem("sp_user", JSON.stringify(u));
      setUser(u);
      return { ok: true };
    }
    return { ok: false, error: "Invalid credentials. Try admin / admin" };
  };

  const logout = () => {
    localStorage.removeItem("sp_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
