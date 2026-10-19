import { Architecture } from "@/components/landing/Architecture";
import { EvaluationPreview } from "@/components/landing/EvaluationPreview";
import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";
import { Hero } from "@/components/landing/Hero";
import { Navbar } from "@/components/landing/Navbar";
import { Pillars } from "@/components/landing/Pillars";

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Pillars />
        <Features />
        <Architecture />
        <EvaluationPreview />
      </main>
      <Footer />
    </>
  );
}
