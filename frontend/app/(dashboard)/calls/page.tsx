"use client";

import { useState, useEffect } from "react";
import { Mic, MicOff, PhoneOff, Activity, AlertCircle } from "lucide-react";
import { listActiveCalls, createCallsWebSocket, type ActiveCall, type WSMessage } from "@/lib/api";

export default function LiveCallsPage() {
  const [activeCalls, setActiveCalls] = useState<ActiveCall[]>([]);
  const [selectedCall, setSelectedCall] = useState<ActiveCall | null>(null);
  const [transcript, setTranscript] = useState<any[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  // Load active calls on mount
  useEffect(() => {
    async function load() {
      try {
        const calls = await listActiveCalls();
        setActiveCalls(calls);
        if (calls.length > 0 && !selectedCall) {
          setSelectedCall(calls[0]);
        }
      } catch (e) {
        console.error("Failed to load active calls", e);
      }
    }
    load();
  }, [selectedCall]);

  // WebSocket for live updates
  useEffect(() => {
    const ws = createCallsWebSocket(
      (msg: WSMessage) => {
        if (msg.event === "call_started") {
          setActiveCalls((prev) => [...prev.filter((c) => c.call_sid !== msg.payload.call_sid), msg.payload]);
        } else if (msg.event === "call_ended") {
          setActiveCalls((prev) => prev.filter((c) => c.call_sid !== msg.payload.call_sid));
          if (selectedCall?.call_sid === msg.payload.call_sid) {
            setSelectedCall(null);
          }
        } else if (msg.event === "transcript") {
          setTranscript((prev) => [...prev, msg.payload]);
        }
      },
      () => setWsConnected(true),
      () => setWsConnected(false)
    );

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [selectedCall?.call_sid]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Live Calls</h1>
          <p className="text-slate-400 mt-1">Real-time observability of your AI agents.</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1.5 border rounded-full text-sm font-medium ${wsConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}>
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
          {wsConnected ? "WebSocket Connected" : "Connecting..."}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Active Calls List */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800/60 bg-slate-900 flex justify-between items-center">
            <h2 className="font-medium text-slate-200">Active Streams</h2>
            <span className="bg-indigo-500/20 text-indigo-400 text-xs px-2 py-0.5 rounded-full font-medium">{activeCalls.length} Active</span>
          </div>
          <div className="p-4 flex-1 overflow-y-auto">
            {activeCalls.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-500">
                <Activity className="w-8 h-8 mb-2 opacity-50" />
                <p className="text-sm">No active calls right now</p>
              </div>
            )}
            {activeCalls.map((call) => (
              <div
                key={call.call_sid}
                onClick={() => {
                  setSelectedCall(call);
                  setTranscript([]);
                }}
                className={`p-4 rounded-xl border cursor-pointer transition-colors mb-3 ${
                  selectedCall?.call_sid === call.call_sid
                    ? "border-indigo-500/30 bg-indigo-500/5"
                    : "border-slate-800 bg-slate-950/30 hover:bg-slate-800/50"
                }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-white">{call.student_name || "Unknown Student"}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Contact: {call.parent_name || "N/A"}</p>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded text-xs font-medium">
                    <Activity className="w-3 h-3 animate-pulse" />
                    {Math.floor(call.duration_seconds / 60).toString().padStart(2, "0")}:
                    {(call.duration_seconds % 60).toString().padStart(2, "0")}
                  </div>
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  {call.call_type}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Transcript Panel */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          {selectedCall ? (
            <>
              {/* Transcript Header */}
              <div className="p-4 border-b border-slate-800/60 flex justify-between items-center bg-slate-950/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
                    <Activity className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-white">Observing: {selectedCall.student_name || "Unknown"}</h2>
                    <p className="text-xs text-slate-400">Agent: School Receptionist v2</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors" title="Takeover Call">
                    <Mic className="w-4 h-4" />
                  </button>
                  <button className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors" title="Terminate Call">
                    <PhoneOff className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Transcript Stream */}
              <div className="flex-1 p-6 overflow-y-auto space-y-6">
                {transcript.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500">
                    <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                    <p className="text-sm">Waiting for transcript...</p>
                  </div>
                )}
                {transcript.map((msg, i) => (
                  <div key={i} className={`flex flex-col max-w-[80%] ${msg.speaker === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}>
                    <div className="flex items-baseline gap-2 mb-1 px-1">
                      <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                        {msg.speaker === 'agent' ? 'AI Receptionist' : selectedCall.parent_name || "Parent"}
                      </span>
                      <span className="text-[10px] text-slate-500">{msg.time || new Date().toLocaleTimeString()}</span>
                    </div>
                    <div className={`p-4 rounded-2xl ${msg.speaker === 'user' ? 'bg-indigo-600 text-white rounded-tr-sm' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm'}`}>
                      <p className="text-sm leading-relaxed">{msg.text}</p>
                    </div>
                  </div>
                ))}
                {transcript.length > 0 && (
                  <div className="flex items-center gap-2 text-slate-500 text-sm italic ml-2">
                    <div className="flex space-x-1">
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                    </div>
                    User is speaking...
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500">
              <p className="text-sm">Select a call to view transcript</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
