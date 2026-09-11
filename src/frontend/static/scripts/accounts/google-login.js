const loginLinks = document.querySelectorAll('a[href*="/auth/google/login/"]');
const loadingOverlay = document.querySelector("#sign-in-loading-overlay");
const cancelSignIn = document.querySelector("#cancel-sign-in");
let previousBodyOverflow = "";
let signInPopup;

export function showSignInLoading() {
  if (!loadingOverlay) {
    return;
  }

  previousBodyOverflow = document.body.style.overflow;
  loadingOverlay.classList.remove("hidden");
  loadingOverlay.classList.add("flex");
  document.body.style.overflow = "hidden";
}

export function hideSignInLoading() {
  if (!loadingOverlay) {
    return;
  }

  loadingOverlay.classList.add("hidden");
  loadingOverlay.classList.remove("flex");
  document.body.style.overflow = previousBodyOverflow;
}

function cancelSignInFlow() {
  if (signInPopup && !signInPopup.closed) {
    signInPopup.close();
  }

  signInPopup = undefined;
  loginLinks.forEach((link) => {
    link.dataset.signInPending = "false";
  });
  hideSignInLoading();
}

loginLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();

    if (link.dataset.signInPending === "true") {
      return;
    }

    link.dataset.signInPending = "true";
    showSignInLoading();

    const loginUrl = new URL(link.href);
    loginUrl.searchParams.set("popup", "1");

    signInPopup = window.open(
      loginUrl.toString(),
      "parks-google-login",
      "popup,width=520,height=680"
    );

    if (!signInPopup) {
      window.location.assign(loginUrl.toString());
      return;
    }

    signInPopup.focus();
  });
});

cancelSignIn?.addEventListener("click", cancelSignInFlow);

if (typeof BroadcastChannel !== "undefined") {
  const broadcastChannel = new BroadcastChannel("google-oauth");

  broadcastChannel.onmessage = (event) => {
    if (event.data.type !== "google-oauth-complete") {
      return;
    }

    hideSignInLoading();
    window.location.replace(event.data.destination);
  };
}
