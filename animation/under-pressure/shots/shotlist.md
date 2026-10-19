# Under Pressure (episode 19): motion experiment

Goal: the comic's own painterly look in motion, nicely paced, no lip-sync
pass. Plates are the published panels with the lettering removed and the
frame extended to 16:9 by a Gemini image edit (`tools/clean_panel.py`), so the
brushwork is the page's. Dialogue goes into the Kling prompt as what the
character says; whatever Kling 4.0 does with it natively is kept, nothing is
dubbed afterwards.

Kling 4.0, Keyframes mode, first frame only, 1080p, adaptive ratio, one
output. 5 s = 67 credits, 10 s = 135.

Every prompt ends with the same style lock:

> Painterly graphic-novel illustration, visible brushwork, rich colour,
> slightly caricatured; keep exactly this painted look throughout, never
> photographic. Faces, masks, fur, costumes and props stay as in the image.
> No text, no speech balloons, no captions.

| # | Plate | s | Action and dialogue |
|---|---|---|---|
| CARD | title_strip over paper | 2.5 | THE PRIMATE SUSPECTS / UNDER PRESSURE |
| S1 | P1_caffeine | 5 | The red-caped ape brandishes the small paper packet and shakes it as he rants; the grey-maned ape in the cream coat answers with a calm, dry shrug; the maroon-jacketed ape sits hunched and miserable, hugging his stomach. Locked camera. Red cape says: "Ten times the caffeine! I've been awake all bloody night!" Cream coat says: "Yes. I spotted that after you went to bed." |
| S2 | P1 crop (right: cream coat + maroon) | 4 | The maroon-jacketed ape grimaces, shifts on his chair and clutches his stomach; the cream-coated ape glances at him sideways. Locked camera. Maroon jacket says, strained: "I need the toilet." |
| S3 | P2_plumber | 5 | The plumber in blue overalls at the open door hefts his red toolbox and turns to go out; the maroon-jacketed ape stands hunched and answers faintly; the red-caped ape slumps in the armchair. Locked camera. Plumber says: "Toilet's disconnected. Five minutes." Maroon jacket says, faintly: "I can do five minutes." |
| S4 | P2 crop (right: armchair) | 4 | The red-caped ape in the armchair sags, eyelids drooping, head lolling, and falls asleep. Slow push in. Red cape says, fading: "I've never been so tired in my life. I feel like I'm gonna pass out." |
| S5 | P3_bubble_house | 10 | Exterior. A vast transparent soap-film bubble swells up from the house and settles over the whole ivy-covered cottage and garden, rainbow colours rippling across its surface. Through the ground-floor window the red-caped ape sleeps in his armchair. Outside the bubble the plumber in blue overalls stands frozen mid-reach at the pipe, utterly still, as if time has stopped for him. Very slow camera drift. No dialogue; a soft shimmering hum. |
| CARD | caption_four_hours over paper | 2 | FOUR HOURS LATER |
| S6 | P4_four_hours | 5 | The ape in the steel helmet presses both palms on the glowing bubble wall in the doorway and strains; the wall flexes like elastic under his hands but holds. Behind him the maroon-jacketed ape and the cream-coated ape watch, exhausted; the red-caped ape sleeps in the chair. Outside, beyond the bubble, the plumber stays frozen. Locked camera. Maroon jacket says: "That's been a bloody long five minutes." Cream coat says: "It hasn't started." |
| S7 | P5_one_push | 5 | The cream-coated ape plants both hands on the helmeted ape's back and shoves; the helmeted ape strains forward, the bubble wall bulges outward around his palms and springs back; a small, short squeak. Locked camera. Cream coat says: "One good push!" |
| S8 | P6_smell | 5 | All three apes recoil: the maroon-jacketed ape claps a hand over his nose and mouth, the cream-coated ape grimaces and waves the air, the helmeted ape hunches, sheepish, and glances back guiltily. The red-caped ape sleeps on behind them. Locked camera. Maroon jacket says, muffled: "My God. What's that smell?" |
| CARD | title_strip over paper | 2.5 | end card |

Running time: 43 s of motion, about 50 s with cards. Credits if every shot
takes once: 7 × 67 + 135 = 604.

Pacing notes for the cut: hard cuts; hold S5 for its full length, it is the
breath before the caption; let S7's squeak land in silence for half a second
before S8; end on S8's reaction, then the card.
