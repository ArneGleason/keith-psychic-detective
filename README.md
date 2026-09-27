# MVE Comics

Comics from the Mega Vegas Elvis Universe, with a small web reader.

Read them here: **https://arnegleason.github.io/keith-psychic-detective/**

| Comic | Status |
|---|---|
| Keith Richards: Psychic Detective No. 1 | Complete |
| Captain Beefheart: Laurel Canyon Tour Guide No. 1 | In progress |

## The reader

A small dependency-free web reader (`index.html`, `viewer.css`, `viewer.js`).

- The home page is a shelf of covers. Pick one to start reading.
- **Strip mode** shows a whole strip at a time. **Frame mode** shows one panel at a time.
  The reader picks a mode to suit the screen, and the Strip / Frame switch overrides it.
- Move with the arrow keys, space, the side arrows, a tap on the left or right third of
  the screen, or a swipe. Tap the middle to show or hide the controls.
- `I` opens the index, `S` switches mode, `F` goes full screen.
- The shelf remembers where each reader stopped and offers to continue from there.
- Links are shareable: `#captain-beefheart` opens a comic at its cover, and
  `#captain-beefheart/p4f2` opens page 4 at its second frame.

## How it fits together

| Path | What it is |
|---|---|
| `source-images*/` | The original artwork, one folder per comic |
| `tools/library.json` | The shelf title and the order of the comics |
| `tools/stories/<comic>.json` | One per comic: its source folder, scenes, and frame names |
| `tools/build.py` | Finds the panels, writes the web images, and writes the data the reader uses |
| `comics/` | Build output. Do not edit by hand |

The build finds the panel gutters in each strip and writes optimised JPEGs,
thumbnails, and each comic's `comic.json`. It also writes `social.jpg`, the preview
image that shows when someone shares the link.

```bash
pip install pillow numpy
python3 tools/build.py
```

## Adding strips to a comic

1. Drop the new images into the comic's source folder.
2. Run the build. Images the story file does not name yet are added at the end under
   "New Pages", with numbered frames, and the build lists them.
3. To name them, add a line per image to the `pages` list in `tools/stories/<comic>.json`,
   with one name per panel, then build again. Add a new entry to `scenes` if the strip
   starts a new scene.

```json
{"file": "CBLCTG - 33.png", "kind": "strip", "scene": "s15", "frames": ["First Frame", "Second Frame", "Third Frame"]}
```

Files are listed in reading order, so a redrawn strip such as `10a.png` just replaces
`10.png` in its line.

When a comic is finished, add its end page with `"kind": "end"` and change `"status"`
from `"in-progress"` to `"complete"`. The last page then says "The End" instead of
"To be continued".

## Adding a new comic

1. Put its images in a new folder, for example `source-images-new-comic/`.
2. Copy one of the files in `tools/stories/` to `tools/stories/new-comic.json`. Set its
   title, `source` folder, scenes and pages.
3. Add `"new-comic"` to the `comics` list in `tools/library.json`. The shelf follows that order.
4. Run the build.

## When the build complains

- **Found 2 panels but the story names 3.** The artwork probably covers a gutter, as the
  green glow does on Keith Richards page 13. Add the gutter positions by hand to that page's
  line, as `"gutters": [[508, 516], [1012, 1022]]`. Each pair is the left and right pixel
  edge of one gutter between panels.
- **Listed but not found.** A file named in the story file is missing from the source folder.
  Check the spelling, including spaces.
- To leave an image in the folder out of the comic, add its file name to a `"skip"` list
  in the story file.
