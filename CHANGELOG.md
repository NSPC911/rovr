# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `screens`: add a shell execution screen #217
- `filelist`: add bypassing single folder dirs #208

## [0.7.0] - 2026-01-31

### Added
- `zip`: add additional options for creating an archive 5f26813

### Fixed
- `filelist`: fix autofocus not working when the first option needs to be highlighted 2ecb37e
- `filelist`: fix crash on entering a directory that cannot be accessed 732c0aa
- `zip`: fix zstd compression level handling 903a32e
- `metadata`: dont use cached stats df2f7a7
- `state`: actually save and use sort orders 2ca72cd

### Build
- add support for building with nuitka #206

## [0.7.0.dev3] - 2026-01-25

### Added
- `app`: add force tty option #197
- `app`: add batch rename support #198
- `screens`: add file list to screen for paste and delete files #202 17275d3
- [BREAKING] `actions`: add extra panel for copy related actions #200
- `config`: refuse to launch if template config is tampered 1dcdd98

### Fixed
- `app`: prevent weird image preview bug that makes it scroll up 9fddec4
- `filelist`: add safeguard from crash bab18b0
- `firstrun`: use the proper dependency dd3c89d
- `app`: fix cd on startup not working 3dda6b6
- `screens`: improve button color coding 9a87831
- `pinned_sidebar`: fix sidebar not appearing due to textual eee15990
- `preview`: load and close image files a04d252
- `screens`: use more horizontal breakpoints for better layout abd78a3

### Performance
- `config`: improve schema checking performance abb1606

### Removed
- [BREAKING] `plugins`: moved `plugins.editor` to `settings.editor` #198
- [BREAKING] `preview`: removed image resizer 99ca469

## [0.7.0.dev2] - 2026-01-12

### Added

- `cli`: add `--config-folder` option to specify custom config folder #185
- `filelist`: dim files/folders that are cut in clipboard #188
- `filelist/state`: option to remember sort order per folder #193
- `log`: improve logging mechanism f8c0988
- `config`: provide two separate profiles for keybinds #179

### Changed

- [BREAKING] `app`: remove `modes` (use `--config-folder`) #195
- [BREAKING] `config`: allow additional flags in config #191
- `preview`: batch pdf loading #184
- `app`: stop causing triple threads to occur f8e015f
- `clipboard`: slightly refactor code #188
- `mixins`: mixin filelist, clipboard and rgsearch 644e4e3

### Fixed

- `filelist`: properly show file list checkboxes 8a63ce9
- `app`: stop watching thread from exiting 5459741

## [0.7.0.dev1] - 2026-01-01

### Added

- `archive`: add support for zstd archives #172
- `app`: add log dump when errors occur a5f38ca e046f8d ac9f129
- `rg`: add support for rg as plugin #175
- `preview`: configurable max preview image size #178
- `cli`: add dev crash ac9f129

### Changed

- [BREAKING] `preview`: add support for mime types using puremagic #172
- [BREAKING] `config`: remove unused preview texts 1b8deb6
- [BREAKING] `preview`: use threads as far as possible #172 #183
- `deps`: bump textual to ~=6.9 09d1d23
- `preview`: load images, and resize them in a separate thread #178
- `preview`: check mtime before loading preview again 9d7c6cf

## [0.6.0] - 2025-12-16

### Added

- `app`: use textual's tree instead of a custom tree
- `app+config`: add support for modes
- `clipboard`: constantly check clipboard added files
- `config`: allow changing bindings for screen layers
- `config`: auto-detect editor to use, add support for more keys
- `editor`: add config to suspend when opening editor, open all files in editor
- `fd`: add additional toggleable options
- `icons`: show icon for symlink/junctions with separate icons
- `preview`: add pdf preview support with poppler, add support for using file(1)
- `cli`: output fix for certain commands 1251ca8

### Changed

- [BREAKING] `cd-on-quit`: remove match type key
- [BREAKING] `fd`: rename from 'finder' to 'fd'
- [BREAKING] `sort_order`: add custom keybind support
- `filelist`: use custom set_options method
- `icons`: use fnmatch instead of using scuffed methods
- `preview`: use pygments instead of tree-sitter, open image in thread
- `pip`: switch to tomli for toml parsing

### Fixed

- `archive`: improved archive type detection
- `cli`: don't load everything when using certain functions
- `filelist`: fix issue with empty directories preventing navigation
- `finder`: use pseudo exclusive worker to prevent error spam
- `input`: fix overscroll issue
- `rename_button`: properly stop execution after error fee8bd0
- `screens`: add click to exit modal screen

### Removed

- `process + screens`: remove permission asker modal

## [0.6.0rc1] - 2025-12-14

### Added

- `clipboard`: constantly check clipboard added files 81df523
- `config`: allow changing bindings for screen layers #161
- `fd`: add additional toggleable options #163
- `icons`: show icon for symlink/junctions e6a354a
- `icons`: show separate symlink/junction icon fbf2a08

