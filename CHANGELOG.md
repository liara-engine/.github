# Changelog

## [0.3.0](https://github.com/liara-engine/.github/compare/v0.2.0...v0.3.0) (2026-07-17)


### Features

* **abi:** ABI CI tools ([#8](https://github.com/liara-engine/.github/issues/8)) ([1fb4e77](https://github.com/liara-engine/.github/commit/1fb4e7761b8cf2764ea6746f72a8c9d5470d2003))


### Bug Fixes

* **docs:** update documentation hub link in README ([bdcc94f](https://github.com/liara-engine/.github/commit/bdcc94f282b62a60b5e2e2cb824185bec1bf627c))

## [0.2.0](https://github.com/liara-engine/.github/compare/v0.1.1...v0.2.0) (2026-07-11)


### Features

* **tags:** add workflows for managing preview tags on pull requests ([a13824b](https://github.com/liara-engine/.github/commit/a13824bd0578adbdabc726fe7d48c920a3e415d3))
* **validate-manifest:** add workflow for validating JSON manifest files ([47002d3](https://github.com/liara-engine/.github/commit/47002d368cc09112b0f38efefb71f8cb1242e44d))


### Bug Fixes

* **cleanup-preview-tags:** add missing checkout step ([53efcb9](https://github.com/liara-engine/.github/commit/53efcb9b37cf2c9e0f2b251538253060fa20177f))
* **commitlint:** rename workflow and update runner version to ubuntu-24.04 ([df66418](https://github.com/liara-engine/.github/commit/df66418a9e1f6e33db98a7dc7bc920535759fb37))
* **preview-tags:** add sticky comment for preview tag creation on pull requests ([5a494a4](https://github.com/liara-engine/.github/commit/5a494a49bb9f68cdf49bda8f713fe4b47b9d6764))
* **preview-tags:** update permissions to allow write access for pull requests ([a32a077](https://github.com/liara-engine/.github/commit/a32a077b532ad603884375e8029576bc9ccbfbb4))

## [0.1.1](https://github.com/liara-engine/.github/compare/v0.1.0...v0.1.1) (2026-06-18)


### Bug Fixes

* **release-please:** update runner version to ubuntu-24.04 and adjust permissions ([feb1840](https://github.com/liara-engine/.github/commit/feb1840a9f3750dcd88b0d5dd1066089f5e2ef6a))
* **release-please:** use the correct name for tag ([0bce758](https://github.com/liara-engine/.github/commit/0bce758d3593b7b29b5a37f76aba4dc5559c9e46))

## [0.1.0](https://github.com/liara-engine/.github/compare/v0.0.9...v0.1.0) (2026-06-18)


### Features

* **clean-ghcr:** refactor workflow to be reusable with input parameters ([397d8ad](https://github.com/liara-engine/.github/commit/397d8adcdba24b3909ed65f81b8260da0dd3de8f))
* **commitlint:** add commitlint configuration and reusable workflow ([7f090f7](https://github.com/liara-engine/.github/commit/7f090f7f4b68c90f2df91f60983785f1f509e703))
* **commitlint:** add commitlint workflow for pull requests and rename release workflow ([185c578](https://github.com/liara-engine/.github/commit/185c578b96733c4f1c3876bdf52c1aead772a947))
* **commitlint:** enhance reusable commitlint workflow with detailed results reporting ([5971dd4](https://github.com/liara-engine/.github/commit/5971dd4e2c15426d0415d6acdc0ce78050d32603))
* **release:** add release-please configuration and workflow ([87fd6e9](https://github.com/liara-engine/.github/commit/87fd6e921c95b895580a7f512ccdd990661b6c6c))
* **workflow:** add scheduled job to clean untagged container images ([6ffb447](https://github.com/liara-engine/.github/commit/6ffb447e9d5ba6a01af30110a20960dad30ce5fd))


### Bug Fixes

* **commitlint:** correct variable name from result to results in reusable commitlint workflow ([9169f2d](https://github.com/liara-engine/.github/commit/9169f2d3433400c2a29bf4d1793886b8df2209b7))
* **commitlint:** update commitlint workflow to use path for comment file ([b2c5cf9](https://github.com/liara-engine/.github/commit/b2c5cf92c074e353d81f0d9de43c387d60f2ce4c))
* **release:** update commitlint workflow reference to reusable-deploy-docs ([ad3eb4a](https://github.com/liara-engine/.github/commit/ad3eb4a5ac488939c887ce45db76f3c2e99a2164))
* **release:** update token reference in release workflow to use ORG_RELEASE_PLEASE_TOKEN ([d6a7b69](https://github.com/liara-engine/.github/commit/d6a7b69a3d99c2e5b3f93d92d7a993bd189f64c0))
* **workflow:** update package listing command in clean-ghcr.yml ([c45b6f5](https://github.com/liara-engine/.github/commit/c45b6f517a04f29dab8af7af1ced2b67025a7378))
