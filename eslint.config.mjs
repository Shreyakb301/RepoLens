import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores(["backend/**", "dist/**", "node_modules/**", "build/**"]),
  js.configs.recommended,
  ...tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
  },
  {
    // Node-side files: the Vite config and the build tests.
    files: ["*.ts", "*.mjs", "tests/**/*.mjs"],
    languageOptions: { globals: globals.node },
  },
]);
