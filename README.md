# Keith Richards: Psychic Detective

**No. 1: The Case of the Guilty Millionaire.** From the world of Mega Vegas Elvis.

Read it here: **https://arnegleason.github.io/keith-psychic-detective/**

## The reader

A small dependency-free web reader (`index.html`, `viewer.css`, `viewer.js`).

- **Strip mode** shows a whole strip at a time. **Frame mode** shows one panel at a time.
  The reader picks a mode to suit the screen, and the Strip / Frame switch overrides it.
- Move with the arrow keys, space, the side arrows, a tap on the left or right third of
  the screen, or a swipe. Tap the middle to show or hide the controls.
- `I` opens the index, `S` switches mode, `F` goes full screen.
- Links are shareable: `#p4` is page 4, `#p4f2` is the second frame on page 4.

## Rebuilding the pages

Original artwork lives in `source-images/`. Scene names, frame names and page order live in
`tools/story.json`. The build script finds the panel gutters in each strip, writes optimised
JPEGs to `pages/`, thumbnails to `thumbs/`, and the manifest `comic.json`.

```bash
pip install pillow numpy
python3 tools/build.py
```

If a page's gutters are hidden by artwork, give that page a `"gutters": [[x0, x1], ...]`
override in `tools/story.json`.
