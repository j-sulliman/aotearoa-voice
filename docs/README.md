# docs/

Repo-level documentation and assets that don't live in the source tree.

## hero.gif

The README's hero image. **You need to capture this before publishing the
repo** — without it, the README opens with a broken-image marker.

What it should show, in 5-7 seconds:

1. The mic button being pressed and held (recording state visible)
2. The transcript filling with the user's question
3. The map panning to the location the agent surfaces
4. The agent's reply typing in alongside playback
5. (Optional) the *Behind the scenes* panel with the live tool call

### Recording

On macOS, the simplest path is QuickTime → File → New Screen Recording, then
crop to the relevant window. For a smaller, web-optimised GIF:

```bash
# Record an .mov, trim to 5-7s, then convert to GIF:
ffmpeg -i input.mov \
  -vf "fps=15,scale=1200:-1:flags=lanczos" \
  -loop 0 docs/hero.gif

# Or use gifski for a smaller, higher-quality output:
brew install gifski
gifski --width 1200 --fps 15 -o docs/hero.gif input.mov
```

Target under 5 MB for fast README loading. Test on mobile — reviewers will
view the README on a phone.

### A good question to demo with

Pick something that exercises the dictionary and the map pan, e.g.:

> "Tell me about Tāmaki Makaurau."

That gets you the cloned voice, the pronunciation dictionary firing on
"Tāmaki Makaurau", a real tool call (`get_location_detail`), and the map
panning to Auckland.

## location-images/ (intentionally absent — forward-compat data field only)

`mcp_server/data/locations.json` includes a `hero_image` field per location
pointing to `/images/locations/<id>.jpg`. **The shipped frontend deliberately
doesn't display these** — its design is a hand-drawn NZ canvas with red pins,
which is the intentional aesthetic. The data field is kept as a forward-compat
placeholder for any future UI that wants real photography; no images are
shipped with the repo and the directory is intentionally absent.

If you fork this and want to add photography, the canonical location is
`frontend/public/images/locations/<id>.jpg`. Use Unsplash or Pexels (CC0 /
permissive) and add an `ATTRIBUTIONS.md` alongside.
