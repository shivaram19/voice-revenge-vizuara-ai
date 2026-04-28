import WaitlistForm from "./WaitlistForm";

export default function Hero() {
  return (
    <section className="flex flex-col items-center justify-center text-center py-24 px-4 max-w-4xl mx-auto">
      <p className="text-sm font-medium tracking-widest uppercase text-slate-400 mb-4">
        TRAYINI
      </p>
      <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
        Infrastructure for Enterprise Voice Agents
      </h1>
      <p className="text-lg md:text-xl text-slate-300 mb-10 max-w-2xl">
        Secure, scalable voice AI built for Education, Construction, Pharma, and Healthcare.
      </p>
      <WaitlistForm />
    </section>
  );
}
