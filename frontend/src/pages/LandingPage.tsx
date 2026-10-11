import { FlowVisual } from "../components/Landing/FlowVisual";
import { Footer } from "../components/Landing/Footer";
import { Hero } from "../components/Landing/Hero";
import { Pillars } from "../components/Landing/Pillars";
import { Pricing } from "../components/Landing/Pricing";
import { ProblemSolution } from "../components/Landing/ProblemSolution";
import { Testimonials } from "../components/Landing/Testimonials";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <ProblemSolution />
      <Pillars />
      <FlowVisual />
      <Testimonials />
      <Pricing />
      <Footer />
    </>
  );
}
