<details>
<summary><h1>[v0.6.0]</h1></summary>
<p>

## breaking changes

- cd-on-quit: remove match type key
- fd: rename from 'finder' to 'fd'
- sort_order: add custom keybind support

## new features

- app: use textual's tree instead of a custom tree
- app+config: add support for modes
- clipboard: constantly check clipboard added files
- config: allow changing bindings for screen layers
- config: auto-detect editor to use, add support for more keys
- editor: add config to suspend when opening editor, open all files in editor
- fd: add additional toggleable options
- icons: show icon for symlink/junctions with separate icons
- preview: add pdf preview support with poppler, add support for using file(1)
- cli: output fix for certain commands 1251ca8

## fixes

- archive: improved archive type detection
- cli: don't load everything when using certain functions
- filelist: fix issue with empty directories preventing navigation
- finder: use pseudo exclusive worker to prevent error spam
- input: fix overscroll issue
- rename_button: properly stop execution after error fee8bd0
- screens: add click to exit modal screen

## perf

- filelist: use custom set_options method
- icons: use fnmatch instead of using scuffed methods
- preview: use pygments instead of tree-sitter, open image in thread

## build

- pip: switch to tomli for toml parsing

## removed features

- process + screens: remove permission asker modal

</p>
</details>
<details>
<summary><h1>[v0.6.0rc1]</h1></summary>
<p>

## new features

- clipboard: constantly check clipboard added files 81df523
- config: allow changing bindings for screen layers #161
- fd!: rename from 'finder' to 'fd' #163
- fd: add additional toggleable options #163
- icons: show icon for symlink/junctions e6a354a
- sort_order!: add custom keybind support #168
- icons: show separate symlink/junction icon fbf2a08

## build

- pip: switch to tomli for toml parsing #162

## fixes

- filelist: fix issue with empty directories preventing navigation 985a509
- input: fix overscroll issue a8b5307

## perf

- filelist: use custom set_options method e6a354a

## docs

- screenshots: perhaps fix the broken fonts #166

</p>
</details>
<details>
<summary><h1>[v0.6.0.dev2]</h1></summary>
<p>

## breaking changes

- cd-on-quit: remove match type key 32a389f

## new features

- preview: add support for using file(1) #157

## fixes

- screens: add click to exit modal screen d84e9a8
- finder: use pseudo exclusive worker to prevent error spam c9a7741
- archive: just gamble which archive type it is 7fe26f6
- cli: don't load everything when using certain functions 18558b9

## perf

- icons: use fnmatch instead of using scuffed methods 4c848a1
- preview: use pygments instead of tree-sitter e95350f

## style

- fix errors related to ty alpha 28 ce59c07

## docs

- cd-on-quit: use more robust functions 32a389f

## removed features

- process + screens: remove permission asker modal 8caa4f9

</p>
</details>
<details>
<summary><h1>[v0.6.0.dev1]</h1></summary>
<p>

## new features

- feat(app): use textual's tree instead of a custom tree a1d7449
- feat(app+config): add support for modes #154
- feat(config): auto-detect editor to use 5f1d7f8
- feat(config): add support for more keys 294d9bb
- feat(editor): add config to suspend when opening editor ed605da
- feat(editor): add config to open all files in the editor 8189699
- feat(preview): add pdf preview support with poppler #153
- perf(preview): open image in thread db617a0

</p>
</details>
<details>
<summary><h1>[v0.5.0]</h1></summary>
<p>

## breaking changes

