import { motion } from "framer-motion";

const steps = [
  {
    number: "01",
    title: "We deploy SkyHerd drones on your ranch",
    description:
      "Our team visits your property, maps the terrain, and installs your drone system. No hardware cost, no complicated setup. We handle everything.",
    icon: (
      <svg
        className="w-10 h-10"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  },
  {
    number: "02",
    title: "They herd, monitor, and patrol — 24/7",
    description:
      "SkyHerd drones autonomously move livestock, scan for health issues, and patrol for predators around the clock. No pilot needed.",
    icon: (
      <svg
        className="w-10 h-10"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
    ),
  },
  {
    number: "03",
    title: "You manage everything from your phone",
    description:
      "Check on your herd, review health alerts, see patrol reports, and adjust priorities — all from a simple app on your phone.",
    icon: (
      <svg
        className="w-10 h-10"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
        />
      </svg>
    ),
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" as const },
  },
};

export default function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative py-24 sm:py-32 bg-slate-900/30"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-3">
            Simple Setup
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
            How it works
          </h2>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-60px" }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12"
        >
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              variants={itemVariants}
              className="relative flex flex-col items-center text-center"
            >
              {/* Connector line (desktop only) */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-12 left-[60%] w-[calc(100%-20%)] h-px bg-gradient-to-r from-amber-600/40 to-amber-600/10" />
              )}

              {/* Icon circle */}
              <div className="relative w-24 h-24 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-amber-500 mb-6">
                {step.icon}
                <span className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-amber-600 text-white text-xs font-bold flex items-center justify-center">
                  {step.number}
                </span>
              </div>

              <h3 className="text-lg font-semibold text-slate-100 mb-3">
                {step.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
                {step.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
