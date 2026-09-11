# Not Found Page

## Purpose

The not found page provides a clear, branded response when a user requests an unknown URL. It should communicate that the requested page is unavailable without exposing internal routing details or making the user feel stranded.

## Page Direction

The page is a standalone dark experience rather than a regular application screen. This gives the error state a clear visual identity while remaining consistent with PARKS's technical, angular design language.

- The page should use:
  - A black canvas with white supporting text
  - NVIDIA Green for the main accent and actions
  - Angular geometry with minimal corner rounding
  - A PARKS wordmark in the upper-left
  - A small green corner-square motif
  - A minimal footer containing the PARKS identity and system label

- **The page should not recreate the full application navigation or display the requested URL.**

## Content

The primary visual anchor is an oversized green `404` numeral accompanied by a small green corner-square detail.

The page copy is:

- **Eyebrow:** `404`
- **Headline:** `Page not found`
- **Supporting message:** `The page you’re looking for doesn’t exist or may have moved.`

The tone is direct and technical. It should avoid playful or overly conversational language.

## Navigation

The page provides two recovery actions:

- **Primary:** return to the home page
- **Secondary:** go back to the previous browser location

The browser-back action should use the user's history when a useful previous location exists. If there is no suitable history entry, it should fall back to the home page.
- The home destination remains appropriate for both authenticated and unauthenticated users because the application handles their next destination.
  - A small reminder/ recall for this:
    - For authenticated users, the browser will direct them to:
      - For active users: `/workspace/entry/`
      - For inactive users: `/auth/approval-pending/`
    - For unauthenticated users, the browser will direct them to home page

## Routing Behavior
- The page is the global response for unknown application URLs. It must preserve the HTTP `404 Not Found` status.

- The branded page is intended for production-like behavior. During local development with debugging enabled, Django's detailed technical error page should remain available for diagnostics.

## Responsive Behavior

- The standalone composition should remain readable and usable across desktop, tablet, and mobile viewports:
  - The oversized numeral and message may use a stacked layout on narrow screens.
  - Both recovery actions must remain comfortably touchable.
  - The PARKS wordmark and footer should retain adequate spacing from the viewport edges.
  - The dark canvas should fill the available page height without relying on fixed viewport dimensions.

## Accessibility

The page should:

- Use a meaningful page title and descriptive main heading.
- Preserve a clear heading hierarchy.
- Provide visible keyboard focus indicators for both actions.
- Maintain sufficient contrast between the dark canvas, white text, and green accent.
- Ensure the browser-back action has an accessible name that describes its behavior.

## Validation
The implementation should verify that:

- An unknown URL renders the branded page.
- The response status remains `404`.
- The page includes the intended recovery actions and core copy.
- The home action resolves correctly.
- The page remains compatible with the existing production-like routing behavior.
