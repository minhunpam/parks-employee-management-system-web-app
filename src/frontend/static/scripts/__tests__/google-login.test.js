describe("Google sign-in loading state", () => {
  let showSignInLoading;
  let hideSignInLoading;

  beforeAll(() => {
    document.body.innerHTML = `
      <div id="sign-in-loading-overlay" class="hidden">
        <button id="cancel-sign-in" type="button">Cancel</button>
      </div>
      <a href="http://localhost/auth/google/login/">Sign in</a>
    `;

    ({ showSignInLoading, hideSignInLoading } = require("../accounts/google-login.js"));
  });

  afterEach(() => {
    hideSignInLoading();
    document.querySelector("a").dataset.signInPending = "false";
    jest.restoreAllMocks();
  });

  test("shows the overlay and locks page scrolling", () => {
    showSignInLoading();

    const overlay = document.querySelector("#sign-in-loading-overlay");
    expect(overlay.classList.contains("hidden")).toBe(false);
    expect(overlay.classList.contains("flex")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });

  test("restores scrolling when the loading state ends", () => {
    document.body.style.overflow = "auto";
    showSignInLoading();
    hideSignInLoading();

    const overlay = document.querySelector("#sign-in-loading-overlay");
    expect(overlay.classList.contains("hidden")).toBe(true);
    expect(document.body.style.overflow).toBe("auto");
  });

  test("shows the loading state when sign-in is clicked", () => {
    const popup = { closed: false, focus: jest.fn(), close: jest.fn() };
    jest.spyOn(window, "open").mockReturnValue(popup);

    document.querySelector("a").click();

    expect(window.open).toHaveBeenCalledWith(
      "http://localhost/auth/google/login/?popup=1",
      "parks-google-login",
      "popup,width=520,height=680"
    );
    expect(document.body.style.overflow).toBe("hidden");
    expect(popup.focus).toHaveBeenCalled();
  });

  test("allows the user to cancel sign-in", () => {
    const popup = { closed: false, focus: jest.fn(), close: jest.fn() };
    jest.spyOn(window, "open").mockReturnValue(popup);

    document.querySelector("a").click();
    document.querySelector("#cancel-sign-in").click();

    expect(popup.close).toHaveBeenCalled();
    expect(document.body.style.overflow).toBe("auto");
    expect(document.querySelector("#sign-in-loading-overlay").classList.contains("hidden")).toBe(true);
  });
});
