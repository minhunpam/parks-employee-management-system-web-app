export function csrfToken() {
    return document.cookie.split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
}

export const htmlInjectionProtection = (value) =>
  String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;"
  }[char])
  );

export function getDaysInMonth(year, month) {
  if (month === 12) {
    month = 1;
    year++;
  }

  const lastDay = new Date(year, month, 0);
  return lastDay.getDate();
}