- feat!: improve preview container and config functions (##135) 530c507
- feat(app)!: expand compact mode into two options b2afee6
- feat(app)!: remove cd on quit in favour of `--cwd-file` (##126) 9b4c6b7
- feat(schema): decline some keycodes ac0b736

## new features

- feat: add sort order switcher (##145) f458a54
- feat(app): add scrolloff behaviour to filelist (##139) c2a38fb
- feat(app): add show key option + slight refactor 75a5780
- feat(app): add tree view command 4fc1a80
- feat(app): add a state manager (##146) 5ad938f

## enhancements

- feat(app): show any stylesheet errors as is a1aae91
- fix(file_list): disable new item button when permissionless fd1f061
- fix(filelist): check up tree as well 8b7ed21
- fix(process + path_utils): fix deletion inside symlinks/junctions 3291017

## other changes

- build(deps): bump astro from 5.15.2 to 5.15.6 in /docs (##148) e2661a9
- build(deps): bump starlight from 0.35.2 to 0.36.1 ffc71fd
- build(deps): bump vite from 6.3.6 to 6.4.1 in /docs (##133) f6a60f5

- ci(formatting): use locked version from now on 47dce0b
- ci(ty): fix literally every issue with ty b0e7763
- ci: add .coderabbit.yaml 809f059
- ci: bump to 0.5.0rc1 d124a46
- ci: update docs 854a81b

- docs: document undocumented features + more images (##147) 8fc3ed7
- docs: rephrase more 5ec52c3

- feat: change ascii logo 1a15b7f
- feat(app): improve borders and stuff ee181e5
- feat(app): improve compact mode (##138) c45832e
- feat(app): improve css change handling 756bb38
- feat(compactmode): make header 1 char height e66a408
- feat(config): remove recursive required adder 9c708d8
- feat(config): use importlib.resources 0561446
- feat(constants): switch to tuple 799ff19
- feat(fileinuse): add skip + retry buttons and toggle (##137) 40c2abf
- feat(filelist): improve archive preview performance 52f2e68
- feat(maps): add typed dict for VAR_TO_DIR cb56f94
- feat(maps): switch to a dot spinner 7eaaf67
- feat(path_input): improve ux a bit ce7f339
- feat(preview): add progress showcase c332da1
- feat(processes): improve permission error handling 4246b72
- feat(readme): improve badges a96440c
- feat(zoxide): switch to proper worker 137a35a

- fix(app): fix right click crash that i got fbfa96c
- fix(app): warn for attempts to suspend on windows 35ec22c
- fix(app+state): do pad fixing 0926808
- fix(clipboard): auto handle paste button disables 3f1124f
- fix(clipboard): fix scuffed disable paste button implementation 9a28b4e
- fix(config): fix startup icon f6da8f0
- fix(copy_path): make use of dir entry 09de59c
- fix(copy_path): remove await 800cd46
- fix(core+app): fix crashes that i experienced e8161ef
- fix(doc-gens): call shutil.which once 310ef05
- fix(doc-gens): check exit code e12ffcb
- fix(doc-gens): show proper tracebacks b3872e9
- fix(doc-gens): use precise delta 574e4f9
- fix(filelist): await reload pins b0b1290
- fix(filelist): fix hist prev not working in empty dirs 2dca5e6
- fix(filelist): fix selection on exit select mode b2c7a16
- fix(filelist): temporary fix for subtitle, ty shall cry 14df8f3
- fix(keybinds): check list before adding it 6c2effb
- fix(keybinds): set default to focus processes to ## symbol b713a5c
- fix(migration): fix typos 7ee9f95
- fix(new_item_button): use update_file_list eb7258a
- fix(new_item_button): improve toast message 58fb410
- fix(path): check if dev then print 3328764
- fix(path): fix name error possibility 7c41fcb
- fix(path_utils): catch nt not found 7e102d0
- fix(path_utils): fix opening of non-existant files 695b63b
- fix(path_utils): prevent drives from being added if it cannot be entered ito a834331
- fix(path_utils): properly handle nt stuff 6f8451c
- fix(path_utils): use improved algo for extension sorting 6db0835
- fix(pinned-sidebar): always show search bar d8047ed
- fix(pinned-sidebar): fix highlighted not saving f6aa4fe
- fix(pinned-sidebar): prevent option refresh 32f72b1
- fix(pins): fix ty 2f728e1
- fix(pins): make pins global again 3e0a3c5
- fix(preview): stop log 0d44fe3
- fix(process): uses proper panic 642169d
- fix(processes): fix forced perm error a0ed7a4
- fix(rename-button): auto focus the item after renaming 5fb7d13
- fix(rename-button): fix renaming to different case 5c069a7
- fix(screens): go straight for the kill b08478e
- fix(sort_order): move icon setter to function 44da946
- fix(sort_order): use proper tooltip string 934efe2
- fix(state_manager): fix nitpicks and stuff 08d0ecd
- fix(state_manager): use icon helper function 9c27bc7
- fix(style): fix Images to be one char from sides 6a1489a
- fix(style): fix option styling 51cab0d 7dd4263
- fix(tabs): prevent selecting text of tabs 4f7a9e2
- fix(ui): fix padding and input not caring about width 4c34778
- fix(utils-func): handle noactiveworker and workercancelled 3147fc8
- fix(zoxide): some minor fixes 85feecb

- perf + refactor: reduce usage of string compression (##143) ca3e898
- perf(path_utils): move path_utils.get_cwd_object to a thread pool and await it (##141) f6813b1
- perf(path_utils): add await because perf improved db61508
- perf: switch from lzstring to scuffed base64 1baa849
- perf: switch to using self.log instead of print 30452be
- perf(finder): use asyncio faecb1a
- perf(zoxide): switch to asyncio (this commit has more than that) 92da08c

- refactor(app+pinned_sidebar): move watchers to app f15061c
- refactor(filelist): move over to file_list_container 7eb3c4b 0d9ac1f
- refactor(icons_utils): remove is_match var 9838637
- refactor(process): improve error handling 2b4eb13
- refactor: address code review feedback from copilot and coderabit aff9acb
- refactor: use list[str] for session directories 92bdb07
- refactor: use set_options instead of clear + add 00eab09 68caa7f

- style(filelist): use inline ifelse e77d01a
- style(path_utils): add overload for hinting 7823dd7
- style: fix ty errors c63be19

</p>
</details>
