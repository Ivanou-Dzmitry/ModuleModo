# Refboard Builder

A one-page tool that turns photos of a building and its facade modules into a clean reference board
(1980×1020 PNG) for game asset production. It runs entirely in the browser: photos never leave the computer.

## How to use

1. **Project**: building name, subtitle, author, date, accent colour, sheet background and text colour,
   sheet language (English or Russian).
2. **Grid and floors**: grid step (3 m), number of bays, ground floor height (4 m), upper floor height (3 m),
   number of upper floors.
3. **General view**: drop a photo of the whole facade and frame it.
4. **Modules**: drop module photos (windows, doors, balcony, wall). For each one set a code (`W-01`, `D-01`,
   `BR-01`), a name, a caption and a size: 3 × 3 m, 3 × 4 m or a custom size. Frame the photo:
   drag to move, mouse wheel to zoom, double-click to reset.
5. **Facade layout**: pick a module and click the grid cells. Right-click clears a cell. Switch between the
   front and the side elevation (set the house depth in bays; 0 hides the side). Choose a filler module
   (usually the brick wall) for empty cells and for the gap under a module that is lower than its floor.
6. **Materials**: up to 6 swatches. Press **Take colours from photos** to take colours from the module photos,
   or add a texture photo (brick, plaster, roof tiles): it is cut to a square that you can move and zoom.
   Swatches fill the column on their own (1–3 in a column, 4 as 2 × 2, 5–6 as 3 × 2), or set the side in px.
7. **Download PNG** saves the board. **Save project** saves a `.json` file with the photos inside, so
   you can open it later with **Open project**.

The interface speaks Russian and English: switch with **RU / EN** in the top bar. The sheet language is a separate
project setting, so a Russian interface can produce an English sheet. The **?** button opens a short help.

Tip: straighten the perspective of your photos first (Photoshop: Perspective Crop; GIMP: Perspective tool).

## Publish on GitHub Pages

1. Put `index.html`, `i18n.js`, `app.js` and `style.css` in the root of a repository (or in a `docs/` folder).
2. Repository **Settings → Pages → Build and deployment → Deploy from a branch**, branch `main`,
   folder `/ (root)` or `/docs`.
3. After a minute the tool is live at `https://<user>.github.io/<repo>/`.

No build step, no dependencies. To run it locally, open `index.html` in a browser.
