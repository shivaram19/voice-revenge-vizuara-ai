/**
 * mock-auth.ts
 * ============
 * Lightweight mock that mirrors the Supabase Auth API surface used in this
 * project. Stores session state in localStorage so page refreshes persist.
 *
 * Mock credentials
 * ----------------
 *  Email    : admin@school.edu
 *  Password : password123
 *
 * Replace this module with the real @supabase/ssr client once a Supabase
 * project is provisioned and NEXT_PUBLIC_SUPABASE_URL is set correctly.
 */

const SESSION_KEY = "mock_auth_session";

export type MockUser = {
  id: string;
  email: string;
  user_metadata: {
    full_name: string;
    role: string;
    school: string;
    avatar_seed: string;
  };
};

export type MockSession = {
  user: MockUser;
  access_token: string;
  expires_at: number; // unix timestamp
};

/** Seed accounts for local development / demo */
const MOCK_ACCOUNTS: Array<{ email: string; password: string; user: MockUser }> =
  [
    {
      email: "admin@school.edu",
      password: "password123",
      user: {
        id: "mock-user-001",
        email: "admin@school.edu",
        user_metadata: {
          full_name: "Dr. Sarah Mitchell",
          role: "Principal",
          school: "Lincoln High School",
          avatar_seed: "Principal",
        },
      },
    },
    {
      email: "teacher@school.edu",
      password: "password123",
      user: {
        id: "mock-user-002",
        email: "teacher@school.edu",
        user_metadata: {
          full_name: "Mr. James Okafor",
          role: "Teacher",
          school: "Lincoln High School",
          avatar_seed: "Teacher",
        },
      },
    },
  ];

// --------------------------------------------------------------------------
// Auth helpers
// --------------------------------------------------------------------------

export function signInWithPassword(
  email: string,
  password: string
): { data: { session: MockSession; user: MockUser } | null; error: { message: string } | null } {
  const account = MOCK_ACCOUNTS.find(
    (a) => a.email.toLowerCase() === email.toLowerCase() && a.password === password
  );

  if (!account) {
    return { data: null, error: { message: "Invalid email or password." } };
  }

  const session: MockSession = {
    user: account.user,
    access_token: `mock-token-${Date.now()}`,
    expires_at: Math.floor(Date.now() / 1000) + 60 * 60 * 8, // 8 hours
  };

  if (typeof window !== "undefined") {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  return { data: { session, user: account.user }, error: null };
}

export function getSession(): MockSession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const session: MockSession = JSON.parse(raw);
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
}

export function isAuthenticated(): boolean {
  return getSession() !== null;
}
