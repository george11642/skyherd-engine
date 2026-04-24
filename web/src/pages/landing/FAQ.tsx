import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const faqs = [
  {
    question: "Do I need to fly it?",
    answer:
      "No. SkyHerd is fully autonomous. Once deployed, the drones operate on their own — taking off, patrolling, herding, and returning to charge without any pilot input. You just check the app when you want updates.",
  },
  {
    question: "What about FAA regulations?",
    answer:
      "We handle all of it. SkyHerd operates under Part 107 with the appropriate waivers for autonomous and beyond-visual-line-of-sight operations. Our team manages all compliance, permitting, and reporting so you don't have to think about it.",
  },
  {
    question: "How big of a ranch can it cover?",
    answer:
      "A single SkyHerd unit covers up to 10,000 acres. For larger operations, we deploy multiple units that coordinate with each other. During our initial consultation, we'll map your property and recommend the right configuration.",
  },
  {
    question: "What happens if it breaks?",
    answer:
      "We replace it — no extra charge. Hardware maintenance and replacement are included in your monthly subscription. If a drone goes down, we ship a replacement and get you back online as fast as possible.",
  },
  {
    question: "How does it handle weather?",
    answer:
      "SkyHerd drones are rated for high winds, dust, and rain — the kind of conditions that are just another Tuesday out here. In severe weather (thunderstorms, hail), the system auto-returns to its base station and resumes operations when conditions clear.",
  },
];

interface FAQItemProps {
  question: string;
  answer: string;
  isOpen: boolean;
  onToggle: () => void;
}

function FAQItem({ question, answer, isOpen, onToggle }: FAQItemProps) {
  return (
    <div className="border-b border-slate-800 last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex items-center justify-between w-full py-5 text-left cursor-pointer"
      >
        <span className="text-base font-medium text-slate-200 pr-4">
          {question}
        </span>
        <motion.svg
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="w-5 h-5 text-slate-500 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </motion.svg>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <p className="text-sm text-slate-400 leading-relaxed pb-5">
              {answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="relative py-24 sm:py-32 bg-slate-900/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-sm font-semibold text-amber-500 uppercase tracking-wider mb-3">
            FAQ
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 tracking-tight">
            Common questions
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="max-w-2xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/50 px-6 sm:px-8"
        >
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              question={faq.question}
              answer={faq.answer}
              isOpen={openIndex === index}
              onToggle={() =>
                setOpenIndex(openIndex === index ? null : index)
              }
            />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
