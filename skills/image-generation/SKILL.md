---
name: factory-image-generation
description: Generate or edit project-bound raster assets from an approved visual contract.
---

# Image generation

Use the harness's built-in OpenAI image-generation tool for approved raster
assets such as game art, textures, sprites, illustrations, mockups, or cutouts.
It uses the configured subscription and does not require an API key. If that tool is not
available, return `blocked`; never silently switch to an API-key CLI, fabricate a
receipt, or replace required art with emoji, generic system symbols, or crude
code-drawn placeholders.

1. Read the approved `visual_contract`, assigned asset entries, consuming code,
   platform constraints, and inspected references. References guide principles;
   do not copy distinctive copyrighted expression, brands, characters, or text.
2. Choose generate versus edit. Prefer existing project-native vector/code assets
   when they already satisfy the contract; use image generation only for genuine
   bitmap work.
3. Shape each prompt around intended use, subject, style, composition, lighting,
   palette, texture, exact text if any, required invariants, and avoid list.
4. Generate one asset or coherent variant set at a time. Inspect subject,
   composition, edge quality, text, transparency, consistency, and platform fit;
   iterate with one targeted change.
5. Save every selected project asset inside the assigned repository paths. Do not
   overwrite existing assets unless the approved task requires replacement, and
   do not leave a referenced asset only in a global generated-images directory.
   For transparent-background web or game assets, request genuine transparency,
   inspect the alpha channel, and preserve it in the project file; a white or
   checkerboard background is not transparency.
6. Record the final prompt, generation mode, selected output path, dimensions,
   alpha requirement, and visual inspection in the lane receipt or a small
   repository-local provenance file when the plan assigns one.

The integrated build, screenshots, and video—not the generation call—prove the
asset works in context. Generated output remains subject to the same originality,
accessibility, file-scope, test, and independent-review gates as code.
