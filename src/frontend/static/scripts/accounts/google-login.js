const loginLinks = document.querySelectorAll('a[href*="/auth/google/login/"]');
console.log(loginLinks);
console.log(window.location.href);

loginLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();

    const loginUrl = new URL(link.href);
    loginUrl.searchParams.set("popup", "1");

    const popup = window.open(
      loginUrl.toString(),
      "parks-google-login",
      "popup,width=520,height=680"
    );

    if (!popup) {
      window.location.assign(loginUrl.toString());
      return;
    }

    popup.focus();
  });
});

const broadcastChannel = new BroadcastChannel("google-oauth");
console.log(broadcastChannel)

broadcastChannel.onmessage = (event) => {
  if (event.data.type !== "google-oauth-complete") {
    return;
  }

  window.location.replace(event.data.destination);
}
