/** Corporate Trust design tokens -- see docs/INITIAL_ARCHITECTURE_ASSESSMENT.md
 * and the product brief section 13. Centralized here; components should
 * reference these token names rather than hard-coding hex values. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F8FAFC",
        surface: "#FFFFFF",
        primary: {
          DEFAULT: "#4F46E5",
          hover: "#4338CA",
        },
        secondary: "#7C3AED",
        text: "#0F172A",
        muted: "#64748B",
        success: "#10B981",
        warning: "#D97706",
        danger: "#DC2626",
        border: "#E2E8F0",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      fontWeight: {
        display: "800",
        heading: "700",
        subheading: "600",
        label: "500",
        body: "400",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.06)",
        "card-hover": "0 2px 4px rgba(15, 23, 42, 0.06), 0 12px 24px rgba(79, 70, 229, 0.10)",
        primary: "0 8px 24px rgba(79, 70, 229, 0.25)",
      },
      borderRadius: {
        card: "16px",
      },
    },
  },
  plugins: [],
};
