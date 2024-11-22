module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-recommended", // Or "vue/recommended" for Vue 2
    "prettier" // Ensures ESLint and Prettier work together
  ],
  plugins: ["vue", "simple-import-sort"],
  rules: {
    "simple-import-sort/imports": "error",
    "simple-import-sort/exports": "error"
  }
};
