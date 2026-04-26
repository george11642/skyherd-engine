import { motion } from "framer-motion";
import Navbar from "./Navbar";
import Hero from "./Hero";
import Problem from "./Problem";
import HowItWorks from "./HowItWorks";
import Capabilities from "./Capabilities";
import AgentMesh from "./AgentMesh";
import Southwest from "./Southwest";
import Pricing from "./Pricing";
import FAQ from "./FAQ";
import WaitlistForm from "./WaitlistForm";
import Footer from "./Footer";

/**
 * Landing page composition — Phase 1 of the skyheard-into-skyherd-engine port.
 *
 * Section order (per plan + Phase 5 LandingPage test):
 *   Navbar → Hero → Problem → HowItWorks → Capabilities → Southwest
 *     → Pricing → FAQ → WaitlistForm → Footer
 *
 * Everything is wrapped in `.landing-root` so landing-only CSS tokens in
 * index.css (`/* landing *\/` block) stay scoped and do not collide with the
 * ops-console palette on `/demo`.
 */
export default function LandingPage() {
  return (
    <div className="landing-root">
      <Navbar />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Capabilities />
        <AgentMesh />
        <Southwest />
        <Pricing />
        <FAQ />

        {/* Standalone waitlist section — region landmark for a11y + tests */}
        <section
          id="waitlist"
          aria-label="Waitlist"
          className="relative py-24 sm:py-32"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6 }}
              className="text-center mb-12"
            >
              <h2
                id="waitlist-heading"
                className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight mb-4"
              >
                Ready to let your ranch run itself?
              </h2>
              <p className="text-lg text-slate-400 mb-8 max-w-xl mx-auto">
                Join the waitlist and be the first to know when SkyHerd is
                available in your area.
              </p>
              <div className="flex justify-center">
                <WaitlistForm variant="footer" />
              </div>
            </motion.div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
