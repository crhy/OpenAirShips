# OpenAirShips Unreal Diagnostic Report

Date: 2026-05-28

## Scope

This is a static repository diagnostic for the first Unreal milestone in issue #8:

- identify why the current OpenAirShips Unreal work is not reproducible from this repository,
- document the concrete blockers to opening or repairing the level,
- define a clean migration target for a 30-90 second cinematic vertical slice,
- provide a handoff checklist for the next Unreal pass.

I did not launch Unreal Engine from this repository because the repo does not currently contain an Unreal project file or source level assets that can be opened directly.

## Repository Findings

The repository currently contains brand, CAD, print, PDF, website snapshot, and rendered video assets, but not a complete Unreal project.

Relevant findings:

- There is no `.uproject` file in the repository.
- There is no Unreal `Config/`, `Content/`, `Plugins/`, `Source/`, or `Saved/Logs/` tree.
- `CurrentModel/Unreal Level` is a text handoff file with two Google Drive links: one old Unreal level and one current Unreal level.
- `CurrentModel/Blender/2024 Google Docs Link` is also an external Google Drive link rather than a versioned `.blend` source file.
- `CurrentModel/CAD Files/airship pie slice 125.FCStd` is a real FreeCAD archive and can be used as a source model candidate.
- `CurrentModel/Print Files/PieSlice1224.stl` is a real binary STL and can be used as a mesh reference.
- Several `CurrentModel/OldFiles/*` model files are 2-byte newline-only placeholders and cannot be used for migration.
- The `vidz/` folder contains rendered MP4 references. These are useful for visual direction, but they are not editable Unreal source.

## Primary Blockers

### 1. Unreal Project Is External To Git

The most important blocker is that the active Unreal level is stored as a Google Drive link instead of a versioned project folder or release artifact. This prevents contributors from knowing:

- the Unreal Engine version,
- required plugins,
- missing asset paths,
- whether the project depends on Marketplace content,
- whether any source files are absent,
- whether the project fails because of hardware scalability, plugin load errors, corrupt assets, or a bad engine association.

### 2. No Engine Version Contract

Without the `.uproject` file, there is no `EngineAssociation` value. The cleanup pass needs one explicit target, otherwise each contributor may try a different Unreal version and produce incompatible migrations.

Recommended target: Unreal Engine 5.4 or 5.5, unless the existing Drive project already has a newer valid `EngineAssociation`.

### 3. No Asset Manifest

The repo has several useful assets, but no manifest that separates:

- source assets,
- generated/exported assets,
- cinematic reference renders,
- deprecated or broken files,
- external-only assets that still need to be pulled into version control or release storage.

This makes it hard to distinguish "missing plugin" from "missing source asset" during Unreal load failures.

### 4. Laptop Load Reliability Is Undefined

The issue mentions that the level does not load reliably on a laptop. The repository has no current Unreal scalability settings, derived data cache notes, target GPU/RAM profile, or low-spec fallback map. The cinematic pass should intentionally split "working editor project" from "high-end final render."

## Recommended Clean Project Shape

Use a new clean Unreal project instead of trying to keep repairing an unknown external state.

Proposed layout:

```text
Unreal/
  OpenAirShips.uproject
  Config/
  Content/
    OpenAirShips/
      Airship/
        Meshes/
        Materials/
        Blueprints/
      Environment/
        Sky/
        Hangar/
        Platform/
        Lighting/
      Cinematics/
        Sequences/
        Cameras/
      Maps/
        OAS_Diagnostic.umap
        OAS_VerticalSlice.umap
SourceAssets/
  FreeCAD/
  Blender/
  ReferenceVideos/
Deliverables/
  screenshots/
  video/
```

Keep heavy generated files out of normal Git history unless Git LFS is configured. If Git LFS is not used, attach the Unreal source zip to a GitHub Release and store a checksum in the repo.

## Recovery Checklist

1. Download the current Unreal level from the Google Drive link in `CurrentModel/Unreal Level`.
2. Inspect the `.uproject` file before opening it:
   - `EngineAssociation`
   - `Plugins`
   - any missing module names
   - project category/template
3. Open with the matching Unreal version first. Do not auto-upgrade before saving a backup copy.
4. If Unreal reports missing plugins, classify each plugin as:
   - built-in and safe to enable,
   - Marketplace/external and unavailable,
   - unnecessary for the vertical slice and safe to remove.
5. If the project opens but is slow, immediately create `OAS_Diagnostic.umap` with only:
   - one imported airship proxy mesh,
   - one sky/atmosphere setup,
   - one platform or hangar blockout,
   - one camera rail or Level Sequence.
6. If the project does not open, migrate only usable assets into a fresh UE 5.4/5.5 project and leave the old project read-only.
7. Export a current airship mesh from FreeCAD or Blender into FBX or glTF, then import into Unreal with scale documented.
8. Create three material tiers:
   - prototype clay material,
   - brushed metal/hull material,
   - emissive window/interior accents.
9. Create a low-spec editor profile:
   - disable hardware ray tracing,
   - use scalable Lumen or baked lighting for the editor map,
   - keep Nanite only for meshes that benefit from it,
   - use proxy meshes for the first cinematic pass.
10. Save screenshots and a short viewport capture before attempting a high-quality Movie Render Queue output.

## 30-90 Second Vertical Slice Direction

The fastest credible cinematic should avoid building a full world. Build one polished scene with strong composition:

- opening shot: airship silhouette emerging from cloud/sky,
- mid shot: pass over a clean platform or hangar deck,
- hero shot: exterior airship orbit with dramatic sunlight and subtle cloud motion,
- detail shot: window/interior glow or engine/duct detail,
- final shot: pull away into open sky with logo or project title optional.

This is more achievable than a large city/world scene and directly supports the project goal: a beautiful visual direction that can attract contributors.

## Files That Need Owner Confirmation

Before a full Unreal repair pass, the owner should confirm or provide:

- current Unreal project archive from Drive,
- expected Unreal Engine version,
- whether Marketplace assets are allowed,
- license status for every non-original asset,
- whether the cinematic should prioritize realism, stylized concept art, or technical build accuracy,
- target laptop spec that must load the project,
- preferred delivery format: GitHub Release zip, Git LFS, or external asset storage plus manifest.

## Recommended Immediate Next PR

After the Drive project is available locally, the next PR should add:

- `Unreal/OpenAirShips.uproject` or a release manifest with checksum,
- `docs/unreal-asset-manifest.md`,
- `docs/unreal-open-runbook.md`,
- one screenshot proving the diagnostic map opens,
- one known-good target engine version.

That would turn the project from an external-link handoff into a reproducible Unreal collaboration target.
