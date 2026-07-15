import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("sp_user");
    if (stored) {
      try {
        const u = JSON.parse(stored);
        setUser(u);
      } catch (e) {
        localStorage.removeItem("sp_user");
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const data = await api.login(username, password);
      const u = { ...data.user, token: data.access_token };
      localStorage.setItem("sp_user", JSON.stringify(u));
      setUser(u);
      return { ok: true };
    } catch (e) {
      return {
        ok: false,
        error:
          e?.response?.status === 401
            ? "Invalid credentials. Try admin / admin"
            : "Login failed. Please try again.",
      };
    }
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
