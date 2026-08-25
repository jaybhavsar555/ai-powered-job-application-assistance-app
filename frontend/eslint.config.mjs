import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Must ignore build/cache artifacts — nested frontend/.next was committed once
  // and CI was linting Turbopack chunks (zustand, findDOMNode, etc.).
  globalIgnores([
    ".next/**",
    "frontend/**",
    "out/**",
    "build/**",
    "dist/**",
    "coverage/**",
    "next-env.d.ts",
    "node_modules/**",
    "playwright-report/**",
    "test-results/**",
  ]),
  {
    rules: {
      // React Compiler rules are too noisy for common mount-fetch / URL sync patterns.
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/purity": "off",
      "react-hooks/preserve-manual-memoization": "off",
    },
  },
]);

export default eslintConfig;
