import { motion } from "framer-motion";

export default function Pricing() {
  return (
    <section id="pricing" className="relative py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-3">
            Pricing
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
            Straightforward. No surprises.
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="max-w-2xl mx-auto"
        >
          <div className="relative rounded-2xl border border-amber-600/30 bg-gradient-to-b from-slate-900 to-slate-900/80 p-8 sm:p-10">
            {/* Badge */}
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="inline-block rounded-full bg-amber-600 px-4 py-1 text-xs font-semibold text-white">
                Drone-as-a-Service
              </span>
            </div>

            <div className="text-center mb-8 pt-2">
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-5xl sm:text-6xl font-bold text-slate-100">
                  $2,500
                </span>
                <span className="text-lg text-slate-400">/month</span>
              </div>
              <p className="text-slate-400 mt-3">
                No upfront hardware cost. Cancel anytime.
              </p>
            </div>

            <div className="border-t border-slate-800 pt-6 mb-8">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
                What&apos;s included
              </h3>
              <ul className="space-y-3">
                {[
                  "Full drone hardware — deployed and maintained by us",
                  "Autonomous herding, health monitoring, and predator patrols",
                  "Mobile app with real-time alerts and reporting",
                  "All FAA compliance and permitting handled",
                  "Hardware replacement if anything breaks",
                  "Dedicated support from our ranch ops team",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <svg
                      className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span className="text-sm text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Comparison */}
            <div className="rounded-xl bg-slate-800/50 border border-slate-700/50 p-5 mb-8">
              <p className="text-sm font-medium text-slate-300 mb-2">
                Compare that to helicopter herding:
              </p>
              <p className="text-2xl font-bold text-slate-400 line-through">
                $8,000 - $15,000
                <span className="text-sm font-normal ml-2 no-underline">
                  /season
                </span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Plus the stress it puts on your cattle.
              </p>
            </div>

            <a
              href="#waitlist"
              className="block w-full rounded-lg bg-amber-600 px-6 py-3.5 text-center text-sm font-semibold text-white hover:bg-amber-500 transition-colors duration-200"
            >
              Talk to Us
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
