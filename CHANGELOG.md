# CHANGELOG

<!-- version list -->

## v0.9.0 (2026-01-05)

### Features

- Enhance const field auto-injection to completely hide const fields
  ([`dfef252`](https://github.com/ScaleWoB/ScaleWoB/commit/dfef252c075b915bdac6e4c1f671498f0d960ac7))

- **automation**: Add const field auto-injection for task parameters
  ([`0a293d6`](https://github.com/ScaleWoB/ScaleWoB/commit/0a293d628a95c96ea67c89bd2f17a68f8f60e716))


## v0.8.1 (2025-12-31)

### Refactoring

- Improve context manager support and environment reset
  ([`bdaa7f8`](https://github.com/ScaleWoB/ScaleWoB/commit/bdaa7f811d3183cfe4e0111d0be37ee7df0e5d4f))


## v0.8.0 (2025-12-31)

### Chores

- Add jsonschema dependency and update lock file
  ([`ef0cf29`](https://github.com/ScaleWoB/ScaleWoB/commit/ef0cf2930c3bd71099a72015e7c933c115ea5d62))

- Update beads issue tracking for completed tasks
  ([`ef0cf29`](https://github.com/ScaleWoB/ScaleWoB/commit/ef0cf2930c3bd71099a72015e7c933c115ea5d62))

### Documentation

- Reorganize README and update API documentation
  ([`ef0cf29`](https://github.com/ScaleWoB/ScaleWoB/commit/ef0cf2930c3bd71099a72015e7c933c115ea5d62))

### Features

- Add automatic task fetching and parameter validation
  ([`314201a`](https://github.com/ScaleWoB/ScaleWoB/commit/314201af8ba080c0da002f230ad2a492ce2e7db8))

### Breaking Changes

- Finish_evaluation() now automatically validates params against task schema when available.
  Requires jsonschema package for validation (raises CommandError if not installed).


## v0.7.1 (2025-12-22)

### Bug Fixes

- **automation**: Use execute_script instead of execute for JavaScript execution
  ([`4c83075`](https://github.com/ScaleWoB/ScaleWoB/commit/4c830750396e4b46e49369a764f93b0d4208021b))


## v0.7.0 (2025-12-16)

### Chores

- Add AI assistant documentation and beads issue tracking setup
  ([`ccfbf9e`](https://github.com/ScaleWoB/ScaleWoB/commit/ccfbf9e5b70b9ec9616894816206c9b7b9494be9))

- **.gitignore**: Add exceptions for CLAUDE.md and AGENTS.md
  ([`1bf0d9b`](https://github.com/ScaleWoB/ScaleWoB/commit/1bf0d9bc49925216e7f196e788dc8c2e6e0a750c))

- **beads**: Record closed issues from task-centric API migration
  ([`14a372a`](https://github.com/ScaleWoB/ScaleWoB/commit/14a372a4fa82d21ab232148af4361c60a8e2146a))

### Documentation

- Update README for task-centric API migration
  ([`eb2f284`](https://github.com/ScaleWoB/ScaleWoB/commit/eb2f28418dc71ec88969a9ded69d79f34f5273c7))

### Features

- Migrate to task-centric API with taskId support
  ([`c4a71d4`](https://github.com/ScaleWoB/ScaleWoB/commit/c4a71d452abf26c1206315c1b81475df86652d6c))

### Breaking Changes

- Replace fetch_environments() with fetch_tasks() that returns a flat list of tasks with environment
  context. Add task_id parameter to finish_evaluation() to support multiple tasks per environment.


## v0.6.0 (2025-12-10)

### Documentation

- Add platform parameter documentation and mobile-specific behavior notes
  ([`8d0c5cf`](https://github.com/ScaleWoB/ScaleWoB/commit/8d0c5cfd389aed5600568d62761d86e0c6327899))

### Features

- **automation**: Add platform-agnostic interaction support with mobile and desktop modes
  ([`a3d06b1`](https://github.com/ScaleWoB/ScaleWoB/commit/a3d06b1cd1016f63f9d5a9007affccede275a190))


## v0.5.0 (2025-12-02)

### Documentation

- Fix docstrings and API documentation inconsistencies
  ([`26f49e7`](https://github.com/ScaleWoB/ScaleWoB/commit/26f49e755c2f5421666b9a3101f6d678aae7385a))

### Features

- **dev**: Add Jupyter notebook support and update development dependencies
  ([`b54ec12`](https://github.com/ScaleWoB/ScaleWoB/commit/b54ec12ca278c4a98415d628d36da4df60e2b10e))


## v0.4.1 (2025-11-28)

### Documentation

- Add environment discovery API documentation
  ([`b0adac0`](https://github.com/ScaleWoB/ScaleWoB/commit/b0adac070c986e299b0305cac7610891b8166e73))

### Refactoring

- **automation**: Simplify browser support and enhance command execution
  ([`8d2921e`](https://github.com/ScaleWoB/ScaleWoB/commit/8d2921e355532c856ffbbd07e7ca5c1143dacfe3))


## v0.4.0 (2025-11-27)

### Build System

- **poe**: Add semantic-release tasks for version management
  ([`e23ca86`](https://github.com/ScaleWoB/ScaleWoB/commit/e23ca864c0a982fa6b2b5066ad8114f290564474))

### Features

- **api**: Add fetch_environments function for environment metadata
  ([`0a79766`](https://github.com/ScaleWoB/ScaleWoB/commit/0a797661b9424e63eac12481c27656c9be1b5319))

- **automation**: Add stealth mode options to Chrome driver
  ([`077d422`](https://github.com/ScaleWoB/ScaleWoB/commit/077d422f2b99d88766379a1be980f75113737a17))


## v0.3.2 (2025-11-27)

### Build System

- **semantic-release**: Add refactor to patch version bump tags
  ([`6206290`](https://github.com/ScaleWoB/ScaleWoB/commit/6206290576d1b001678c61992281188607cf9cee))

### Refactoring

- **automation**: Simplify start_evaluation by removing Play Mode toggle
  ([`9c5bb97`](https://github.com/ScaleWoB/ScaleWoB/commit/9c5bb978181a9ebad9cda0b23fc9d30e0ab70e25))


## v0.3.1 (2025-11-25)

### Bug Fixes

- Use dynamic version and correct screenshot scale factor
  ([`b0efcfb`](https://github.com/ScaleWoB/ScaleWoB/commit/b0efcfb94641490a54df05ad9b2cf1dc8c190110))


## v0.3.0 (2025-11-25)

### Build System

- **release**: Update semantic-release build command to upgrade lock file
  ([`4acdf6b`](https://github.com/ScaleWoB/ScaleWoB/commit/4acdf6bad1f423a470dcf453a6d0f5cb41f1cd05))

### Features

- **automation**: Add configurable screenshot quality with coordinate scaling
  ([`bd0e650`](https://github.com/ScaleWoB/ScaleWoB/commit/bd0e650fc110a7ce92b86975cf7cd34247e51992))

- **automation**: Maximize browser window on initialization
  ([`1add2fc`](https://github.com/ScaleWoB/ScaleWoB/commit/1add2fca10ee338145d79f44b90a816348dfcff6))


## v0.2.0 (2025-11-22)

### Build System

- **ci**: Add python-semantic-release for automated versioning
  ([`4f7c33c`](https://github.com/ScaleWoB/ScaleWoB/commit/4f7c33cc4b99a6054065ee4b14316ddb2495228f))

### Documentation

- Add comprehensive README with SDK documentation
  ([`b98e420`](https://github.com/ScaleWoB/ScaleWoB/commit/b98e420aa15e9fc65c44f7f68d95963eb46540fe))

### Features

- **automation**: Add trajectory tracking for automatic action recording
  ([`9037717`](https://github.com/ScaleWoB/ScaleWoB/commit/903771757e78405b5f137dce8f83103679131c44))


## v0.1.0 (2025-11-19)

- Initial Release
