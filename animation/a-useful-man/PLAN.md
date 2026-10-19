# The Primate Suspects: animated short. Plan v2 (2026-10-19)

Inputs read: all 18 pages in `source-images-primate-suspects` (repo
`ArneGleason/keith-psychic-detective`, main at a895d71), and the ChatGPT care
package `primate-suspects-claude-handoff.zip` (five briefs plus two reference
sheets: Dr. Agatha Hindsight, and Boggler / hippie neighbour / goat).

## 0. Decisions so far

| Decision | Status |
|---|---|
| Fully voiced cartoon, placeholder voices now, redub later | **Owner, 2026-10-19** |
| Which film | **Owner, 2026-10-19: *A Useful Man*** (episodes 9 + 14). Cold open and "Lovely people" tag still to confirm at animatic. |
| Project home | `animation/` in the comics repo (local clone `Documents/ChatGPT/keith-psychic-detective`); generated media gitignored |
| Swearing stays | Assumed yes (it is most of the Boggler and the goat) |

## 1. What the handoff adds to what the pages show

- **Rules of the world.** No mission, no villain, no origin. Episodes work in
  any order. Comedy is vanity, misplaced confidence, petty needs. Earnestness
  matters: the Major is never malicious. The owner's favourite device is a
  heroic fantasy that snaps back to something mundane, with the reveal held to
  the end and never labelled a dream.
- **Names fixed.** Laura and Rob Pritchard (the neighbours; not Mary, not
  Dick). Cyril is the human, Clive is the gnome. Dr. Agatha Hindsight is the
  mother. The hippie neighbour has no name yet. Major is never "Havoc".
- **Design corrections.** Professor: no glasses, no tweed. Agatha: glasses,
  tweed, one gold banana brooch. Hands: four fingers plus thumb. Clive is
  ceramic, never a living dwarf. Title lettering is made in the edit, never
  asked of the video model.
- **Power corrections.** Major's touch breaks *things*, not only machines, and
  not every teacup. Count's bubble: ordinary time inside, almost none outside;
  never "frozen", never time travel. Boggler hears objects, but not every
  object, and only he reacts to them.
- **Two approved episodes are missing from the repo:** 18 *Special
  Containment* (Major + sci-fi Agatha, alien container, SPROING, bra across the
  helmet) and 19 *Under Pressure* (caffeine, house-sized bubble, plumber,
  burrito). They exist only in the ChatGPT workspace. Not on this machine
  either (searched Downloads, Documents, Pictures, Desktop).
- **Voice directions (provisional):** Count dry and tired with theatrical
  airs; Professor self-satisfied pedantic precision; Major warm earnest
  enthusiasm; Boggler tentative courteous confusion; Agatha clipped
  authoritative restraint; Laura sweet and carefully innocent; Rob breezy
  conspiratorial confidence.

## 2. The film: *A Useful Man* (recommended)

Episodes 9 and 14 joined, about 2.5 to 3 minutes. Laura and Rob Pritchard
each discover, separately, that the ape next door will destroy anything you
hand him, and each secretly uses it. The Major is simply happy to be wanted.
Handoff's own timed outline, with my additions marked NEW:

| Time | Beat | Source | Notes |
|---|---|---|---|
| 0:00–0:10 | NEW cold open: HQ kitchen, "DAYS WITHOUT POOP FLING: 1", Major does the toast, PFFT, Count: "Every bloody time." | ep 1 | Establishes the power in one gag for anyone who has not read the strip. Cut if it feels like padding. |
| 0:10–0:22 | Exterior Pritchard house. Laura welcomes the Major. The musical clown's tune already audible. | ep 9 p1 | One recurring location, one sound motif. |
| 0:22–0:48 | "My husband gave me this on our honeymoon. It really deserves a more prominent position." Major takes it with great care. Laura watches a little too intently. | ep 9 p2–3 | Hands, her anticipation, his earnest care. |
| 0:48–1:02 | KRRK-PLONK. Tune dies mid-phrase. Silence. "Oh, no." "Oh... my honeymoon clown." | ep 9 p4 | Short silence before the reaction. No line explaining her scheme. |
| 1:02–1:18 | Tea. "Won't your husband be upset?" "I'll bear up through it somehow. Tea?" | ep 9 p5 | Breathing room, warmth. |
| 1:18–1:30 | At the door: "Perhaps my anniversary figurine would look lovely over the fireplace." Cut before the outcome. | ep 9 p6 | Button. |
| 1:30–1:48 | Later. Rob with the pool-table flyer, eyeing the organ. "It would fit perfectly where the organ is." "Then it won't fit." Hears the Major arriving. | ep 14 p1 | Flyer readable as an insert. |
| 1:48–2:10 | Rob: "Could you look at this fan? It's stopped turning." Major: "You might want to move anything valuable." Rob pockets the chimney-sweep bobblehead. | ep 14 p2–3 | One geography shot showing fan, trophy, bowling ball, organ BEFORE the close-ups. |
| 2:10–2:34 | WHIRR-KLACK. PING. The ball rolls. BRAAANG. | ep 14 p4–5 | Three or four short cause-and-effect inserts, never one generated physics shot. |
| 2:34–2:52 | "I only asked him to fix the fan." Laura, arriving: "Well. Now I can get one with three keyboards." | ep 14 p5–6 | Mirror Laura's earlier solicitousness without repeating her words. |
| 2:52–3:02 | NEW tag: Major walks home, "Lovely people." Behind him, through two windows, Laura and Rob each look at a different unwanted object. | handoff proposal | Needs your approval. Imply, do not explain. |
| 3:02–3:08 | THE PRIMATE SUSPECTS title card, end sting. | cover | Lettering done in Blender. |

