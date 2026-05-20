# GeoTrave Frontend Development Plan

## Purpose

This document tracks the short-term frontend plan after the travel planning workspace prototype. It should stay practical and updated as design decisions become implementation tasks.

The current product direction is:

- Left side: Agent conversation and user steering.
- Right side: a collaborative planning canvas for map context, notes, tips, decisions, images, and timeline material.
- The canvas should eventually be driven by structured planning data, not hard-coded visual blocks.

## Current Design Decision

The Agent should not output pixel-level layout such as fixed `x` and `y` positions.

Instead, the system should separate:

1. Semantic planning data: places, activities, hotels, meals, route segments, decisions, tips, media, and timeline events.
2. Relationship data: which tip affects which place, which decision affects which day, which route segment connects which points.
3. Frontend layout: responsive placement, grouping, line routing, collision handling, drag state, and visual hierarchy.

This keeps the Agent responsible for planning meaning, while the frontend owns visual layout.

## Short-Term Scope

The next frontend work should focus on turning the current demo into a maintainable foundation, not building the full product at once.

### Phase 1: Stabilize The Prototype

Goal: keep the current visual direction, but make the implementation easier to change.

Tasks:

- Extract the current demo into a small set of components:
  - `TravelWorkspace`
  - `AgentPanel`
  - `PlanningBoard`
  - `CanvasArea`
  - `CanvasCard`
  - `TravelTimeline`
  - `Composer`
- Move demo data out of JSX rendering code.
- Keep the current two-region layout directly on the page, without wrapping both regions in large floating cards.
- Preserve the latest accepted visual choices:
  - left conversation area around a 2:3 relationship with the canvas;
  - dotted canvas background;
  - map-centered planning board;
  - simple segmented travel timeline;
  - richer typography than a single default font.

Deliverable:

- The demo still looks close to the accepted version.
- The code is split enough that future changes do not require editing one large component.

### Phase 2: Introduce Mock CanvasPlan

Goal: render the same demo from a structured local object.

Create a frontend-only `CanvasPlan` mock that includes:

- `nodes`: canvas items such as places, tips, decisions, media cards, and summary notes.
- `edges`: semantic links between nodes and map anchors.
- `timeline`: arrival, lodging, activities, meals, checkout, departure, and buffer events.
- `map`: center, image/source metadata, route segments, and point anchors.

This phase should avoid backend changes. The point is to validate whether the data shape can drive the UI.

Deliverable:

- `CanvasArea` and `TravelTimeline` render from mock data instead of scattered hard-coded JSX.
- Adding a new mock node should require changing data, not layout code.

### Phase 3: Define Frontend Rendering Rules

Goal: make CanvasArea support more source types without redesigning each time.

Initial rendering rules:

- Place and accommodation nodes should prefer map proximity.
- Tips should visually connect to the place, route segment, or day they affect.
- Decision nodes should be visually distinct from informational notes.
- Timeline events should stay on the timeline, not mixed into the map canvas.
- Media cards should support missing images with a designed fallback state.
- Connections should be derived from anchors and container measurements, not hand-aligned constants.

Deliverable:

- A small renderer that maps `node.type` to the correct visual component.
- A connection layer that can draw lines from structured relationships.

### Phase 4: Prepare For Backend Integration

Goal: make the frontend ready for a future Agent-produced canvas artifact.

Tasks:

- Draft a TypeScript `CanvasPlan` type in the frontend.
- Add lightweight validation at the API boundary once backend integration begins.
- Keep layout fields optional and frontend-owned.
- Support a stable `id` for every node, edge, and timeline event.

Deliverable:

- The frontend can accept a future `canvas_plan` response field without major redesign.

## Not In Short-Term Scope

These are important, but should not block the next prototype cleanup:

- Full drag-and-drop editing.
- Persistent user canvas edits.
- Real map SDK integration.
- Multi-user collaboration.
- Backend Agent graph changes.
- CanvasPlan conflict resolution between user edits and Agent updates.

## Open Questions

- Should user-created notes and Agent-created notes share the same node model with different `source` values?
- Should route geometry be stored as map coordinates, polyline data, or both?
- How much layout memory should be persisted after the user manually moves items?
- Should the timeline be a separate artifact or part of the same CanvasPlan?
- Which backend node should eventually compose the CanvasPlan artifact: `planner`, a new `canvas_composer`, or an API adapter layer?

## Immediate Next Step

Refactor the current demo into the Phase 1 component structure while preserving the accepted visual result.
