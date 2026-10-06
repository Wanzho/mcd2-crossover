# MCD2 Crossover website

The page at https://wanzho.github.io/mcd2-crossover/ for [MCD2 Crossover](https://github.com/Wanzho/mcd2-crossover), Minecraft Dungeons II on Apple silicon Macs with CrossOver. It lives on this repository's `gh-pages` branch, apart from `main`, so rebuilding or force-pushing `main` never touches it.

Plain HTML, CSS and JavaScript, served by GitHub Pages with no build step and no outside requests except one to GitHub's API for the newest release:

- `index.html`, `style.css`, `site.js`: the page, the portal scene in the hero and the scroll reveals (`?y=1234` in the URL jumps to that scroll position, for screenshots). Nothing is tied to the scroll position; each scene plays on a timer once it's in view. The design matches [wasdmod's site](https://wanzho.github.io/wasd/).
- `app-demo.js`, `app-demo.css`: the clickable replica of the app in "Try it". Its strings come from the app's `localization/en.json`; refresh them when the app's screens change.
- `privacy.html`: the privacy page.
- `og.png`: the link preview (1200×630).

The version, size and download link in the page are filled in from the newest GitHub release when the page loads; the numbers typed into `index.html` are only the fallback, so update them at each release.

The "MCD2 Crossover" wordmark uses "Mojang" by b.tenthousand (CC0), `pixel.ttf`; everything else uses the system font. All art is drawn in code except the app icon.
