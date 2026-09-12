import { htmlInjectionProtection, getDaysInMonth } from "../common.js";

describe("htmlInjectionProtection", () => {
  test("escapes HTML characters", () => {
    expect(htmlInjectionProtection("<script>")).toBe(
      "&lt;script&gt;"
    );
  });

  test("handles null values", () => {
    expect(htmlInjectionProtection(null)).toBe("");
  });
});

describe("getDaysInMonth", () => {
  test("returns the number of days in February", () => {
    expect(getDaysInMonth(2024, 2)).toBe(29);
    expect(getDaysInMonth(2025, 2)).toBe(28);
  });

  test("returns 31 for January", () => {
    expect(getDaysInMonth(2025, 1)).toBe(31);
  });
});
