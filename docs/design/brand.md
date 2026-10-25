# Brand: the mark, the name, and the launch splash

Decided by Cayden on 2026-10-24 (`decisions.md` D21).
This file is the reference for the logo and the launch animation.
If code and this file disagree, fix the code or update this file in the same change.

## 1. The mark

The mark is a circle with a random walk inside it.
The walk starts at a filled dot and has small barbed arrowheads along it that show its direction.

What it means [inferred, Cayden's framing]:
- The walk is Brownian motion: each step goes somewhere that cannot be predicted from the last one.
  These are the stochastic agents, whose output is not deterministic.
- The circle is the deterministic system around them: the gateway, the code that does all the math, and the audit log.
  The agents move only inside it.
- The walk ends inside the circle, at a point the system has checked.
  A random process resolves into a checked result.

### Geometry

The source is a 1300-unit square, shown through `viewBox="240 240 820 820"`.

| Part | Value |
| --- | --- |
| Circle | `cx 650`, `cy 650`, `r 392`, stroke 7, no fill |
| Walk | polyline `437,397 550,588 752,385 345,637 812,925 812,628 402,763 515,898 958,793 622,632 782,498 896,566`, stroke 7, miter joins, butt caps |
| Start dot | `cx 437`, `cy 397`, `r 27`, filled |
| Arrowheads | path `M12 0 L-12 -11 L-5 0 L-12 11 Z`, filled, rotated to each segment's direction |
| Arrowhead places | the fraction along segments 1 to 11: 0.55, 0.62, 0.62, 0.55, 0.35, 0.47, 0.35, 0.55, 0.55, 0.55, 0.45 |

Everything in the mark is one ink color.
There are no gradients, no second color, and no fill inside the circle.

### Weights

The mark has three weights for three sizes.
The geometry (the circle and the walk) stays the same in each.

| Weight | Used at | Strokes | Dot | Arrowheads |
| --- | --- | --- | --- | --- |
| Full | 64 px and larger: the splash (232 px) | 7 | r 27 | scale 1 |
| Small | below 64 px: the sidebar (24 px), the favicon | 40 to 52, round joins | r 45 to 58 | none |
| Icon | the macOS app icon | 22 | r 48 | scale 2.6 |

The full weight's 7-unit strokes are under 0.25 px at 24 px and disappear, so small sizes use the small weight.
The arrowheads are left out below 64 px because they turn into noise on the line.
`StochasticMark` in the console picks the weight from its `size` prop.

### Minimum size and clear space

- Minimum size: 16 px for the small weight (favicon), 64 px for the full weight.
- Clear space: keep at least a quarter of the mark's width empty on every side.
  In the sidebar the 8 px gap to the name is the exception, because the mark and the name form one row.

## 2. Color

The ink follows the theme.

| Theme | Ink |
| --- | --- |
| Light | `#16191D` |
| Dark | `#ECE9E2` |

Inside the console the mark takes the color of the text around it (`currentColor`).
In the sidebar that is forest (`#1A5140`), the same as the name next to it.
The console has no dark theme yet, so the browser splash always uses the light ink (`--color-mark` in `globals.css`).
The favicon switches ink with the browser's `prefers-color-scheme`.
The desktop splash switches ink with the macOS appearance (section 4).

## 3. The name

The name in the lockup is "Stochastic", with a capital S (changed from lowercase by Cayden on 2026-10-25).
It is set in Instrument Serif Regular, the console's display serif (`--font-serif`, loaded in `frontend/src/app/layout.tsx`), at 48 px in the splash, with 0.01em letter spacing and a line height of 1.
It sits centered under the mark, 14 px below it.
The fallbacks are Iowan Old Style, New York, and Georgia.

The sidebar brand row uses the same "Stochastic" next to the small mark.

## 4. The launch splash

The rule: the splash shows only the circle and the name, centered, on a transparent background, until the whole app has loaded.
There is no card, no panel, no progress bar, and no text other than the name.

### The animation

The timings come from the approved prototype [verified: Cayden, 2026-10-24].
Time 0 is the moment the splash is visible.

| Time (ms) | What happens | Easing |
| --- | --- | --- |
| 0 to 380 | The circle draws clockwise, starting at the top | ease-in-out cubic |
| 300 to 460 | The start dot pops in with a slight overshoot: r scale = 1.25 sin(t pi / 2) - 0.25 t | as written |
| 420 to 1500 | The walk draws from the start dot (stroke-dashoffset); each arrowhead appears when the drawn length passes it | ease-in-out cubic |
| 1450 to 1770 | The name fades in and rises 6 px | ease, 320 ms |
| 2100 | The earliest the splash may close (the prototype's handover) | |

The ease-in-out cubic is `t < 0.5 ? 4t^3 : 1 - (-2t + 2)^3 / 2`.
The splash never closes before 2100 ms, so it never cuts mid-draw and the finished lockup is seen for at least 330 ms.
The brief from Cayden said about 1.8 s; 2.1 s is the prototype's own handover, so we used that [inferred].
After the draw, while the app is still loading, the start dot breathes slowly (12% larger and back over 2.4 s).
Nothing else moves.
When it closes, the splash fades out over 200 ms.

### Reduced motion

With `prefers-reduced-motion: reduce` (macOS Settings, Accessibility, Display, Reduce motion), the finished mark and the name show at once, with no draw, no fade-in, and no idle.

### Desktop

The desktop app is the real target.
`desktop/main.js` opens the splash before anything else, as its own window:
- Frameless and transparent (`frame: false`, `transparent: true`, `backgroundColor: "#00000000"`, `hasShadow: false`), 360 by 420, centered on the screen, not resizable or movable, and on top of other windows while it loads.
- It loads `desktop/splash.html`, a static page with the SVG and the script inline and the font from `desktop/assets/fonts/`.
  It makes no network request, so it works offline.

The launch sequence:
1. The splash opens and plays.
2. The backend and the console start (or, with `STOCHASTIC_DEV=1`, the app waits for the running `next dev`).
3. The main window loads the console while hidden.
4. When `GET /health` answers, the console page has loaded (`did-finish-load` and `ready-to-show`), and the console has finished its first read of the deal (`window.stochastic.appReady()`, or 8 s after the load if a console never reports it), and at least 2100 ms have passed since the splash appeared, the main window shows and the splash fades out and closes.
5. If anything fails on the way, the existing error window opens and the splash closes.
   The main window keeps its settings (1440 by 900, `hiddenInset`, background `#F7F4EC`), so there is no white flash.

Ink on a transparent window: the desktop behind the splash can be any wallpaper or app.
We pick the ink from the macOS appearance, through Electron's `nativeTheme`, which sets the page's `prefers-color-scheme`: `#16191D` in light mode, `#ECE9E2` in dark mode.
We chose this over a soft halo behind the strokes because a halo on a frameless window reads as a smudge around thin lines, and the appearance matches what macOS itself does with menu bar text [inferred].
The known gap: a dark-mode user with a very light wallpaper behind the splash sees light ink on light [inferred, not seen in testing].

### Browser

When the console runs in a browser, `LaunchSplash` (`frontend/src/components/launch-splash.tsx`) shows the same lockup centered over the page background (white), from first paint until the first read of the deal has finished, at least 2100 ms and at most 8 s, then fades out over 200 ms.
It shows on each full page load, not on page changes inside the console.
In the desktop app it renders nothing (the Electron splash already played): CSS hides it before hydration (`html[data-electron]`), and the component checks `window.stochastic?.isDesktop`.

## 5. Where each asset lives

| Asset | File |
| --- | --- |
| The mark as a React component (static and animated) | `frontend/src/components/stochastic-mark.tsx` |
| The browser splash | `frontend/src/components/launch-splash.tsx` |
| The sidebar brand row | `frontend/src/components/sidebar.tsx` |
| The favicon | `frontend/src/app/icon.svg` |
| The desktop splash | `desktop/splash.html` |
| The splash window and launch sequence | `desktop/main.js` (`createSplash`, `createMainWindow`) |
| The display font for the splash | `desktop/assets/fonts/InstrumentSerif-Regular.woff2` (latin subset, SIL Open Font License, `OFL.txt` next to it) |
| The app icon source | `desktop/assets/icon.svg` |
| The rendered app icon | `desktop/assets/icon.png` (1024 px, Dock when run from source) and `desktop/assets/icon.icns` (the packaged app) |

The geometry and the timings are written in two places: `stochastic-mark.tsx` and `splash.html`.
Change both together.
After a change to `icon.svg`, run `npm run icon` in `desktop/` and commit the PNG and the ICNS too.

## 6. Open item: the walk's source

The walk's points were traced from a stock reference image (Alamy) that Cayden supplied [verified: Cayden, 2026-10-24].
We do not hold a license for that image.
Before any public brand use beyond the hackathon demo, either license the image or replace the walk with our own seeded random walk of the same character (11 steps, inside the circle, ending near the right edge).
The circle, the dot, the arrowheads, and the animation do not depend on the traced points.
