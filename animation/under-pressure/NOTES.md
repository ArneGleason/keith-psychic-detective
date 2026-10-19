# Under Pressure: painterly motion experiment (2026-10-19)

Owner brief: forget dialogue and lip sync; get the comic's own graphic,
painterly, caricatured look moving, nicely paced, from the page for episode
19 (not yet in the comic folder; the owner supplied it as an image).

Result: `out/under_pressure_v1.mp4`, 49 s, eight shots plus three cards.
Every shot keeps the painted surface in motion. Cost 805 Kling credits for
eleven jobs, three of which were wasted (see log).

## What made the look work

The plates are the published panels themselves, not re-imagined images.
`tools/clean_panel.py` sends the panel crop to Gemini
(`gemini-3-pro-image`, about 17 s each) with one instruction: remove every
balloon, caption and sound-effect word, paint in what was behind them,
extend the scene to 16:9, keep every character, pose and brushstroke. The
same call with "REFRAME as a closer medium shot ..." makes close-up plates
from the same painting (`P1b_prof_boggler`, `P2b_count_armchair`). The first
attempt at `P5_one_push` invented a laboratory beyond the bubble; naming what
is outside the door fixed it.

Kling 4.0 Keyframes image-to-video then keeps the brushwork. Each prompt ends
with the same style lock (in `shots/prompts.json`). Dialogue is written into
the prompt as what each character says; Kling moves the mouths and adds its
own sound. No voices were generated and nothing was dubbed.

## What went wrong, and the rules that came out of it

- Three jobs ran as text-to-video and produced generic flat anime apes. Two
  used 2x upscaled crops (not needed, and apparently rejected); one was
  submitted while the First-frame slot was still uploading. Rule: wait and
  zoom on the slot until the plate thumbnail shows before Generate. An output
  of exactly 1920x1080 means the plate was ignored; 1924x1076 means
  image-to-video ran.
- After a page reload the grid composer's file input stops binding uploads.
  Start from the home composer (kling.ai/app, Keyframes), then keep working
  in the grid composer without reloading. The duration resets to 10 s on
  reload; the spinner arrows set it more reliably than typing.

## Pacing

`shots/cut_v1.json`, assembled by `tools/assemble_cut.py`: title 2.5 s, S1 5,
S2 4, S3 5, S4 5, S5 (bubble) 7.5 of its 10, caption 2, S6 5, S7 5, 0.4 s
black, S8 5, 0.3 s black, end card 2.5. Hard cuts; the cards fade.

## v2 (same evening): comic overlays, music to replace the audio

Owner review of v1: the painted look and Kling's own voices are not bad, but
the push gag was lost (the squeak never read), "I need the toilet" was cut
off, and the whole thing felt clipped together. Direction: use the Monsters
Undone word-bubble effect for the dialogue, keep the lip movement, replace
Kling's audio with music, do the sound effects as lettering with emanata
lines, and title in-shot instead of cutting to page crops.

`tools/overlays.py` is a Pillow port of the Monsters Undone balloon
(HARPER-SPEECH-001 build v005 in the toolkit): one continuous contour with
the tail in the perimeter, ivory fill, pressure-varying ink outline, Bangers
lettering, inflation on the first word, words landing at fixed positions, a
settle, five-frame ease in and four-frame fade out. Plus `sfx` lettering with
a pop and radiating lines from a source point, a sliding `caption` box, and
the series `masthead` band (yellow/red on teal, sheared). Elements are timed
relative to the clip they sit on (`shots/overlays_v2.json` +
`out/base_v2_silent.timeline.json`), so holds can change without renumbering.
Lip timing came from `tools/speech_timing.py` (Gemini watches each clip and
reports who speaks when); speakers follow the page where Gemini disagreed.

Pacing changes in `shots/cut_v2.json`: S1 holds its first frame 2.2 s under
the masthead; S2, S3, S4 and S6 hold their last frame so the final bubble can
breathe; S7 is cut at 3.4 s, straight after the squeak reaction, because Kling
put the Professor's "one good push" mouth movement after the push; S8 holds
for the end card. Cards are gone; the caption and masthead live in-shot.
Outputs: `out/under_pressure_v2_silent.mp4` (for music) and
`out/under_pressure_v2_klingaudio.mp4` (reference, Kling's sound kept).

## v3: music and the squeak

Owner liked v2 with the bubbles and asked for Curb-style comedy music and a
balloon squeak for the Major. `out/under_pressure_v3.mp4`, mixed by
`tools/mix_audio.py` from `shots/mix_v3.json`:

- Music: original cue from Google Lyria 3.5 (`tools/lyria_music.py`, Gemini
  API, GOOGLE_API_KEY), prompted as a bouncy 1960s Italian film comedy cue
  (mandolin, oom-pah tuba, pizzicato, bassoon); take A of two. ElevenLabs
  Music generated two takes too (1,800 credits) but its free plan will not
  download music; those takes are still in the ElevenLabs history if the
  owner upgrades.
- Squeak: ElevenLabs Sound Effects, take 4 of 4 ("rubber balloon neck"
  prompt, 84 credits). Free plan downloads sound effects as WAV.
- Clock: ElevenLabs Sound Effects, slow mantel clock (180 credits), under
  the awkward pause.
- Timing: the music stops dead at 39.1 as the push peaks, the squeak hits at
  39.3 with the SQUEAK lettering, the clock ticks 41.2 to 44.3 while "What's
  that smell?" lands, and the cue's last bar returns at 44.0 so its button
  chord lands at 47.3 under the masthead. Integrated loudness -13.9 LUFS.
- `tools/listen.py` has Gemini listen to audio and compare takes; used to
  pick the squeak, the clock and the music take, and to check the gag.

## Next, if this direction continues

- Same recipe on *A Useful Man*: regenerate its plates with `clean_panel.py`
  from the episode 9 and 14 panels instead of the photoreal lock block.
- Voices remain the open problem (see `../a-useful-man/RETRO_2026-10-19.md`).
  With this recipe the picture is cheap; a redub is Avatar per line.
- Page 19 (and 18) should be added to the comic folder and story JSON so the
  reader has them; `src/19-under-pressure.png` is the owner's export.
