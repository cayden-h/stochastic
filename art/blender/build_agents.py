"""Rig and animate the four Agent House characters, then export them for three.js.

Run headless from the repo root:

    blender -b --factory-startup -P art/blender/build_agents.py

For each agent it imports the clay model from art/blender/source/<key>.glb (the Figma Make prototype's file, which
this script never changes), keeps its mesh, vertex colors, and materials as they are, and adds:

- a small armature: `root` (whole-body move, sway, and spin, pivot at the feet), `body` (squash and stretch, pivot at
  the feet), and `head` (the upper half: nods and tilts, blended smoothly into the body);
- a `blink` shape key that closes the eyes toward their middle;
- one action per clip, each keyed on every frame from the formulas below, so every loop closes exactly.

It saves art/blender/<key>.blend and writes frontend/public/agents/<key>.glb (plain glTF binary, no compression, so
three.js loads it with GLTFLoader alone and no decoder download).

The clips, at 30 fps (lengths in seconds):

- idle (4.0, loop): a slow breathing bob and sway, one blink.
- working (1.2, loop): a quick bob with squash and stretch and a typing nod toward the desk.
- asking (1.85, loop): two bounces with squash on landing, a sway, and a quizzical head tilt up at the human.
- talking (1.2, loop): two nods and small syllable pulses, leaning toward the listener.
- done (1.5, once): crouch, jump with a full turn, land, settle back to rest.
"""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE = os.path.join(HERE, "source")
OUT = os.path.join(REPO, "frontend", "public", "agents")
AGENTS = ["brief-reader", "mapper", "preparer", "reviewer"]
FPS = 30
TAU = 2 * math.pi

