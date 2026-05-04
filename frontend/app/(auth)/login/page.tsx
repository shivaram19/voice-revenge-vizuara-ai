"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signInWithPassword } from "@/lib/auth";
import { Eye, EyeOff, Zap, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    // Simulate a brief network delay for realism
    await new Promise((r) => setTimeout(r, 600));

    const { data, error: authError } = signInWithPassword(email, password);

    if (authError || !data) {
      setError(authError?.message ?? "Authentication failed.");
      setIsLoading(false);
      return;
    }

    // Redirect based on mock session
    router.push("/dashboard");
  };

  const fillDemoCredentials = () => {
    setEmail("admin@school.edu");
    setPassword("password123");
    setError("");
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-600/8 blur-[100px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md px-6 z-10">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-lg shadow-lg shadow-indigo-500/30">
            V
          </div>
          <span className="font-bold text-xl tracking-tight text-white">VoiceCRM</span>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-1 tracking-tight">Welcome back</h1>
          <p className="text-slate-400 text-sm mb-7">
            Sign in to your school's command center.
          </p>

          {/* Mock mode banner */}
          <div className="flex items-start gap-3 p-3 mb-6 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <Zap className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div className="text-xs text-amber-300/90 leading-relaxed">
              <span className="font-semibold text-amber-400">Mock Mode Active</span> — Supabase not connected.{" "}
              <button
                type="button"
                onClick={fillDemoCredentials}
                className="underline underline-offset-2 hover:text-amber-200 transition-colors font-medium"
              >
                Use demo credentials
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 mb-5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950/70 border border-slate-700/60 rounded-lg px-4 py-3 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500/50 transition-all"
                placeholder="admin@school.edu"
                autoComplete="email"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950/70 border border-slate-700/60 rounded-lg px-4 py-3 pr-11 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/70 focus:border-indigo-500/50 transition-all"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 relative bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-all duration-200 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 overflow-hidden group"
            >
              <span className={`transition-opacity duration-200 ${isLoading ? "opacity-0" : "opacity-100"}`}>
                Sign In
              </span>
              {isLoading && (
                <span className="absolute inset-0 flex items-center justify-center">
                  <svg className="animate-spin w-5 h-5 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                  </svg>
                </span>
              )}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-6 p-4 bg-slate-950/60 rounded-lg border border-slate-800/60">
            <p className="text-xs text-slate-500 font-medium mb-2 uppercase tracking-wider">
              Demo credentials
            </p>
            <div className="space-y-1 font-mono text-xs text-slate-400">
              <div className="flex gap-2">
                <span className="text-slate-600 w-16">Email</span>
                <span className="text-slate-300">admin@school.edu</span>
              </div>
              <div className="flex gap-2">
                <span className="text-slate-600 w-16">Password</span>
                <span className="text-slate-300">password123</span>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          Don&apos;t have an account?{" "}
          <a href="/register" className="text-indigo-400 hover:text-indigo-300 transition-colors">
            Register here
          </a>
        </p>
      </div>
    </div>
  );
}
