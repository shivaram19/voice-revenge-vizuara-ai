/**
 * Auth module — real backend API wrapper
 * Mirrors the mock-auth.ts interface so pages can swap imports easily.
 */

import { login as apiLogin, logout as apiLogout, getSession as apiGetSession } from "@/lib/api";
import type { GatewayUser, GatewaySession } from "@/lib/api";

export type { GatewayUser as MockUser, GatewaySession as MockSession };

const SESSION_KEY = "mock_auth_session";

export async function signInWithPassword(
  email: string,
  password: string
): Promise<{ data: { session: GatewaySession; user: GatewayUser } | null; error: { message: string } | null }> {
  const result = await apiLogin(email, password);
  if (!result) {
    return { data: null, error: { message: "Invalid email or password." } };
  }
  return {
    data: { session: result.session, user: result.user },
    error: null,
  };
}

export function getSession(): GatewaySession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const session: GatewaySession = JSON.parse(raw);
    if (session.expires_at < Math.floor(Date.now() / 1000)) {
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function signOut(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(SESSION_KEY);
  }
  // Fire-and-forget backend logout
  apiLogout().catch(() => {});
}

export function isAuthenticated(): boolean {
  return getSession() !== null;
}
