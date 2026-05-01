"use client";

import { Activity, PhoneOutgoing, CheckCircle2, AlertCircle, Clock } from "lucide-react";

export default function DashboardOverviewPage() {
  const stats = [
    { title: "Total Calls Today", value: "142", icon: PhoneOutgoing, trend: "+12%", trendUp: true },
    { title: "Successful Contacts", value: "128", icon: CheckCircle2, trend: "+8%", trendUp: true },
    { title: "Failed / Voicemail", value: "14", icon: AlertCircle, trend: "-2%", trendUp: false },
    { title: "Active AI Agents", value: "3", icon: Activity, trend: "Optimal", trendUp: true },
  ];

  const recentCalls = [
    { id: 1, student: "Emma Thompson", type: "Absence Follow-up", status: "completed", time: "2m ago", duration: "1m 24s" },
    { id: 2, student: "James Wilson", type: "Fee Reminder", status: "failed", time: "15m ago", duration: "0m 45s" },
    { id: 3, student: "Sophia Martinez", type: "Event Announcement", status: "completed", time: "1h ago", duration: "2m 10s" },
    { id: 4, student: "Liam Garcia", type: "Absence Follow-up", status: "completed", time: "2h ago", duration: "1m 55s" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard Overview</h1>
        <p className="text-slate-400 mt-1">Monitor your school's automated voice outreach.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-colors">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Icon className="w-16 h-16 text-indigo-500" />
              </div>
              <div className="flex justify-between items-start mb-4 relative z-10">
                <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                  <Icon className="w-5 h-5 text-indigo-400" />
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${stat.trendUp ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                  {stat.trend}
                </span>
              </div>
              <div className="relative z-10">
                <h3 className="text-3xl font-bold text-white mb-1">{stat.value}</h3>
                <p className="text-sm text-slate-400 font-medium">{stat.title}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl shadow-sm flex flex-col">
          <div className="p-5 border-b border-slate-800/60 flex justify-between items-center">
            <h2 className="font-semibold text-white">Recent AI Calls</h2>
            <button className="text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors">View All</button>
          </div>
          <div className="flex-1 p-5">
            <div className="space-y-4">
              {recentCalls.map((call) => (
                <div key={call.id} className="flex items-center justify-between p-4 rounded-lg bg-slate-950/50 border border-slate-800/50 hover:bg-slate-800/50 transition-colors group">
                  <div className="flex items-center gap-4">
                    <div className={`w-2 h-2 rounded-full ${call.status === 'completed' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                    <div>
                      <p className="font-medium text-slate-200">{call.student}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{call.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm text-slate-400">
                    <div className="flex items-center gap-1.5 hidden sm:flex">
                      <Clock className="w-4 h-4" />
                      {call.duration}
                    </div>
                    <div className="w-20 text-right">
                      {call.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Actions & System Status */}
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border border-indigo-500/20 rounded-xl p-6 relative overflow-hidden">
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-500/20 blur-[40px] rounded-full"></div>
            <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
            <div className="space-y-3 relative z-10">
              <button className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-sm transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2">
                <PhoneOutgoing className="w-4 h-4" />
                Initiate Broadcast
              </button>
              <button className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg font-medium text-sm transition-colors">
                Add Student Contact
              </button>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="font-semibold text-white mb-4">System Status</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-400">Telephony Gateway</span>
                <span className="text-xs font-medium px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded-full flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                  Operational
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-400">AI Latency</span>
                <span className="text-sm text-slate-200 font-medium">850ms</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-400">Daily Quota</span>
                <div className="w-1/2 flex items-center gap-3">
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 w-[14%]"></div>
                  </div>
                  <span className="text-xs text-slate-500">14%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
