import Hero from "../components/Hero";
import IndustryPills from "../components/IndustryPills";
import Footer from "../components/Footer";

export default function HomePage() {
  return (
    <main className="min-h-screen relative overflow-hidden bg-slate-950 text-white">
      <div className="gradient-bg absolute inset-0 -z-10" />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <Hero />
        <IndustryPills />
        <Footer />
      </div>
    </main>
  );
}
