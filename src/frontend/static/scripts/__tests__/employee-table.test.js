import { renderEmployeeRows } from "../workspace/employee-table.js";
import { htmlInjectionProtection } from "../common.js";

const makeRow = (date) => ({
  date,
  shiftStart: "—",
  pauseStart: "—",
  pauseEnd: "—",
  shiftEnd: "—",
  pauseTime: "—",
  shiftTotalTime: "0:00",
  type: "Frei",
  warnings: "—",
});

const render = (dates) => renderEmployeeRows(dates.map(makeRow), htmlInjectionProtection);

describe("renderEmployeeRows calendar week separators", () => {
  test("counts the partial week at the start of a month as week 1", () => {
    const markup = render(["01.05.2026", "02.05.2026", "03.05.2026"]);

    expect(markup).toContain("End of week 1");
    expect(markup.indexOf("03.05.2026")).toBeLessThan(markup.indexOf("End of week 1"));
  });

  test("adds a separator after an in-month Sunday", () => {
    const markup = render(["03.05.2026", "04.05.2026"]);

    expect(markup.indexOf("03.05.2026")).toBeLessThan(markup.indexOf("End of week 1"));
    expect(markup.indexOf("End of week 1")).toBeLessThan(markup.indexOf("04.05.2026"));
  });

  test("adds a separator for a month ending in a partial calendar week", () => {
    const markup = render(["30.05.2026", "31.05.2026"]);

    expect(markup).toContain("End of week 5");
  });

  test("numbers weeks by the calendar month, not ISO week numbers", () => {
    const markup = render(["03.01.2021", "04.01.2021"]);

    expect(markup.indexOf("03.01.2021")).toBeLessThan(markup.indexOf("End of week 1"));
    expect(markup.indexOf("End of week 1")).toBeLessThan(markup.indexOf("04.01.2021"));
  });

  test("renders a full-width separator without a correction action", () => {
    const markup = render(["03.05.2026"]);
    const separator = markup.match(/<tr class="border-b border-\[#cccccc\] bg-\[#f7f7f7\]">[\s\S]*?<\/tr>/)[0];

    expect(separator).toContain('colspan="10"');
    expect(separator).toContain("End of week 1");
    expect(separator).not.toContain("correct-entry");
    expect(markup.match(/class="correct-entry/g)).toHaveLength(1);
  });
});
