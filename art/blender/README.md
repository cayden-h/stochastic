# Agent House models

The four Agent House characters (Brief Reader, Mapper, Preparer, Reviewer) as the Agents page plays them.
The console loads the exported files from `frontend/public/agents/<key>.glb` with three.js.

## Files

- `source/<key>.glb` is the clay model from the team's Figma Make prototype ("The Agent House · 3D V2", frame V3-6 Agents).
  The build reads it and never changes it.
- `build_agents.py` rigs, animates, and exports every model.
- `<key>.blend` is the Blender file the build saves, with the rig, the shape key, and one action per clip.
  Open it to look at or adjust a clip, then rerun the build so the `.glb` matches.

## Regenerate

From the repository root, with Blender 5.2 or later:

```sh
blender -b --factory-startup -P art/blender/build_agents.py
```

To rebuild one model, add its key after `--`:

```sh
blender -b --factory-startup -P art/blender/build_agents.py -- mapper
```

The build writes `art/blender/<key>.blend` and `frontend/public/agents/<key>.glb`.
The `.glb` is plain glTF binary with no Draco or meshopt compression, so the page needs no decoder and makes no network request beyond its own files.

## What the build adds

Each model is one mesh with vertex colors and two materials (body and eyes).
The build keeps the mesh, the colors, and the materials as they are, and adds:

- A small armature.
  `root` moves, sways, and turns the whole body, with its pivot at the feet.
  `body` squashes and stretches, also from the feet.
  `head` nods and tilts the upper half, blended smoothly into the body over the middle.
- A `blink` shape key that closes each eye toward its own middle.
- One action per clip, keyed on every frame from the formulas in `build_agents.py`, so each loop closes exactly.

## Clips

All clips are at 30 fps.

| Clip | Length | Plays | What it does |
| --- | --- | --- | --- |
| `idle` | 4.0 s | loop | A slow breathing bob and sway, a small head drift, one blink. |
| `working` | 1.2 s | loop | A quick bob with squash and stretch and a typing nod toward the desk. |
| `asking` | 1.85 s | loop | Two bounces with squash on landing, a sway, and a quizzical head tilt up at the human. |
| `talking` | 1.2 s | loop | Two nods and small syllable pulses, leaning toward the listener. |
| `done` | 1.5 s | once | Crouch, jump with a full turn, land, and settle back to rest. |

The page (`frontend/src/components/agent-house/house.ts`) plays them with an `AnimationMixer` and crossfades between states in 0.35 s.
After `done` finishes, the agent rests in `idle` with its done bubble still up.
The pointer glance and the hover hop are added on top in code, as in the prototype.
