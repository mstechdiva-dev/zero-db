const PLANS = [
  {
    name: "Solo",
    price: "$19",
    period: "/mo",
    description: "For solo developers who need to stay on top of schema changes.",
    features: [
      "1 seat",
      "1 connected database",
      "Full impact analysis",
      "Slack + email alerts",
      "14-day free trial",
    ],
    cta: "Start free trial",
    href: "/auth/signup",
    highlight: true,
  },
  {
    name: "Teams",
    price: "Custom",
    period: "",
    description: "For engineering teams with multiple databases and members.",
    features: [
      "Multiple seats",
      "Multiple databases",
      "PagerDuty integration",
      "Priority support",
      "14-day free trial",
    ],
    cta: "Talk to us",
    href: "/auth/signup",
    highlight: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations with compliance and security requirements.",
    features: [
      "VPC peering",
      "SSO / SAML",
      "SOC 2 Type II",
      "Dedicated SLA",
      "Custom onboarding",
    ],
    cta: "Talk to us",
    href: "/auth/signup",
    highlight: false,
  },
];

export default function Pricing() {
  return (
    <div className="pt-16 pb-12">
      <h2 className="text-3xl font-bold text-white mb-4">Pricing</h2>
      <p className="text-gray-400 mb-12 text-lg">
        All plans include a 14-day free trial. No credit card required.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`bg-[#111] border rounded-xl p-6 flex flex-col ${
              plan.highlight
                ? "border-[#00e87a]"
                : "border-gray-800"
            }`}
          >
            {plan.highlight && (
              <span className="text-xs font-bold text-[#00e87a] font-mono uppercase tracking-widest mb-4">
                Most popular
              </span>
            )}
            <h3 className="text-white font-bold text-xl">{plan.name}</h3>
            <div className="mt-2 flex items-end gap-1">
              <span className="text-4xl font-bold text-white">{plan.price}</span>
              {plan.period && (
                <span className="text-gray-400 mb-1">{plan.period}</span>
              )}
            </div>
            <p className="text-gray-400 text-sm mt-3">{plan.description}</p>
            <ul className="mt-6 space-y-2 flex-1">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm text-gray-300">
                  <span className="text-[#00e87a]">✓</span>
                  {feature}
                </li>
              ))}
            </ul>
            <a
              href={plan.href}
              className={`mt-8 block text-center px-4 py-3 font-semibold rounded-lg transition-colors text-sm ${
                plan.highlight
                  ? "bg-[#00e87a] text-black hover:bg-[#00c96a]"
                  : "border border-gray-700 text-white hover:border-gray-500"
              }`}
            >
              {plan.cta}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
