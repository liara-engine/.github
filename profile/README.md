# Liara Engine

> A modern 3D game engine, built from scratch in C++ with Vulkan.
> Modular by construction, cross-platform, openly developed.

---

## About

Liara Engine is a personal learning project that grew into something
bigger. It is a 3D game engine composed of independently developed
modules that communicate through a stable C ABI, allowing in
principle for any module to be reimplemented in another language.

The project is openly developed under the MIT license, with a clear
roadmap, explicit design documents, and an honest scope: it aims to
be a clean engine that lets a determined developer ship a small 3D
game by version 1.0, not a Unity competitor.

---

## Repositories

The engine is split across several repositories, each with a
focused responsibility.

### Engine modules

### Repositories

| Repository                                                             | What it owns                                                                   |
|------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`liara`](https://github.com/liara-engine/liara)                       | The launcher, the workspace tooling, and the shared documentation. Start here. |
| [`liara-interfaces`](https://github.com/liara-engine/liara-interfaces) | The C ABI contract shared by every module. Header-only.                        |
| [`liara-core`](https://github.com/liara-engine/liara-core)             | ECS, math, logger, settings, event bus, loop primitives.                       |
| [`liara-platform`](https://github.com/liara-engine/liara-platform)     | Window, input, OS signals, timing.                                             |
| [`liara-renderer`](https://github.com/liara-engine/liara-renderer)     | Vulkan rendering.                                                              |
| [`liara-assets`](https://github.com/liara-engine/liara-assets)         | Asset loading, decoding, lifetime.                                             |
| [`liara-audio`](https://github.com/liara-engine/liara-audio)           | Playback and mixing.                                                           |
| [`docs-shared`](https://github.com/liara-engine/docs-shared)           | Templates and assets shared by every module's documentation.                   |

### Infrastructure

- **[docs-shared](https://github.com/liara-engine/docs-shared)** —
  shared documentation templates and the navigation bar that ties
  per-module docs to the central hub.
- **[.github](https://github.com/liara-engine/.github)** —
  organization-wide templates and reusable GitHub Actions workflows.

---

## Where to Start

If you are **curious** about the project, read the
[meta repository's README](https://github.com/liara-engine/liara)
for a complete overview.

If you want to **understand the design**, the
[architecture document](https://github.com/liara-engine/liara/blob/main/docs/ARCHITECTURE.md)
is the foundational read. The
[modules document](https://github.com/liara-engine/liara/blob/main/docs/MODULES.md)
describes how the project is split.

If you want to **see where the project is going**, the
[roadmap](https://github.com/liara-engine/liara/blob/main/docs/ROADMAP.md)
is precise about milestones up to v1.0 and intentionally vague
about what comes after.

If you want to **build it locally**, the
[bootstrap guide](https://github.com/liara-engine/liara/blob/main/docs/BOOTSTRAP.md)
walks through setup on Arch Linux and Windows 11.

If you want to **contribute**, the
[contributing guide](https://github.com/liara-engine/liara/blob/main/docs/CONTRIBUTING.md)
describes the workflow.

---

## Project Status

Liara is in **Phase 0**: the bootstrap phase, where the
infrastructure (repositories, CI, documentation, tooling) is being
put in place.
Only bootstrap/test code exists so far; no feature code under the
versioned milestones has been written yet.

The roadmap targets:

- **v0.1** — "Hello Triangle" through the modular pipeline.
- **v1.0** — first shippable game milestone.
- **v2.0** — production-ready: ambitious projects become realistic.

The cadence is **milestone-driven, not calendar-driven**. Pauses
happen and are part of the project's normal mode of operation.

---

## Technical Highlights

- **Language**: C++20, with C ABI at module boundaries.
- **Graphics**: Vulkan 1.3 via Vulkan-Hpp and VMA.
- **Architecture**: hand-written ECS, render-packet pattern, modular
  by construction.
- **Platforms**: Linux (Arch primary), Windows 11.
- **Build**: CMake 3.29+ with presets, vcpkg in manifest mode.
- **CI/CD**: GitHub Actions with reusable workflows, release-please.
- **Documentation**: Doxygen for API, mdBook for users, hosted on
  Cloudflare Workers.

---

## License

All repositories under this organization are released under the
**MIT License**, unless explicitly stated otherwise in a specific
repository's `LICENSE` file.

---

## Connect

- **Discussions** for general questions and ideas: on the
  [meta repository](https://github.com/liara-engine/liara/discussions).
- **Issues** for bugs and feature requests: on the relevant module's
  repository.
- **Documentation hub**: [liara-engine.liara-engine-documentation.workers.dev](https://liara-engine.liara-engine-documentation.workers.dev)

---

<div align="center">

*A personal project, openly developed in case it is useful to anyone else.*

</div>
