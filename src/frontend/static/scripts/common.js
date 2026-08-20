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