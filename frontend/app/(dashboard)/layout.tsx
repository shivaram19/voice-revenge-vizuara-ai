"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Users, PhoneCall, Settings, Bell, Search, LogOut } from "lucide-react";
import { getSession, signOut, type MockSession } from "@/lib/mock-auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<MockSession | null>(null);

  useEffect(() => {
    const s = getSession();
    if (!s) {
      router.push("/login");
      return;
    }
    setSession(s);
  }, [router]);

  const handleSignOut = () => {
    signOut();
    router.push("/login");
  };

  const navItems = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Students", href: "/students", icon: Users },
    { name: "Live Calls", href: "/calls", icon: PhoneCall },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const user = session?.user;
  const avatarSeed = user?.user_metadata.avatar_seed ?? "Principal";
  const fullName = user?.user_metadata.full_name ?? "Administrator";
  const school = user?.user_metadata.school ?? "Your School";

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden selection:bg-indigo-500/30">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col bg-slate-900 border-r border-slate-800 transition-all">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            V
          </div>
          <span className="font-bold text-lg tracking-tight text-white">VoiceCRM</span>
        </div>

        <div className="px-4 pb-6">
          <div className="bg-slate-950/50 rounded-xl p-3 border border-slate-800/50">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">Active Tenant</p>
            <p className="font-medium text-sm text-slate-200 truncate">{school}</p>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-[inset_0_0_12px_rgba(99,102,241,0.05)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User profile + logout */}
        <div className="p-4 mt-auto border-t border-slate-800/60">
          {user && (
            <div className="flex items-center gap-3 px-2 py-2 mb-2">
              <img
                src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${avatarSeed}`}
                alt={fullName}
                className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 shrink-0"
              />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{fullName}</p>
                <p className="text-xs text-slate-500 truncate">{user.email}</p>
              </div>
            </div>
          )}
          <button
            id="signout-btn"
            onClick={handleSignOut}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Subtle background glow */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />

        {/* Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md z-10">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-full px-4 py-1.5 w-80 focus-within:border-indigo-500/50 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all">
            <Search className="w-4 h-4 text-slate-500 mr-2" />
            <input
              type="text"
              placeholder="Search students, calls..."
              className="bg-transparent border-none outline-none text-sm w-full text-slate-200 placeholder:text-slate-500"
            />
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-full hover:bg-slate-800">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full ring-2 ring-slate-950"></span>
            </button>
            <img
              src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${avatarSeed}`}
              alt={fullName}
              className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 cursor-pointer hover:ring-2 hover:ring-indigo-500/50 transition-all"
              title={fullName}
            />
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-8 z-10">
          <div className="max-w-6xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
