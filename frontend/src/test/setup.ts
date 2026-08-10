import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import i18n from "../i18n";

// Deterministic regardless of the machine's locale or a previously stored
// language preference in localStorage (jsdom persists it across test files).
void i18n.changeLanguage("en");

afterEach(() => {
  cleanup();
});
