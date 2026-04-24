import { motion } from "framer-motion";

const capabilities = [
  {
    title: "Move Your Herd Without the Stress",
    description:
      "Gentle acoustic herding moves cattle exactly where you need them — no helicopters roaring overhead, no dogs nipping at heels. Less stress means better weight gain and healthier animals.",
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.536a5 5 0 001.414 1.414m-2.828-9.9a9 9 0 000 12.728"
        />
        <circle
          cx="12"
          cy="12"
          r="2"
          stroke="currentColor"
          strokeWidth={1.5}
        />
      </svg>
    ),
    color: "amber",
  },
  {
    title: "Spot Sick Animals Before It Spreads",
    description:
      "Thermal imaging and behavior analysis catch early signs of illness — limping, isolation, fever — before it becomes an outbreak. Early detection saves you thousands in vet bills and lost stock.",
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
        />
      </svg>
    ),
    color: "green",
  },
  {
    title: "Keep Predators Away All Night",
    description:
      "Autonomous night patrols use light and sound deterrents to keep coyotes, mountain lions, and wolves away from your herd. Protection that never sleeps, never takes a night off.",
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        />
      </svg>
    ),
    color: "amber",
  },
  {
    title: "Earn Carbon Credits From Your Land",
    description:
      "SkyHerd maps your pasture health and grazing patterns to help you qualify for carbon credit programs. Get paid for the sustainable grazing you're already doing.",
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    color: "green",
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

export default function Capabilities() {
  return (
    <section id="capabilities" className="relative py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-3">
            Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
            Everything your ranch needs in the sky
          </h2>
          <p className="mt-4 text-lg text-slate-400 max-w-2xl mx-auto">
            Four core systems working together to keep your operation running
            smooth.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-60px" }}
          className="grid grid-cols-1 sm:grid-cols-2 gap-6 lg:gap-8"
        >
          {capabilities.map((cap) => (
            <motion.div
              key={cap.title}
              variants={cardVariants}
              className="group relative p-6 sm:p-8 rounded-2xl border border-slate-800 bg-slate-900/40 hover:bg-slate-800/50 transition-colors duration-300"
            >
              <div
                className={`w-14 h-14 rounded-xl flex items-center justify-center mb-5 ${
                  cap.color === "green"
                    ? "bg-green-600/10 text-green-500"
                    : "bg-amber-600/10 text-amber-500"
                }`}
              >
                {cap.icon}
              </div>
              <h3 className="text-xl font-semibold text-slate-100 mb-3">
                {cap.title}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {cap.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
