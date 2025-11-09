# Changelog

All notable changes to this project will be documented in this file.

The format is _sort of_ based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project _sort of_ adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixes

#### crash fixes
* **app:** fix right click crash that i got ([fbfa96c](https://github.com/NSPC911/rovr/commit/fbfa96ca673c57a2f129aea0e98d919069bffbc5))
* **utils-func:** handle NoActiveWorker and WorkerCancelled ([3147fc8](https://github.com/NSPC911/rovr/commit/3147fc8d2b317bb20c844712270d7566c5d2935f))
* **core+app:** fix crashes that i experienced ([e8161ef](https://github.com/NSPC911/rovr/commit/e8161efd725fa6433208306aed602590b592d552))
* **path_utils:** fix opening of non-existent files ([695b63b](https://github.com/NSPC911/rovr/commit/695b63b8d301d71eefde5923ae4d6438b95a665b))

#### lint fixes
* **config:** resolve DOC102 error ([240a937](https://github.com/NSPC911/rovr/commit/240a937860dd3f10965e86879f61bd82f9838db5))
* **pins:** fix ty ([2f728e1](https://github.com/NSPC911/rovr/commit/2f728e129e16551c59881602707cc31b72a6200c))

#### ui fixes
* **clipboard:** auto handle paste button disables ([3f1124f](https://github.com/NSPC911/rovr/commit/3f1124f837b4a3fb869704fec73b1ab426b5c2ba))
* **config:** fix startup icon ([f6da8f0](https://github.com/NSPC911/rovr/commit/f6da8f0e595cfd8b0f47bfdaf13441b5c6d81ad7))
* **file_list:** disable new item button when without permission ([fd1f061](https://github.com/NSPC911/rovr/commit/fd1f061a581a3e731c5d5c1f49cb850362191863))
* **filelist:** fix hist prev not working in empty dirs ([2dca5e6](https://github.com/NSPC911/rovr/commit/2dca5e668f1a41ca86959883624d9865b6639113))
* **filelist:** fix selection on exit select mode ([b2c7a16](https://github.com/NSPC911/rovr/commit/b2c7a16bea27a0e12266475fe9b397c668bcdbc3))
* **path_utils:** prevent drives from being added if it cannot be entered into ([a834331](https://github.com/NSPC911/rovr/commit/a8343313e9b8c35521182ee51bd104a4785171de))
* **new_item_button:** improve toast message ([58fb410](https://github.com/NSPC911/rovr/commit/58fb4101ec1f929fba5b91630a56703716e56adb))
* **pinned-sidebar:** always show search bar ([d8047ed](https://github.com/NSPC911/rovr/commit/d8047ed52c44ce91579c5f6a076606c5d7046299))
* **process:** uses proper panic ([642169d](https://github.com/NSPC911/rovr/commit/642169de6e54e5253937c5c1182d6b086970dc78))
* **style:** fix Images to be one char from sides ([6a1489a](https://github.com/NSPC911/rovr/commit/6a1489aff00c37080fded9c32536b82388dc1860))
* **tabs:** prevent selecting text of tabs ([4f7a9e2](https://github.com/NSPC911/rovr/commit/4f7a9e2bc1c7edd9a4f6227af716775f0a9cdceb))
* **zoxide:** some minor fixes ([85feecb](https://github.com/NSPC911/rovr/commit/85feecb226a86fc110ec661beb92f6dcca3422d3))

#### behavior fixes
* **clipboard:** fix scuffed disable paste button implementation ([9a28b4e](https://github.com/NSPC911/rovr/commit/9a28b4ef944c4444099a0d10fb8dbe069d734132))
* **pinned_sidebar:** fix highlighted not saving ([f6aa4fe](https://github.com/NSPC911/rovr/commit/f6aa4fe63c5b558fcf9c32e52f97b6ecbe7a5b73))
* **pinned_sidebar:** prevent option refresh ([32f72b1](https://github.com/NSPC911/rovr/commit/32f72b16b51b4c2f52423497f7fb6209cc38c30c))
* **process:** fix forced perm error ([a0ed7a4](https://github.com/NSPC911/rovr/commit/a0ed7a49bc643a598680a57472406a6678676e9a))
* **process+path_utils:** fix deletion inside symlinks/junctions ([3291017](https://github.com/NSPC911/rovr/commit/3291017e8d4e9ac398764e2a7d364c4d369c9af4))

### Added

#### new config options
* **app:** add scroll-off behaviour to filelist ([#139](https://github.com/NSPC911/rovr/issues/139)) ([c2a38fb](https://github.com/NSPC911/rovr/commit/c2a38fb27e11f080518152519ae01927eb75d544))

#### style improvements
* **app:** improve borders and stuff ([ee181e5](https://github.com/NSPC911/rovr/commit/ee181e5629eb4652873e92b373674392c983a693))
* **app:** improve compact mode ([#138](https://github.com/NSPC911/rovr/issues/138)) ([c45832e](https://github.com/NSPC911/rovr/commit/c45832e0ca3e1baf1019c223e550d5d7e24259a2))
* change ascii logo ([1a15b7f](https://github.com/NSPC911/rovr/commit/1a15b7fa1907b7fde6babd7d8793d390ee86ed48))
* **compact-mode:** make header 1 char height ([e66a408](https://github.com/NSPC911/rovr/commit/e66a408e552c7127232098ba583f5742084e3012))

#### error toasts
* **app:** improve css change handling ([756bb38](https://github.com/NSPC911/rovr/commit/756bb3812af10e7d1b6f280d874864e3cde65a1d))
* **app:** show any stylesheet errors as is ([a1aae91](https://github.com/NSPC911/rovr/commit/a1aae911a254d143a757f00e5fa08e58e929e475))

#### modal screens
* **fileinuse:** add skip + retry buttons and toggle ([#137](https://github.com/NSPC911/rovr/issues/137)) ([40c2abf](https://github.com/NSPC911/rovr/commit/40c2abfe4ad2b06d642aba2d7a663c6e82004e3e)), closes [#123](https://github.com/NSPC911/rovr/issues/123)


#### housekeeping
* **config:** remove recursive required adder ([9c708d8](https://github.com/NSPC911/rovr/commit/9c708d8e6b5b240ec51714c54ebdedd27f113e5a))
* **config:** use importlib.resources ([0561446](https://github.com/NSPC911/rovr/commit/0561446f46184bf7246bf5fa1e52953dc9906ff4))
* **constants:** switch to tuple ([799ff19](https://github.com/NSPC911/rovr/commit/799ff19f4c31045ae4984923d2d2ecabfedfc914))
* **maps:** add typed dict for VAR_TO_DIR ([cb56f94](https://github.com/NSPC911/rovr/commit/cb56f94fdf827f302851259a1b1058fc8ac9f51e))

#### user experience
* **path_input:** improve ux a bit ([ce7f339](https://github.com/NSPC911/rovr/commit/ce7f33971a7a8d649e10ff5bacf69f2dbb21ecb8))
* **preview:** add progress showcase ([c332da1](https://github.com/NSPC911/rovr/commit/c332da1fc1a8d71cabe68bf33886cea6f2204f07))
* **processes:** improve permission error handling ([4246b72](https://github.com/NSPC911/rovr/commit/4246b721447b5875c3a8a83bf3b0c7b38c0dff3c))
* **search:** add custom scorer because yes ([92108ae](https://github.com/NSPC911/rovr/commit/92108ae0c62fe988edde6c1bb5661e6f425fa5c2))

### Removed
* **config**: removed `interface.preview_*` in favour of `interface.preview_text.*` ([530c507](https://github.com/NSPC911/rovr/commit/530c50771fdee3e5e0456bce94088c4cd0b338d8))
* **config**: removed `settings.cd_on_quit` in favour of `--cwd-file` ([9b4c6b7](https://github.com/NSPC911/rovr/commit/9b4c6b7c580c1f2945a969448082f1a78ee22fb8))

### Performance Improvements

* **path-func:** add await because perf improved ([db61508](https://github.com/NSPC911/rovr/commit/db61508e214d40087fc18f642ed8ff7eb6e96010))
* **filelist:** improve archive preview performance ([52f2e68](https://github.com/NSPC911/rovr/commit/52f2e6863caa92501b00331dddd109faaf2174eb))
* **zoxide:** switch to proper worker ([137a35a](https://github.com/NSPC911/rovr/commit/137a35a4af62d5d366e3bfc8300285580ab8cc0a))
