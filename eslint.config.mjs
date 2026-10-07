import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
      "**/build/**",
      "**/next-env.d.ts",
      ".opencode/**",
      "docs/**",
    ],
  },
  ...tseslint.configs.recommended,
);
