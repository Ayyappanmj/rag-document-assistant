"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { getAuthToken, getMe, loginUser, registerUser, setAuthToken } from "@/lib/api";
import type { UserRecord } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<UserRecord | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const u = await getMe();
      setUser(u);
    } catch {
      setAuthToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, pass: string) => {
      const res = await loginUser({ email, password: pass });
      setAuthToken(res.access_token);
      setUser(res.user);
      toast.success(`Logged in as ${res.user.email}`);
      return res.user;
    },
    []
  );

  const register = useCallback(
    async (email: string, pass: string) => {
      const res = await registerUser({ email, password: pass });
      setAuthToken(res.access_token);
      setUser(res.user);
      toast.success(`Registered successfully as ${res.user.email}`);
      return res.user;
    },
    []
  );

  const logout = useCallback(() => {
    setAuthToken(null);
    setUser(null);
    toast.info("Logged out");
  }, []);

  return {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
  };
}
