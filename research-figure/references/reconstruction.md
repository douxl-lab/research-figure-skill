**Canonical v1:** `rfs.py reconstruction-package --spec ... --bundle ... --design-notes ... --out ...` requires the real producer bundle and an image-bound note. It verifies the immutable original scientific fingerprint, all bundle hashes, and that a native artifact has not yet been generated. See [canonical-exchange](canonical-exchange.md). Below: legacy v0.1 packaging details.

# 三源协同重建合同（FigureSpec + Image + Written Guidance）

The editable builder receives three complementary sources:

1. **FigureSpec** — binding scientific nodes/edges, exact labels, data/evidence status and prohibited claims.
2. **Visual reference** — actual user-selected image, visual spatial hierarchy, proportions, palette, composition, assets. Do not treat invisible details as observable.
3. **Textual design notes** — precise per-region and per-object guidance: relative bounds, layer ordering, connector ports and lanes, typography, original assets, what to preserve/change. This must describe the *actual image after inspection*; use `assets/design-notes-template.md`.

## How to use

- Review candidates and pick a preferred composition. Don't silently interpret "nice image" as permission to make a PPTX.
- Author `design-notes.md` after **viewing the chosen image**. Do not invent measurements or phantom objects. Detail each important region, its reading purpose, object inventory, native/raster classification and connector routing.
- Use `rfs.py reconstruction-package --spec ... --reference ... --design-notes ... --backend paper-fig --approved --out ...` *only when the user approved that exact visual version*. Without `--approved`, the package remains unapproved.
- The packaging script copies image and notes, snapshots FigureSpec, writes an explicit reconstruction guide, and produces SHA256 receipt. Run `rfs.py audit-package --package ...` to verify **integrity**, not native editability.
- Pass the *whole package* to the installed native backend. Prefer paper-fig for editable PPTX if it has the required runtime; Sivia for supported live native editors, subject to its noncommercial license; draw.io if a live backend is actually available.

## Discrepancy precedence

1. **Science > aesthetics**: scientific topology and real source results outrank image-generated arrows, text or implied evidence.
2. **Approved composition > default style**: when science does not conflict, do not redesign layout or color because an editor's generic style guide prefers something else.
3. **Explicit notes clarify the image**: for internal object types, exact ports and text behavior that the image cannot convey, use the written notes. If notes contradict scientific source, flag and stop the affected element.

## Object and rendering verification

Rebuild labels, formulas, modules and connectors using native semantic objects as much as the backend genuinely supports. Allow atomic raster artwork only where native reconstruction is impractical, with disclosed scope and source. Real remote-sensing fields/masks/predictions must remain *original images*, not regenerated approximations. Never flatten the whole figure as one image and call it fully editable.

The source file must be re-opened/rendered by an actual importer. Verify scientific label coverage, objects, arrow endpoint attachment, no clipping/crossing, layer order and text legibility at target physical width. After each scoped repair, rerender that native source. A separate PNG approximation is not proof of a PPTX rendering.

**Status:** `READY_FOR_BACKEND_HANDOFF_NOT_EXECUTED` means precisely that. User-approved image is a *design lock*, not verification that its scientific structure is true. `audit-package` can return integrity PASS while editability and target rendering remain PENDING.