Dialogue: everything in quotes above is from the pages. New lines: none
except "Lovely people." (handoff proposal). Shortened: nothing yet.

Alternatives, kept on the shelf:
- **Private Conversations** (ep 11 opener + ep 16 goat): cheaper motion,
  harder voice timing. Good second film.
- **Special Containment** (ep 18): the handoff's pick for a first motion test
  because of its fantasy-to-reality cut. Blocked until the keeper page is
  exported from ChatGPT.
- **One-day omnibus** (plan v1, ten beats across twelve episodes): too much
  for a first film. Possible later as a "season one" reel.

## 3. Voices: placeholder now, redub later

**Placeholder voices.** An OpenAI key is on this machine, so the placeholder
track can be generated by script with `gpt-4o-mini-tts`: a fixed voice name
per character plus a written performance instruction. Same voice name and
instruction every time gives consistent casting across every line, which is
the thing you were unsure about. Proposed casting to test (one line each,
pick or swap):

| Character | TTS voice | Instruction |
|---|---|---|
| Major Malfunction | `ash` | warm, eager, slightly military clip, delighted to be asked |
| Professor Hindsight | `fable` | pompous British precision, savouring long words |
| Count Napula | `onyx` | dry, tired, a touch theatrical |
| Mind Boggler | `echo` | tentative, courteous, confused by himself |
| Laura Pritchard | `shimmer` | sweet, carefully innocent, 1960s sitcom wife |
| Rob Pritchard | `alloy` | breezy, conspiratorial |
| Agatha | `sage` | clipped, authoritative, unimpressed |

Telepathy (Clive, the goat, the banana): same TTS voice, then a close dry
intimate treatment in the mix (no room, slight low-pass), so it reads as
heard-in-the-head. Only the Boggler ever reacts.

**Redub later.** Keep the picture independent of the voice: silent base clips
plus a separate dialogue track per line. A redub then means re-running the lip
sync on the dialogue shots only, not regenerating picture. Candidates for the
real voices: ElevenLabs voice design, or you and friends.

**Lip sync.** Kling Lip Sync with an uploaded dubbing track is the recipe
already proven on Rivers of Mars (8 s vocal slice from the cut start, Add
Speech at 0:00, download via the Download button). Unproven: whether Kling's
mouth detection works on a 1970s ape mask. That is test T3 below. Kling 4.0
now also lists an **Avatar** tool (talking avatar from one image plus audio)
which may suit dialogue close-ups better than syncing a generated clip. The
pane was not signed in, so credits and current prices are unverified.

## 4. Test battery before any scale-up (handoff step 5)

All three from episode 9, inside the chosen film, so nothing is wasted:

| Test | Shot | Proves |
|---|---|---|
| T1 | Two-shot: Laura hands the Major the clown, he takes it carefully, she watches | two-character exchange, hands, costume stability |
| T2 | Insert: clown shatters (KRRK-PLONK), then Major's appalled close-up | physical gag as before/contact/after, reaction timing |
| T3 | Close-up: Laura line, then Major line, placeholder voices, Kling lip sync on the ape mask | the whole voiced pipeline on the hardest face |

Review together, then decide whether the Major's dialogue uses Lip Sync,
Avatar, or stays mostly in reaction shots with lines off-screen.

## 5. Pipeline

1. **Clean plates.** The pages have bubbles baked in. Regenerate the keyframes
   bubble-free in 16:9 from the page crops as reference (OpenAI image edit by
   script, or ChatGPT by hand), with one identical lock block per character
   from the cover, the reference sheets and the corrections above. Store the
   lock block as `style.md`, as the toolkit does.
2. **Shot list** as `shotlist.json` (toolkit schema): shot id, duration,
   plate, one action, speaker, line, SFX, lettering.
3. **Animatic** in Blender from plates plus the placeholder dialogue track
   and temp music. Judge the gag timing here before spending credits.
4. **Motion**: Kling image-to-video from the approved plate (never from a
   video frame), one action per shot, held end pose. Continuous takes for
   anything that recurs.
5. **Lip sync** on dialogue shots only.
6. **Comp** in Blender: titles, the two SFX letterings (KRRK-PLONK, BRAAANG),
   paper-texture transitions between scenes, grain.
7. **Log** every generated clip against shot id, plate, prompt, credits.

Tools on this machine: ffmpeg, Blender 5.2, the toolkit's `blender_comp.py`,
`shotplan.py`, `prompts.py`; OpenAI and Google API keys in the environment.

## 6. Needed from you

1. **Casting**: listen to `voices/casting/casting_reel.mp3`; say which Major and Laura (primary or alt) and anything that sounds wrong.
2. **Episodes 18 and 19**: export the two keeper pages from ChatGPT into the repo when convenient. Not blocking for *A Useful Man*.
3. **Kling**: sign in to the built-in browser pane (or tell me to use Chrome) so I can read credits and the 4.0 Lip Sync / Avatar options.
4. **Project home**: `animation/` in the comics repo is my recommendation; say if you want it elsewhere.
