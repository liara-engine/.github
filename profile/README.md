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

- **[liara](https://github.com/liara-engine/liara)** — the meta
  repository: launcher, packaging, documentation hub, and the
  compatibility matrix that ties everything together. **Start here.**
- **[liara-interfaces](https://github.com/liara-engine/liara-interfaces)**
  — header-only repository defining the C ABI contracts between
  modules. The most version-sensitive part of the project.
- **[liara-core](https://github.com/liara-engine/liara-core)** —
  engine foundation: ECS, math, asset management, logger, settings,
  application loop.
- **[liara-renderer](https://github.com/liara-engine/liara-renderer)**
  — Vulkan reference renderer. The graphics backend.
- **liara-editor** *(post-v1.0)* — visual scene editor.
- **liara-physics** *(post-v1.0)* — physics module.

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
put in place. No engine code has been written yet under this
organization; the project is still defining itself.

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
  GitHub Pages.

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
- **Documentation hub**: [liara-engine.github.io](https://liara-engine.github.io)
  *(active once Phase 0 completes).*

---

<div align="center">

*A personal project, openly developed in case it is useful to anyone else.*

</div>