### Changed

- [BREAKING] `fd`: rename from 'finder' to 'fd' #163
- [BREAKING] `sort_order`: add custom keybind support #168
- `pip`: switch to tomli for toml parsing #162
- `filelist`: use custom set_options method e6a354a
- `screenshots`: perhaps fix the broken fonts #166

### Fixed

- `filelist`: fix issue with empty directories preventing navigation 985a509
- `input`: fix overscroll issue a8b5307

## [0.6.0.dev2] - 2025-12-02

### Added

- `preview`: add support for using file(1) #157

### Changed

- [BREAKING] `cd-on-quit`: remove match type key 32a389f
- `icons`: use fnmatch instead of using scuffed methods 4c848a1
- `preview`: use pygments instead of tree-sitter e95350f
- `style`: fix errors related to ty alpha 28 ce59c07
- `cd-on-quit`: use more robust functions 32a389f

### Fixed

- `screens`: add click to exit modal screen d84e9a8
- `finder`: use pseudo exclusive worker to prevent error spam c9a7741
- `archive`: just gamble which archive type it is 7fe26f6
- `cli`: don't load everything when using certain functions 18558b9

### Removed

- `process + screens`: remove permission asker modal 8caa4f9

## [0.6.0.dev1] - 2025-11-24

### Added

- `app`: use textual's tree instead of a custom tree a1d7449
- `app+config`: add support for modes #154
- `config`: auto-detect editor to use 5f1d7f8
- `config`: add support for more keys 294d9bb
- `editor`: add config to suspend when opening editor ed605da
- `editor`: add config to open all files in the editor 8189699
- `preview`: add pdf preview support with poppler #153

### Changed

- `preview`: open image in thread db617a0

## [0.5.0] - 2025-11-15

### Added

- add sort order switcher (##145) f458a54
- `app`: add scrolloff behaviour to filelist (##139) c2a38fb
- `app`: add show key option + slight refactor 756bb38
- `app`: add tree view command 4fc1a80
- `app`: add a state manager (##146) 5ad938f

### Changed

- [BREAKING] improve preview container and config functions (##135) 530c507
- [BREAKING] `app`: expand compact mode into two options b2afee6
- [BREAKING] `app`: remove cd on quit in favour of `--cwd-file` (##126) 9b4c6b7
- [BREAKING] `schema`: decline some keycodes ac0b736
- `app`: show any stylesheet errors as is a1aae91
- `deps`: bump astro, starlight, and vite for documentation
- `ci`: update formatting, ty, and documentation workflows
- `docs`: document undocumented features and rephrase content (##147)
- `logo`: change ascii logo 1a15b7f
- `app`: improve borders, compact mode, and css change handling
- `config`: improve required adder and resource loading
- `fileinuse`: add skip + retry buttons and toggle (##137)
- `filelist`: improve archive preview performance and container refactor
- `preview`: add progress showcase c332da1
- `processes`: improve permission error handling 4246b72
- `zoxide`: switch to proper worker and asyncio
- `perf`: reduce string compression, switch to base64, and improve path_utils performance
- `logging`: switch to using self.log instead of print
- `finder`: switch to asyncio faecb1a
- `session`: use list[str] for session directories 92bdb07

### Fixed

- `filelist`: fix navigation in empty directories, selection issues, and reload pins
- `process`: fix deletion inside symlinks/junctions and improve error handling
- `app`: fix crashes (right click, etc.) and windows suspension warnings
- `clipboard`: handle paste button states properly
- `config`: fix startup icon and migration typos
- `copy_path`: improve directory entry usage
- `doc-gens`: fix traceback display and execution checks
- `keybinds`: fix list adding and default symbols
- `path_utils`: handle nt-specific issues and improve extension sorting
- `pinned-sidebar`: fix search bar visibility and state saving
- `screens`: improve modal exit behavior
- `sort_order`: fix icon setting and tooltips
- `style`: fix image and option padding/styling

[Unreleased]: https://github.com/NSPC911/rovr/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev3...v0.7.0
[0.7.0.dev3]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev2...v0.7.0.dev3
[0.7.0.dev2]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev1...v0.7.0.dev2
[0.7.0.dev1]: https://github.com/NSPC911/rovr/compare/v0.6.0...v0.7.0.dev1
[0.6.0]: https://github.com/NSPC911/rovr/compare/v0.6.0rc1...v0.6.0
[0.6.0rc1]: https://github.com/NSPC911/rovr/compare/v0.6.0.dev2...v0.6.0rc1
[0.6.0.dev2]: https://github.com/NSPC911/rovr/compare/v0.6.0.dev1...v0.6.0.dev2
[0.6.0.dev1]: https://github.com/NSPC911/rovr/compare/v0.5.0...v0.6.0.dev1
[0.5.0]: https://github.com/NSPC911/rovr/compare/v0.4.0...v0.5.0
