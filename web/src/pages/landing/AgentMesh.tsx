import { motion } from "framer-motion";

/**
 * AgentMesh — names the five Managed Agents that run the ranch.
 *
 * Surfaces the Opus 4.7 / Claude Managed Agents stack in the marketing copy
 * so a hackathon judge can see the mesh is real before they hit /demo.
 * Sits between Capabilities and Southwest in the LandingPage composition.
 */

const agents = [
  {
    name: "FenceLineDispatcher",
    description:
      "Classifies thermal-camera intrusions and dispatches the drone.",
  },
  {
    name: "HerdHealthWatcher",
    description: "Per-animal anomaly detection from camera feeds.",
  },
  {
    name: "PredatorPatternLearner",
    description: "Learns multi-day predator crossing patterns.",
  },
  {
    name: "GrazingOptimizer",
    description: "Proposes weekly paddock rotation.",
  },
  {
    name: "CalvingWatch",
    description: "Seasonal labor monitoring with priority paging.",
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.08,
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

export default function AgentMesh() {
  return (
    <section
      id="agent-mesh"
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
            The 5-Agent Mesh
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
            Five Managed Agents on Opus 4.7. One ranch nervous system.
          </h2>
          <p className="mt-4 text-lg text-slate-400 max-w-2xl mx-auto">
            Each agent owns one job and pages the rancher only when it counts.
            They share memory, pause when idle, and keep the bill small.
          </p>
        </motion.div>

        <motion.ul
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-60px" }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6"
        >
          {agents.map((agent) => (
            <motion.li
              key={agent.name}
              variants={cardVariants}
              className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 hover:bg-slate-800/50 transition-colors duration-300"
            >
              <p className="font-mono text-sm font-semibold text-amber-400 mb-2">
                {agent.name}
              </p>
              <p className="text-sm text-slate-400 leading-relaxed">
                {agent.description}
              </p>
            </motion.li>
          ))}
        </motion.ul>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-center text-sm text-slate-500 mt-10 max-w-2xl mx-auto"
        >
          Every drone action is signed and logged to a tamper-evident ledger.
          Replay any day from a seed.
        </motion.p>
      </div>
    </section>
  );
}
