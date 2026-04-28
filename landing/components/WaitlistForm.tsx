"use client";

import { useState } from "react";

export default function WaitlistForm() {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Waitlist submission:", email);
    setEmail("");
  };

  return (
    <div className="w-full max-w-md mx-auto py-8">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col sm:flex-row gap-0"
      >
        <input
          type="email"
          required
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 rounded-lg sm:rounded-r-none bg-slate-800 border border-slate-700 text-white placeholder-slate-400 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
        <button
          type="submit"
          className="bg-violet-600 hover:bg-violet-500 text-white font-medium px-6 py-3 rounded-lg sm:rounded-l-none transition mt-2 sm:mt-0"
        >
          Join the Waitlist
        </button>
      </form>
    </div>
  );
}
