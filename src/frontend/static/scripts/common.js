export function csrfToken() {
    return document.cookie.split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
}