module.exports = {
  testEnvironment: "jsdom",
  testMatch: ["<rootDir>/tests/**/*.test.ts", "<rootDir>/tests/**/*.test.tsx"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.ts"],
  transform: {"^.+\\.[jt]sx?$": "babel-jest"},
  moduleNameMapper: {"\\.css$": "<rootDir>/tests/style.cjs"},
  collectCoverageFrom: ["src/**/*.{ts,tsx,js,jsx}"],
  coverageReporters: ["text", "json", "lcov"],
  coverageThreshold: {global: {statements: 100, branches: 100, functions: 100, lines: 100}, "./src/**/*.{ts,tsx}": {statements: 100, branches: 100, functions: 100, lines: 100}},
};
