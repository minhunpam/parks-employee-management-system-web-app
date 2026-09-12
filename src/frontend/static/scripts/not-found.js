export function goBackOrHome(fallbackUrl, windowObject = window, documentObject = document) {
  const referrer = documentObject.referrer;
  let hasSameOriginReferrer = false;

  if (referrer) {
    try {
      hasSameOriginReferrer = new URL(referrer).origin === windowObject.location.origin;
    } catch {
      hasSameOriginReferrer = false;
    }
  }

  if (windowObject.history.length > 1 && hasSameOriginReferrer) {
    windowObject.history.back();
    return;
  }

  windowObject.location.assign(fallbackUrl);
}

const backButton = document.querySelector("[data-back-button]");

if (backButton) {
  backButton.addEventListener("click", () => {
    goBackOrHome(backButton.dataset.homeUrl);
  });
}
