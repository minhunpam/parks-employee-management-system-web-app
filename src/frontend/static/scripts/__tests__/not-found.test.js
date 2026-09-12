import { goBackOrHome } from "../not-found.js";

describe("goBackOrHome", () => {
  test("uses browser history for a same-origin previous page", () => {
    const back = jest.fn();
    const windowObject = {
      history: { length: 2, back },
      location: { origin: "https://parks.example", assign: jest.fn() },
    };
    const documentObject = { referrer: "https://parks.example/workspace/entry/" };

    goBackOrHome("/", windowObject, documentObject);

    expect(back).toHaveBeenCalledTimes(1);
    expect(windowObject.location.assign).not.toHaveBeenCalled();
  });

  test("falls back home without a useful previous page", () => {
    const windowObject = {
      history: { length: 1, back: jest.fn() },
      location: { origin: "https://parks.example", assign: jest.fn() },
    };

    goBackOrHome("/", windowObject, { referrer: "" });

    expect(windowObject.location.assign).toHaveBeenCalledWith("/");
    expect(windowObject.history.back).not.toHaveBeenCalled();
  });
});