# Blender axes: X to the agent's left-right, -Y is the agent's front (glTF +Z), Z is up.
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def smoothstep(a: float, b: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def ease_out_cubic(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def blink(t: float, at: float, length: float = 0.16) -> float:
    """0 open, 1 closed: a quick close and open centred on `at`."""
    d = abs(t - at) / (length / 2)
    return max(0.0, 1 - d) ** 0.7 if d < 1 else 0.0


def world_rot(pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0) -> Quaternion:
    """A rotation in world terms: pitch nods the top toward the front (-Y), roll tips it sideways, yaw turns around Z."""
    q = Quaternion(Z, yaw) @ Quaternion(Y, roll) @ Quaternion(X, pitch)
    return q


# ------------------------------------------------------------------ clips
# Each clip returns, for time t, the pose: root (lift, pitch, roll, yaw), body (squash: + is taller and thinner),
# head (pitch, roll), and blink. Amounts are in model units (the models are about 2 units tall).

def pose(lift=0.0, pitch=0.0, roll=0.0, yaw=0.0, squash=0.0, hpitch=0.0, hroll=0.0, closed=0.0, fwd=0.0):
    return dict(lift=lift, pitch=pitch, roll=roll, yaw=yaw, squash=squash, hpitch=hpitch, hroll=hroll, closed=closed, fwd=fwd)


def idle(t, L):
    p = TAU * t / L
    return pose(lift=0.065 * math.sin(p), roll=0.035 * math.sin(p + 1.0), squash=0.012 * math.sin(2 * p),
                hroll=0.03 * math.sin(p + 2.0), hpitch=0.015 * math.sin(2 * p + 0.5), closed=blink(t, 2.6))


def working(t, L):
    p = TAU * t / L
    return pose(lift=0.08 * math.sin(p), squash=0.035 * math.sin(2 * p), pitch=0.04,
                hpitch=0.06 + 0.05 * math.sin(4 * p), hroll=0.025 * math.sin(p), closed=blink(t, 0.7))


def asking(t, L):
    p = TAU * t / L
    b = abs(math.sin(p))  # |sin| repeats every half loop: two bounces
    land = (1 - b) ** 4
    return pose(lift=0.29 * b, roll=0.14 * math.sin(p), squash=0.045 * b - 0.07 * land, pitch=-0.05,
                hpitch=-0.08, hroll=0.18 + 0.05 * math.sin(2 * p), closed=blink(t, 1.2))


def talking(t, L):
    p = TAU * t / L
    return pose(lift=0.02 * math.sin(4 * p), pitch=0.05, squash=0.022 * math.sin(4 * p + 0.6),
                hpitch=0.06 + 0.07 * math.sin(2 * p), hroll=0.04 * math.sin(p), closed=blink(t, 0.95), fwd=0.03)


def done(t, L):
    if t < 0.2:  # crouch
        k = ease_out_cubic(t / 0.2)
        return pose(squash=-0.12 * k, hpitch=0.06 * k)
    if t < 0.9:  # jump with a full turn
        u = (t - 0.2) / 0.7
        lift = 0.5 * math.sin(math.pi * u)
        return pose(lift=lift, squash=0.08 * (1 - u) - 0.12 * max(0.0, 1 - u * 6), yaw=TAU * ease_out_cubic((t - 0.2) / 0.9),
                    hpitch=-0.08 * math.sin(math.pi * u))
    if t < 1.1:  # land
        u = (t - 0.9) / 0.2
        return pose(squash=-0.1 * math.sin(math.pi * u), yaw=TAU * ease_out_cubic((t - 0.2) / 0.9))
    u = (t - 1.1) / (L - 1.1)  # settle
    return pose(squash=0.03 * math.sin(TAU * u * 1.5) * (1 - u) ** 2, yaw=TAU * ease_out_cubic(min(1.0, (t - 0.2) / 0.9)),
                closed=blink(t, 1.3))


CLIPS = [("idle", 4.0, idle, True), ("working", 1.2, working, True), ("asking", 1.85, asking, True),
         ("talking", 1.2, talking, True), ("done", 1.5, done, False)]


# ------------------------------------------------------------------ build

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups next to the sources


def add_blink(obj):
    """A shape key that squeezes each eye toward its own middle, height only, so the eyes stay on the face."""
    me = obj.data
    eye_mats = [i for i, m in enumerate(me.materials) if m and m.name.lower().endswith("eye")]
    eye_verts = set()
    for poly in me.polygons:
        if poly.material_index in eye_mats:
            eye_verts.update(poly.vertices)
    obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name="blink", from_mix=False)
    for side in (-1, 1):
        vs = [i for i in eye_verts if me.vertices[i].co.x * side > 0]
        if not vs:
            continue
        zs = [me.vertices[i].co.z for i in vs]
        mid = (min(zs) + max(zs)) / 2
        for i in vs:
            co = me.vertices[i].co
            key.data[i].co = Vector((co.x, co.y, mid + (co.z - mid) * 0.08))
    return len(eye_verts)


def add_rig(obj):
    me = obj.data
    zs = [v.co.z for v in me.vertices]
    zmin, zmax = min(zs), max(zs)
    h = zmax - zmin
    arm_data = bpy.data.armatures.new(f"{obj.name} rig")
    arm = bpy.data.objects.new(f"{obj.name} rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    root = eb.new("root"); root.head = (0, 0, zmin); root.tail = (0, 0, zmin + 0.2 * h)
    body = eb.new("body"); body.head = (0, 0, zmin); body.tail = (0, 0, zmin + 0.5 * h); body.parent = root
    head = eb.new("head"); head.head = (0, 0, zmin + 0.45 * h); head.tail = (0, 0, zmax); head.parent = body
    for b in (root, body, head):
        b.roll = 0.0
    bpy.ops.object.mode_set(mode="OBJECT")

    # Weights: the lower body follows `body`, the upper half follows `head`, blended over the middle so it bends softly.
    gb = obj.vertex_groups.new(name="body")
    gh = obj.vertex_groups.new(name="head")
    for v in me.vertices:
        w = smoothstep(0.35, 0.8, (v.co.z - zmin) / h)
        if w < 1:
            gb.add([v.index], 1 - w, "REPLACE")
        if w > 0:
            gh.add([v.index], w, "REPLACE")
    obj.parent = arm
    mod = obj.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    return arm, h


def key_clip(arm, obj, name, length, fn, h):
    frames = int(round(length * FPS))
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    key = obj.data.shape_keys
    key.animation_data_create()
    key.animation_data.action = act
    pb = arm.pose.bones
    rest = {n: arm.data.bones[n].matrix_local.to_quaternion() for n in ("root", "body", "head")}
    for b in pb:
        b.rotation_mode = "QUATERNION"
    prev = {}
    for f in range(frames + 1):
        t = f / FPS
        p = fn(t, length)
        # root: lift and lean, turn about the feet
        qw = world_rot(pitch=p["pitch"], roll=p["roll"], yaw=p["yaw"])
        loc_world = Vector((0, -p["fwd"] * h, p["lift"]))
        values = {
            "root": (rest["root"].inverted() @ qw @ rest["root"], rest["root"].inverted() @ loc_world, Vector((1, 1, 1))),
            "body": (Quaternion(), Vector(), Vector((1 - p["squash"] * 0.5, 1 + p["squash"], 1 - p["squash"] * 0.5))),
            "head": (rest["head"].inverted() @ world_rot(pitch=p["hpitch"], roll=p["hroll"]) @ rest["head"], Vector(), Vector((1, 1, 1))),
        }
        for n, (q, loc, scl) in values.items():
            # keep each bone's quaternion on one hemisphere frame to frame, so a full turn interpolates the short way
            if n in prev and prev[n].dot(q) < 0:
                q = -q
            prev[n] = q.copy()
            b = pb[n]
            b.rotation_quaternion = q
            b.location = loc
            b.scale = scl
            b.keyframe_insert("rotation_quaternion", frame=f)
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("scale", frame=f)
        kb = key.key_blocks["blink"]
        kb.value = p["closed"]
        kb.keyframe_insert("value", frame=f)
    # store each clip as an NLA strip so the exporter writes every one, then clear the active action
    for ad in (arm.animation_data, key.animation_data):
        track = ad.nla_tracks.new()
        track.name = name
        track.strips.new(name, 0, act)
        track.mute = True
        ad.action = None
    return frames


def build(agent):
    reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(SOURCE, f"{agent}.glb"))
    obj = next(o for o in bpy.data.objects if o.type == "MESH")
    n_eye = add_blink(obj)
    arm, h = add_rig(obj)
    summary = []
    for name, length, fn, _loop in CLIPS:
        frames = key_clip(arm, obj, name, length, fn, h)
        summary.append(f"{name} {frames}f")
    for b in arm.pose.bones:
        b.rotation_quaternion = Quaternion(); b.location = Vector(); b.scale = Vector((1, 1, 1))
    obj.data.shape_keys.key_blocks["blink"].value = 0
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, int(4.0 * FPS)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, f"{agent}.blend"), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, f"{agent}.glb"), export_format="GLB",
        export_animations=True, export_animation_mode="ACTIONS", export_merge_animation="ACTION",
        export_force_sampling=True, export_optimize_animation_size=False, export_anim_slide_to_zero=True,
        export_skins=True, export_morph=True, export_morph_normal=False, export_def_bones=False,
        export_leaf_bone=False, export_rest_position_armature=True, export_yup=True, export_vertex_color="MATERIAL",
        export_draco_mesh_compression_enable=False,
    )
    print(f"BUILT {agent}: eye verts {n_eye}, height {h:.3f}, clips: {', '.join(summary)}")


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    os.makedirs(OUT, exist_ok=True)
    for a in (only or AGENTS):
        build(a)
