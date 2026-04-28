export default function IndustryPills() {
  const industries = ["Education", "Construction", "Pharma", "Healthcare"];

  return (
    <div className="py-8">
      <p className="text-center text-xs text-slate-400 mb-3">Built for</p>
      <div className="flex flex-wrap justify-center gap-3">
        {industries.map((industry) => (
          <span
            key={industry}
            className="rounded-full border border-slate-700 px-4 py-1.5 text-sm text-slate-300 transition-colors hover:border-violet-500 hover:text-white"
          >
            {industry}
          </span>
        ))}
      </div>
    </div>
  );
}
