# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1.post2]

### Fixed

- `opener`: check returncode, not stderr [feb6afb](https://github.com/NSPC911/rovr/commit/feb6afbe22cb50ea1b5edb5804cf80f3275868bb)
- `firstlaunch`: remove `open_all_in_editor` [b7b97ab](https://github.com/NSPC911/rovr/commit/b7b97abea837b6f30ab62973e09b654e0f1a2714)

## [0.9.1.post1]

### Fixed

- `metadata`: show pipe/fifo/other weird unix files [bd2ab73](https://github.com/NSPC911/rovr/commit/bd2ab73878d33d5463d58a02f4c42e5522b4e710)
- `style`: remove `background: red` [2ca8bf1](https://github.com/NSPC911/rovr/commit/2ca8bf122f7c0382a56bfc7304b503df1fc7fc01)
- `clipboard`: safely remove options [4100119](https://github.com/NSPC911/rovr/commit/41001197b249a0a739e92f9a122665657c09fead)

### Removed

- revert libuv support [b0d84cf](https://github.com/NSPC911/rovr/commit/b0d84cf2e57e452a74bd2718702902e4208251d3) [f1a42b6](https://github.com/NSPC911/rovr/commit/f1a42b69e5ec8e98fb3f4ad3aeef4a54aa5cd3b6)

### Performance

- `app`: fix insane movement lag [1c29683](https://github.com/NSPC911/rovr/commit/1c296837f58f23992f43e75b72db54f193d76696)

## [0.9.1]

### Added

- `app`: add libuv as optional asyncio loop (used in nuitka) [#294](https://github.com/NSPC911/rovr/pull/294)
- `metadata`: show mimetypes as a metadata section [#293](https://github.com/NSPC911/rovr/pull/293)

### Fixed

- `config`: actually cache schema validator [155e458](https://github.com/NSPC911/rovr/commit/155e458e3d1e0232efe693d817ae9e5144d2fa60)
- `shell`: use separate bg implementation instead of orphans [#295](https://github.com/NSPC911/rovr/pull/295) [1ec3556](https://github.com/NSPC911/rovr/commit/1ec3556a6d0bdac57d429ee6689f1b77cfdc3154) [9f57978](https://github.com/NSPC911/rovr/commit/9f57978d82d74da4d378b880c2ca810302ee9acd)

## [0.9.0]

### Added

- `context`: add right click menu options [#279](https://github.com/NSPC911/rovr/pull/279)
- `editor`: add support for opening editor as orphan [704400e](https://github.com/NSPC911/rovr/commit/704400e623fe2d47da432a3f6b873dd75841b8f7)
- `shell_exec`: add command substitution support [464e71c](https://github.com/NSPC911/rovr/commit/464e71c977d48c5e599a17cc1f5b3ee1131683d2)
- `openers`: add support for opening with a specific app [#281](https://github.com/NSPC911/rovr/pull/281)
- `new_item`!: add batch creation support [#283](https://github.com/NSPC911/rovr/pull/283)
- `context`: add windows properties shortcut thing [7b15bc6](https://github.com/NSPC911/rovr/commit/7b15bc62189505e24d0ac7f5de2fb8c7c73e889b)
- `filelist`: add configurable styles for specific files/folders [#284](https://github.com/NSPC911/rovr/pull/284)
- `app`: add theme name as class to #root [ba12d0f](https://github.com/NSPC911/rovr/commit/ba12d0f908b74ff97dd6554d831ed3f6f536fd0d)
- disable clock by default [24406d650f1d119a1a156ac71e022bc63c404cb6](https://github.com/NSPC911/rovr/commit/24406d650f1d119a1a156ac71e022bc63c404cb6)
- `app`: allow drag and and drop from gui to terminal using bracketed paste [#285](https://github.com/NSPC911/rovr/pull/285)

### Fixed

- `drives`: dont list all of them instead [8cf0822](https://github.com/NSPC911/rovr/commit/8cf0822c5f40dbe57da57af788c62cce5bc9804a)
- `config`: add java archive support ig [fb17dad](https://github.com/NSPC911/rovr/commit/fb17dada9b77e76893490e9c0bca18b721a9e04a)
- `process`: show overwrite unless dest=initial [5d580c3](https://github.com/NSPC911/rovr/commit/5d580c37f60236102a17a40f657fd815948def91)
- `pins`: fix warn from testing (not sure what happened but ok) [7cfa925](https://github.com/NSPC911/rovr/commit/7cfa925da8e0e345391d2cb6609a52b66b889d12)
- `config`: properly render config errors [477fc95](https://github.com/NSPC911/rovr/commit/477fc954cfcd81ce00cdec33531b2c363d5cda28)
- `path`: use powershell if another file is locking the file on windows [1a2d764](https://github.com/NSPC911/rovr/commit/1a2d764e0f019d79796b7582c8efa44054eec5d9)
- `app`: dont crash if cwd goes missing [2e04330](https://github.com/NSPC911/rovr/commit/2e04330d534b2e9f16e8f6481923f5fe7510bbe5)
- `config`: deepmerge with custom higher in order [0aeebe9](https://github.com/NSPC911/rovr/commit/0aeebe99feaa0515139d6890fa6e6c1db5deca0b)
- `preview`: dont hang if attempting to read a socket/fifo [2027875](https://github.com/NSPC911/rovr/commit/202787581c37693b44d36fd9a3802b52e356725e)
- `preview`: warn if inode/preview is not directory [9400cf2](https://github.com/NSPC911/rovr/commit/9400cf216f805ebe0493701e00c990f4ee2b1b10)
- `input`: follow screen sizes [df9923d](https://github.com/NSPC911/rovr/commit/df9923d4c36ca58edff1362d56b8d79c82a2137c)
- `showkeys`: fix offset and other stuff [757b4c3](https://github.com/NSPC911/rovr/commit/757b4c3bd492c2da5f8a37368ad22bea14f11a67)
- `zoxide`: dont crash with \_asyncio.Future if nuitka compiled [6ad395b](https://github.com/NSPC911/rovr/commit/6ad395b4e54d86a56cd956d4e492d8536d7660b7)
- `editors`: use shlex.split rather than shlex.quote-ing the file [7a6dae6](https://github.com/NSPC911/rovr/commit/7a6dae6542a5689d6057e8883da8a64b7cf8ca10)
- `utils`: properly check for file being used on windows [5622571](https://github.com/NSPC911/rovr/commit/56225710d00486fdd7621a3d685c222e8e0ceb0d)
- `preview`: fix crash on broken wsl symlink [ae50128](https://github.com/NSPC911/rovr/commit/ae50128160e9d82a3d47b9b0c02563e9410e48ab)
- `lists`: make checkbox use the same color as the text [b45eeea](https://github.com/NSPC911/rovr/commit/b45eeeabd59bccc442e029634480b42811add54e)
- `screens`: improve resized ui [a17e2cb](https://github.com/NSPC911/rovr/commit/a17e2cb3d92ececc05b931ab30a8ee3e28ea6f92) [2f34dc0](https://github.com/NSPC911/rovr/commit/2f34dc0d3efcd51d012b8628a3d7e88fb355d1ba)
- `log`: only keep latest 50 logs [b351152](https://github.com/NSPC911/rovr/commit/b3511529736c3963b3ee25b624938591ab409aee)

### Refactor

- `archive`: switch to external dependency [bc4c6e9](https://github.com/NSPC911/rovr/commit/bc4c6e9226762ea026835563149929ad9fde73ce)
- `preview`!: rename `mime_rules` to `preview_rules` [36d1316](https://github.com/NSPC911/rovr/commit/36d131633a734ee118bca7e4cba2411b55e74bae)
- `editor`!: use `app` to define what to do when editor is used [8e9b7a6](https://github.com/NSPC911/rovr/commit/8e9b7a6455876751a0df19d1dc14be2566baa60a)
- `app`: use a custom binding handler [#282](https://github.com/NSPC911/rovr/pull/282) [3aeed2f](https://github.com/NSPC911/rovr/commit/3aeed2f5ce8b51e0a5579f6eae064b09d6482515)
- `app`: use reactive.var instead of reactive.reactive [63ffa89](https://github.com/NSPC911/rovr/commit/63ffa89861fe689a74430a371895e9d4970bcb28)

### Removed

- `editor`: remove blocked opening support (only orphan and suspend allowed) [e03a42d](https://github.com/NSPC911/rovr/commit/e03a42ddeeb5f4f05842234925b367668ca9f043) [3118230](https://github.com/NSPC911/rovr/commit/3118230559c88551a890b1d6f98f6a9bfb5b3f32) [f904e18](https://github.com/NSPC911/rovr/commit/f904e1860c9fa2592d229cd3f90ba1a642c0e6ec) [1983afa](https://github.com/NSPC911/rovr/commit/1983afa3a62e8bf0bb84154939404ebada85dadf)

## [0.8.2] - 2026-05-04

### Added

- `filelist`: visually distinguish broken symlinks [7f5232e](https://github.com/NSPC911/rovr/commit/7f5232ef06dcde70e8056a31f8ef6453535c396a)
- `image`: use resampler based on config [d13c104](https://github.com/NSPC911/rovr/commit/d13c10457b66aabbaac0351f11c99317b670e851)
- `pinned_sidebar`: keep focus if click on [#264](https://github.com/NSPC911/rovr/pull/264)
- `rg+fd`: allow custom timeout [d497bfd](https://github.com/NSPC911/rovr/commit/d497bfd2ceb3a8cc0b249b4112395ebff5a3a05c)

### Fixed

- `app`: force forkserver > spawn for Process [e69d124](https://github.com/NSPC911/rovr/commit/e69d124092c67d484ef9e2fcee37e3bcc363dfb7)
- `app`: prevent second drive check [76de6c5](https://github.com/NSPC911/rovr/commit/76de6c5db0f954fbb53a8e27a25716c8493dabd6)
- `filelist`: prevent crash on broken symlink [#271](https://github.com/NSPC911/rovr/pull/271)
- `metadata`: no crash on focus [e0994ee](https://github.com/NSPC911/rovr/commit/e0994ee88cefd9c9fe0de2364c1c83890b1686f1)
- `options`: dont cause recursion error when `--dev` [c14239b](https://github.com/NSPC911/rovr/commit/c14239bdad0560d0407299ea4f4c8197b2a2fc9f)
- `path_input`: 'escape' out [ab82a7f](https://github.com/NSPC911/rovr/commit/ab82a7fd1098c94f38e1e34973e1d54de4af8442)
- `preview`: use transparent background color when not bat [3778b4a](https://github.com/NSPC911/rovr/commit/3778b4a8bcb5676a1b13a9c45db5603bcdbc4a2e)
- `process`: correctly handle same file error [fdd7b96](https://github.com/NSPC911/rovr/commit/fdd7b96a061818eae7951be6dd93fd469e851357)
- `multiprocess`: forcefully disable multiprocessing if user's machine is bad [b0dcba9](https://gitihub.com/NSPC911/rovr/commit/b0dcba964250beaf94458ad32c2381e6f69251a6)
- `rich`: monkeypatch ansi decoder [01e0c95](https://github.com/NSPC911/rovr/commit/01e0c954a49556fa4902e08d2d898c2f1892baeb) [639f0ea](https://github.com/NSPC911/rovr/commit/639f0eab75151cdc959cc0c95afde159b11c60f9)
- `screens`: dismiss cancel event [723eee9](https://github.com/NSPC911/rovr/commit/723eee96c2583c32bd84b2aa3ec98e101958bb12)
- `sortorder`: use box char for separator [80439d6](https://github.com/NSPC911/rovr/commit/80439d6e8fed71e17b2ddf283a14cd27314d81f4)
- dont check for global vars [fe644b7](https://github.com/NSPC911/rovr/commit/fe644b70f776dc622238d65d36c8d6be45b6b8d4)

### Performance

- `config`: cache schema [bbd38af](https://github.com/NSPC911/rovr/commit/bbd38af8a25f8ca0b23f1580cd7ef72cd3b6cdec) [4f810c6](https://github.com/NSPC911/rovr/commit/4f810c67ac21d17630fb4ad5c63cbd4c6bacf1fc)
- `filelist`: improve loading by lazy loading renderer and stuff [#263](https://github.com/NSPC911/rovr/pull/263) [5653956](https://github.com/NSPC911/rovr/commit/565395644835d51c165b418ce314bb3e5d795244)
- `filelist`: in select mode, select only if name matches [dc7a46d](https://github.com/NSPC911/rovr/commit/dc7a46d3fee8457062091d5f4336ed5842399c14) [7ded7d4](https://github.com/NSPC911/rovr/commit/7ded7d49b75b3b0f26fabda56220ca9761f4bc33)
- `options`: use module level cache for options [c29c1c3](https://github.com/NSPC911/rovr/commit/c29c1c38de7b3016788a92612bdbd881cef044fe)
- `preview`: move svg loader to Process [35ca21e](https://github.com/NSPC911/rovr/commit/35ca21ea5cd8858257955ad5c02826e8c1ef9ab3)
- `rg+fd`: incrementally add options for better responsiveness [#268](https://github.com/NSPC911/rovr/pull/268)
- even lazier imports [74cb7f6](https://github.com/NSPC911/rovr/commit/74cb7f6f8d057f8fde8eb0cbcc0659f457bdc0da)

## [0.8.1] - 2026-04-10

### Added

- `filelist`: add create item and paste item to right click [7198cfa](https://github.com/NSPC911/rovr/commit/7198cfa22f3bf4d8667e5bf2df6558434800079a) [ad11200](https://github.com/NSPC911/rovr/commit/ad11200533a4bbe9b78101d839202c32f5425b63)
- `path_input`: improve path input to force absolute path and use better completions [#256](https://github.com/NSPC911/rovr/pull/256)

### Fixed

- `filelist`: fix right click bugs and stuff [53acbcd](https://github.com/NSPC911/rovr/commit/53acbcded00d7bc4330f6d761a26e1fe4c65b990) [0629cd7](https://github.com/NSPC911/rovr/commit/0629cd7d068c2301f723644eb5413131bb9b19d8) [7198cfa](https://github.com/NSPC911/rovr/commit/7198cfa22f3bf4d8667e5bf2df6558434800079a) [ad11200](https://github.com/NSPC911/rovr/commit/ad11200533a4bbe9b78101d839202c32f5425b63)
- `config`: use `D` not `shift+d` [f171500](https://github.com/NSPC911/rovr/commit/f1715000898977b67fdf6ba876941dd812f4e0b3)
- `preview`: use hashables [cd95fca](https://github.com/NSPC911/rovr/commit/cd95fcae640bd3c27619dd89fbfcfc4e11385523)
- `app`: safeguard filelist property hopefully [be3fdd9](https://github.com/NSPC911/rovr/commit/be3fdd900a9d9b4a5fa88f5db9d82859da0a140a) 0baa63b
- `app`: comfy buttons should work now [ee62cc0](https://github.com/NSPC911/rovr/commit/ee62cc00baa63b2e12acf0548963bed206ef98d5)
- `path_input`: dont select all text on focus [#256](https://github.com/NSPC911/rovr/pull/256)

### Performance

- `app`: move drive stuff to separate process [44a669d](https://github.com/NSPC911/rovr/commit/44a669de8e513775479a724888f8c268761b2792)

## [0.8.0] - 2026-03-31

### Added

- `app`: watch for changes in mtime of highlighted file and update if changes [#242](https://github.com/NSPC911/rovr/pull/242)
- `fd`: show hidden files optionally [e0e6fc1](https://github.com/NSPC911/rovr/commit/e0e6fc15e46700cfa42de116df4524219f8aa5c3)

### Fixed

- `preview`: fix preview not updating loading indicator's border subtitle [038a473](https://github.com/NSPC911/rovr/commit/038a473089b0e4199d44459dd03ee334c669c59d)
- `fd`: fix toggle changes not applying visually [4acc181](https://github.com/NSPC911/rovr/commit/4acc1811272782cdcabc75f7d8caca1721ee2146)
- `cli`: fix rare circumstance where path of config folder cannot be resolved [e2ab50a](https://github.com/NSPC911/rovr/commit/e2ab50a333da1752f34cf92c3ed7f083ae43ebf9)

### Performance

- `preview`: use mtime as cache for preview [659f7b7](https://github.com/NSPC911/rovr/commit/659f7b72bccf76e46130ac34c80b6b3bf2d099aa)

## [0.8.0rc1] - 2026-03-28

### Performance

- `app`: improve startup times in general [#240](https://github.com/NSPC911/rovr/pull/240)
- `cli`: use custom argparse instead of rich-click [#241](https://github.com/NSPC911/rovr/pull/241)

### Fixed

- `pins`: dont reload the pins continuously [10e3467](https://github.com/NSPC911/rovr/commit/10e346710069ba1408c2cc556828d0747f20ea5c)

## [0.8.0.dev3] - 2026-03-20

### Notable

- fix: ensure search is cleared when going to a new directory [880f6d6](https://github.com/NSPC911/rovr/commit/880f6d670e1f3bb73b166b9271f611fb4ca56bda)
- refactor: switch to an actions oriented method api [#238](https://github.com/NSPC911/rovr/pull/238)

### Added

- `filelist`: add class if select mode is enabled [41ab467](https://github.com/NSPC911/rovr/commit/41ab4674d8787454c04c4b73fdefb442cec92193)

### Fixed

- `zoxide`: try fix for nuitka ig [362a9ad](https://github.com/NSPC911/rovr/commit/362a9add6ff190232c8871bc0f8151719db310da)
- `nuitka`: build on proper os for macos x64 [4a90521](https://github.com/NSPC911/rovr/commit/4a9052174a12568513dd8ceadcd3e39555ce4bd8)
- `config`: fix mimerules for archive files [9b4865d](https://github.com/NSPC911/rovr/commit/9b4865d8fd9063d65cebd0ef25ad76600867620d)
- `preview`: actually show loading state [879f2c3](https://github.com/NSPC911/rovr/commit/879f2c31ed64be950affe4dd8ae481f97a7f8213)
- `filelist`: try preventing crash [773abc1](https://github.com/NSPC911/rovr/commit/773abc10eeedc10035c0df4e2bcc0fbf2f72c931)

### Refactor

- `screens`!: rename `CommonFileNameDoWhat` to `FileNameConflict` [8eea71f](https://github.com/NSPC911/rovr/commit/8eea71fad7fde3a33d05b26a14c1cd96230b82a5)

### Performance

- `all`?: use non-async + push to after first pain(t) [9e2a5d6](https://github.com/NSPC911/rovr/commit/9e2a5d6098619ca5c12b515ba4f6d0d04f7d4802)
- `clipboard`?: use direct clipboard reference in app [13ebaa4](https://github.com/NSPC911/rovr/commit/13ebaa47e5a3d992535bae90b7e1f972806e0fbc)

## [0.8.0.dev2] - 2026-03-11

### Notable

- feat(`preview`): add font previewing support [0d4aec5](https://github.com/NSPC911/rovr/commit/0d4aec5268c708e772de6268581cf86cdd6faa1a) [49fbb93](https://github.com/NSPC911/rovr/commit/49fbb93a42d2ff2e00aaabba2d6658d83fdb83c4)
- feat(`mimetype`): update puremagic + use regex for matching [92a709b](https://github.com/NSPC911/rovr/commit/92a709b1e1980893fb45af178a28405d5b50c27a)
- feat(`mime`): check different encodings for mimetype detection [c6d61d4](https://github.com/NSPC911/rovr/commit/c6d61d483e89f9916faa5e126e3b6debc30628cc)
- fix(`cli`): silence textual-image warnings [c9d3865](https://github.com/NSPC911/rovr/commit/c9d386514cc118aa3badead03225c046da713a74)
- fix(`config`): actually point to the error line in the config file [0733791](https://github.com/NSPC911/rovr/commit/07337919c0a38a21d4199d6482cb9567727a4959)
- fix(`file(1)`): use the actual executable and not depend on path [6700c0a](https://github.com/NSPC911/rovr/commit/6700c0a0524b72a218cba6478a15101f0bcb6aeb)
- fix(`macos-clipboard`): replace clippy with ctypes (absolute chaos) [8f4c83c](https://github.com/NSPC911/rovr/commit/8f4c83c2f1c5173ed23cbff4d06aa9c924934a49)
- fix(`preview`): bypass selected folders in the preview should work now [34317f2](https://github.com/NSPC911/rovr/commit/34317f2d8cd007a8e7e1c12b2a331fa0cad0f77a)
- fix(`preview`): fix issues where normal file preview simply fails [9337468](https://github.com/NSPC911/rovr/commit/9337468e5a5629bebcdcc413ae49d7abfdbdb86d) e5a5629
- fix(`utils`): make editor query shutil.which before running [dfa4691](https://github.com/NSPC911/rovr/commit/dfa469113eab1aa222dde8f8bd8fc37a2068fbc7)
- perf(`preview`): debounce the loading state [a119744](https://github.com/NSPC911/rovr/commit/a119744596649ddd429be82b738ad675408c52dc) [2d4cb70](https://github.com/NSPC911/rovr/commit/2d4cb708316e4cede4aefaf21d4ad88308c5583a)
- perf(`preview`): move image loading into separate Process [#226](https://github.com/NSPC911/rovr/pull/226)

### Added

- `cli`: add logs folder to config-path [550639c](https://github.com/NSPC911/rovr/commit/550639ce5826d631861d12061d200bef3c2a162c)
- `config`: add config migration templates [b5a7f61](https://github.com/NSPC911/rovr/commit/b5a7f61032f7f4dcf1def1c531fca5ab452b89df)
- `mime`: check different encodings for mimetype detection [c6d61d4](https://github.com/NSPC911/rovr/commit/c6d61d483e89f9916faa5e126e3b6debc30628cc)
- `mimetype`: update puremagic + use regex for matching [92a709b](https://github.com/NSPC911/rovr/commit/92a709b1e1980893fb45af178a28405d5b50c27a)
- `preview`: add font previewing support [0d4aec5](https://github.com/NSPC911/rovr/commit/0d4aec5268c708e772de6268581cf86cdd6faa1a)
- `preview`: add max image preview size [#226](https://github.com/NSPC911/rovr/pull/226)

### Fixed

- (dev) `cli`: use asyncio to crash when using `--force-crash-in` [53ec6da](https://github.com/NSPC911/rovr/commit/53ec6da0fb36694a1194270a6c1b6d2bdf36c293)
- `app`: call callback directly in FileList [c337728](https://github.com/NSPC911/rovr/commit/c3377283d6e583d3a0c92ba93631daaf4fba07d5)
- `app`: download screenshot to proper location [52e6a45](https://github.com/NSPC911/rovr/commit/52e6a45998507da49f815c49bfac914fd7dbdd5a)
- `app`: use threading event to stop background thread [907fd86](https://github.com/NSPC911/rovr/commit/907fd862ee959ed1c1ea03279db5326c526d1363)
- `cli`: silence textual-image warnings [c9d3865](https://github.com/NSPC911/rovr/commit/c9d386514cc118aa3badead03225c046da713a74)
- `config`: actually point to the error line in the config file [0733791](https://github.com/NSPC911/rovr/commit/07337919c0a38a21d4199d6482cb9567727a4959)
- `config`: don't create config directory until necessary [69afa5e](https://github.com/NSPC911/rovr/commit/69afa5e70209a60752a8e45c0d7120baa8fbdeab)
- `file(1)`: use the actual executable and not depend on path [6700c0a](https://github.com/NSPC911/rovr/commit/6700c0a0524b72a218cba6478a15101f0bcb6aeb)
- `filelist`: add to session before creating options [447845f](https://github.com/NSPC911/rovr/commit/447845f96d0d41f5a80c9869c0e74a532f7a5a5e)
- `filelist`: previously saved stuff should be saved again [2a14985](https://github.com/NSPC911/rovr/commit/2a149857723891cb39dc5ae54363433e4f589e19)
- `firstlaunch`: use proper path for config dumper [53baee7](https://github.com/NSPC911/rovr/commit/53baee7a96301eda57fae0205a4e309e0101fd21)
- `footer`: make children use one wide scrollbar [697a686](https://github.com/NSPC911/rovr/commit/697a686864de5703a23c1effac98469895fa4a58)
- `folder_prefs_utils`: ensure config directory exists [e9a982a](https://github.com/NSPC911/rovr/commit/e9a982ae8e6ea76275c923e4c7c7e1f474c73d9b)
- `macos-clipboard`: replace clippy with ctypes (absolute chaos) [8f4c83c](https://github.com/NSPC911/rovr/commit/8f4c83c2f1c5173ed23cbff4d06aa9c924934a49)
- `metadata`: handle negative unix timestamp because of nt epoch [4e8ba9d](https://github.com/NSPC911/rovr/commit/4e8ba9db54ffb99eb13c1da49b622ae66aa7352b)
- `pdf`: use future annotations to prevent crash [faf9f06](https://github.com/NSPC911/rovr/commit/faf9f064d6cf39752cc9b565fbe3f43c89480f01)
- `pinned_sidebar`: fix typo + create config dir if not found [37a944c](https://github.com/NSPC911/rovr/commit/37a944c542bad77af8a8b1df75aa5a5b81855e28)
- `preview`: dont save lookup error thing [1a6d984](https://github.com/NSPC911/rovr/commit/1a6d9843a7ca7431b94a8f5109b441884a512971)
- `preview`: fix issues where normal file preview simply fails [9337468](https://github.com/NSPC911/rovr/commit/9337468e5a5629bebcdcc413ae49d7abfdbdb86d) e5a5629 [49f3456](https://github.com/NSPC911/rovr/commit/49f3456b8b383ba3011ff86758518660a0bdb046)
- `preview`: force set enter_into to bypass selected folders in the preview [34317f2](https://github.com/NSPC911/rovr/commit/34317f2d8cd007a8e7e1c12b2a331fa0cad0f77a)
- `preview`: wrap errors [d5c51c1](https://github.com/NSPC911/rovr/commit/d5c51c11fd75e3b1363caa2a2797e9ddf2ce3d54)
- `utils`: make editor query shutil.which before running [dfa4691](https://github.com/NSPC911/rovr/commit/dfa469113eab1aa222dde8f8bd8fc37a2068fbc7)
- `windows-clipboard`: use proper property for return code [59fdc5d](https://github.com/NSPC911/rovr/commit/59fdc5dde8f49675faefb5028a17171adeef8272)

### Performance

- `app+pins`?: improve startup [92ebc91](https://github.com/NSPC911/rovr/commit/92ebc91489a6b4205f4a2da2edb73ce6764feaa6)
- `filelist`?: use dict and convert to set for faster lookups? [d120056](https://github.com/NSPC911/rovr/commit/d120056f21b200e030e54b2e0df1944d08e3686b)
- `preview`: debounce the loading state [a119744](https://github.com/NSPC911/rovr/commit/a119744596649ddd429be82b738ad675408c52dc) [2d4cb70](https://github.com/NSPC911/rovr/commit/2d4cb708316e4cede4aefaf21d4ad88308c5583a)
- `preview`: move image loading into separate Process [#226](https://github.com/NSPC911/rovr/pull/226)
- `preview`: try to not use threads (locks suck) [f5bbf65](https://github.com/NSPC911/rovr/commit/f5bbf653599f79fbc8caed3a764d54bf4e4ad369)

### Refactor

- `preview`: directly use `has_child` instead of re-checking children again [7ecaf73](https://github.com/NSPC911/rovr/commit/7ecaf73a5a9cdb55ee4617a1a9e22a6726a1ed34)

## [0.8.0.dev1] - 2026-02-16

### Added

- `filelist`: add bypassing single folder dirs [#208](https://github.com/NSPC911/rovr/pull/208)
- `preview`: add resvg for svg rendering [#213](https://github.com/NSPC911/rovr/pull/213)
- `cli`: add `--ignore-first-launch` [9640c0d](https://github.com/NSPC911/rovr/commit/9640c0d4c0f82970a0839c49ddb0604f537a69fc)
- `screens`: add a shell execution screen [#217](https://github.com/NSPC911/rovr/pull/217)
- `cli`: inclue commit hash for `--version` [88d094d](https://github.com/NSPC911/rovr/commit/88d094d89c8903d175b12f794d0b22e3ae0b14fd)
- (dev): add `TypedDict` for config variable references [d00c1c3](https://github.com/NSPC911/rovr/commit/d00c1c308cad77ef9fefc7746a81e2de91e8035b) [20c75fe](https://github.com/NSPC911/rovr/commit/20c75fec983a60875e640cf7d86e8f90050b5263)

### Fixed

- `firstlaunch`: allow single press quit when forced [ae292a4](https://github.com/NSPC911/rovr/commit/ae292a4ea633258e6d4f578148e1b4b66fbf42ec)
- `tabs+filelist`: keep selections when switching tabs [9ace592](https://github.com/NSPC911/rovr/commit/9ace59212a51fe8b4eb61ee014f8d899f221cd4e)
- `app`: load the first paint faster [c4f3a2c](https://github.com/NSPC911/rovr/commit/c4f3a2c2df6e0e7ea0cb71dfa98cab33f9bfb556) [37b8fef](https://github.com/NSPC911/rovr/commit/37b8fef618434cfb02f546881df634efd45083d2)

### Performance

- `path_utils`: directly use `os.scandir` for iteration [e19bd08](https://github.com/NSPC911/rovr/commit/e19bd08281c0fb88de3e0a208e5049e35ede6fb9)
- `pinned_sidebar`: await 0 seconds [a3692c5](https://github.com/NSPC911/rovr/commit/a3692c5096a99187614d2fb10bdcb04a9eb8936e)
- `preview`: use a custom pdf preview implementation [#221](https://github.com/NSPC911/rovr/pull/221)

### Removed

- `deps`: remove ujson [e0b3253](https://github.com/NSPC911/rovr/commit/e0b3253d5e45ba703652785d5182b12ce9dd11d2)

## [0.7.0] - 2026-02-02

### Added

- `zip`: add additional options for creating an archive [5f26813](https://github.com/NSPC911/rovr/commit/5f2681383d6ad7fa368e2596b85f45667b951612)

### Fixed

- `filelist`: fix autofocus not working when the first option needs to be highlighted [2ecb37e](https://github.com/NSPC911/rovr/commit/2ecb37e0102af5473065a91b74ce69a807176628)
- `filelist`: fix crash on entering a directory that cannot be accessed [732c0aa](https://github.com/NSPC911/rovr/commit/732c0aa77ce32f3dec463d645380465a87481d80)
- `zip`: fix zstd compression level handling [903a32e](https://github.com/NSPC911/rovr/commit/903a32e7c1db6dc28b0e77775cfb127989a022cc)
- `metadata`: dont use cached stats [df2f7a7](https://github.com/NSPC911/rovr/commit/df2f7a7d7a917eac64839a32e88c6e780b4cbb0e)
- `state`: actually save and use sort orders [2ca72cd](https://github.com/NSPC911/rovr/commit/2ca72cd6dbac15d79cef84040fe579804157f408)

### Build

- add support for building with nuitka [#206](https://github.com/NSPC911/rovr/pull/206)

## [0.7.0.dev3] - 2026-01-25

### Added

- `app`: add force tty option [#197](https://github.com/NSPC911/rovr/pull/197)
- `app`: add batch rename support [#198](https://github.com/NSPC911/rovr/pull/198)
- `screens`: add file list to screen for paste and delete files [#202](https://github.com/NSPC911/rovr/pull/202) [17275d3](https://github.com/NSPC911/rovr/commit/17275d37216c139c3f6560696a5f421ab9992004)
- [BREAKING] `actions`: add extra panel for copy related actions [#200](https://github.com/NSPC911/rovr/pull/200)
- `config`: refuse to launch if template config is tampered [1dcdd98](https://github.com/NSPC911/rovr/commit/1dcdd9885d064a18ae577e976c72ce64936fc1c3)

### Fixed

- `app`: prevent weird image preview bug that makes it scroll up [9fddec4](https://github.com/NSPC911/rovr/commit/9fddec4a69f5f3353e4603eb1e27586458d374c6)
- `filelist`: add safeguard from crash [bab18b0](https://github.com/NSPC911/rovr/commit/bab18b0b84860f938ee28945402f2f5192a8d540)
- `firstrun`: use the proper dependency [dd3c89d](https://github.com/NSPC911/rovr/commit/dd3c89d57602fe968339e5edf81d882cbfd3531b)
- `app`: fix cd on startup not working [3dda6b6](https://github.com/NSPC911/rovr/commit/3dda6b6615c4a2e2ef391857fb4b2a080b0d88de)
- `screens`: improve button color coding [9a87831](https://github.com/NSPC911/rovr/commit/9a8783124ec07e2e58fb9bad8c415360c7109ef4)
- `pinned_sidebar`: fix sidebar not appearing due to textual [eee1599](https://github.com/NSPC911/rovr/commit/eee1599056bee0fecbe3603cabaef08c5ba43344)
- `preview`: load and close image files [a04d252](https://github.com/NSPC911/rovr/commit/a04d252cde76a2019765d5e687ba966febfd4f72)
- `screens`: use more horizontal breakpoints for better layout [abd78a3](https://github.com/NSPC911/rovr/commit/abd78a32a868e41086855d3b5f4223340d198ca7)

### Performance

- `config`: improve schema checking performance [abb1606](https://github.com/NSPC911/rovr/commit/abb16066bcb5447bb822cf427619485854b67cb4)

### Removed

- [BREAKING] `plugins`: moved `plugins.editor` to `settings.editor` [#198](https://github.com/NSPC911/rovr/pull/198)
- [BREAKING] `preview`: removed image resizer [99ca469](https://github.com/NSPC911/rovr/commit/99ca469fb1412a6802d2c9763f2e9f27ef984755)

## [0.7.0.dev2] - 2026-01-12

### Added

- `cli`: add `--config-folder` option to specify custom config folder [#185](https://github.com/NSPC911/rovr/pull/185)
- `filelist`: dim files/folders that are cut in clipboard [#188](https://github.com/NSPC911/rovr/pull/188)
- `filelist/state`: option to remember sort order per folder [#193](https://github.com/NSPC911/rovr/pull/193)
- `log`: improve logging mechanism [f8c0988](https://github.com/NSPC911/rovr/commit/f8c0988fa12b1e00c38c1624d6daf8b170f6108d)
- `config`: provide two separate profiles for keybinds [#179](https://github.com/NSPC911/rovr/pull/179)

### Changed

- [BREAKING] `app`: remove `modes` (use `--config-folder`) [#195](https://github.com/NSPC911/rovr/pull/195)
- [BREAKING] `config`: allow additional flags in config [#191](https://github.com/NSPC911/rovr/pull/191)
- `preview`: batch pdf loading [#184](https://github.com/NSPC911/rovr/pull/184)
- `app`: stop causing triple threads to occur [f8e015f](https://github.com/NSPC911/rovr/commit/f8e015f9de3d171c9fb03a83f92eede312dc9030)
- `clipboard`: slightly refactor code [#188](https://github.com/NSPC911/rovr/pull/188)
- `mixins`: mixin filelist, clipboard and rgsearch [644e4e3](https://github.com/NSPC911/rovr/commit/644e4e3e14c21790b67a95ef65eb2bf972067b01)

### Fixed

- `filelist`: properly show file list checkboxes [8a63ce9](https://github.com/NSPC911/rovr/commit/8a63ce919e26e8b649a49c59c91bb505f302e9d4)
- `app`: stop watching thread from exiting [5459741](https://github.com/NSPC911/rovr/commit/545974139a0b8444de2a74dd07378ffcfb7e419c)

## [0.7.0.dev1] - 2026-01-01

### Added

- `archive`: add support for zstd archives [#172](https://github.com/NSPC911/rovr/pull/172)
- `app`: add log dump when errors occur [a5f38ca](https://github.com/NSPC911/rovr/commit/a5f38cad1777f404115fd27d7a80a38b370041ce) [e046f8d](https://github.com/NSPC911/rovr/commit/e046f8dd5689a36dc0de70963452d3ba26fa8489) [ac9f129](https://github.com/NSPC911/rovr/commit/ac9f1299b4af587d5ddffb48da1c4049db35cdff)
- `rg`: add support for rg as plugin [#175](https://github.com/NSPC911/rovr/pull/175)
- `preview`: configurable max preview image size [#178](https://github.com/NSPC911/rovr/pull/178)
- `cli`: add dev crash [ac9f129](https://github.com/NSPC911/rovr/commit/ac9f1299b4af587d5ddffb48da1c4049db35cdff)

### Changed

- [BREAKING] `preview`: add support for mime types using puremagic [#172](https://github.com/NSPC911/rovr/pull/172)
- [BREAKING] `config`: remove unused preview texts [1b8deb6](https://github.com/NSPC911/rovr/commit/1b8deb69ce7102cf65d8e4021a23eb27e3b29669)
- [BREAKING] `preview`: use threads as far as possible [#172](https://github.com/NSPC911/rovr/pull/172) [#183](https://github.com/NSPC911/rovr/pull/183)
- `deps`: bump textual to ~=6.9 [09d1d23](https://github.com/NSPC911/rovr/commit/09d1d23a0b1d2ea5f6de39de205577dce87f1190)
- `preview`: load images, and resize them in a separate thread [#178](https://github.com/NSPC911/rovr/pull/178)
- `preview`: check mtime before loading preview again [9d7c6cf](https://github.com/NSPC911/rovr/commit/9d7c6cfb8e7f84a4c308a3f19ad2ed21eabdcccb)

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
- `cli`: output fix for certain commands [1251ca8](https://github.com/NSPC911/rovr/commit/1251ca81bcab803cfa00cddf6d935a239b62dd07)

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
- `rename_button`: properly stop execution after error [fee8bd0](https://github.com/NSPC911/rovr/commit/fee8bd0b70151f1bb8a4dcb0885390cf023cb11c)
- `screens`: add click to exit modal screen

### Removed

- `process + screens`: remove permission asker modal

## [0.6.0rc1] - 2025-12-14

### Added

- `clipboard`: constantly check clipboard added files [81df523](https://github.com/NSPC911/rovr/commit/81df523b06c5875436410a8adc79556eb872aacf)
- `config`: allow changing bindings for screen layers [#161](https://github.com/NSPC911/rovr/pull/161)
- `fd`: add additional toggleable options [#163](https://github.com/NSPC911/rovr/pull/163)
- `icons`: show icon for symlink/junctions [e6a354a](https://github.com/NSPC911/rovr/commit/e6a354a87e7b326f29c3b16edf148c49e78ecc55)
- `icons`: show separate symlink/junction icon [fbf2a08](https://github.com/NSPC911/rovr/commit/fbf2a088d2d11617b764399f87a99d83928d1c67)

### Changed

- [BREAKING] `fd`: rename from 'finder' to 'fd' [#163](https://github.com/NSPC911/rovr/pull/163)
- [BREAKING] `sort_order`: add custom keybind support [#168](https://github.com/NSPC911/rovr/pull/168)
- `pip`: switch to tomli for toml parsing [#162](https://github.com/NSPC911/rovr/pull/162)
- `filelist`: use custom set_options method [e6a354a](https://github.com/NSPC911/rovr/commit/e6a354a87e7b326f29c3b16edf148c49e78ecc55)
- `screenshots`: perhaps fix the broken fonts [#166](https://github.com/NSPC911/rovr/pull/166)

### Fixed

- `filelist`: fix issue with empty directories preventing navigation [985a509](https://github.com/NSPC911/rovr/commit/985a5092cbcc9917005882ead10286043b42e4a4)
- `input`: fix overscroll issue [a8b5307](https://github.com/NSPC911/rovr/commit/a8b530766aad75e595b1bcdd90bce0c37d65af42)

## [0.6.0.dev2] - 2025-12-02

### Added

- `preview`: add support for using file(1) [#157](https://github.com/NSPC911/rovr/pull/157)

### Changed

- [BREAKING] `cd-on-quit`: remove match type key [32a389f](https://github.com/NSPC911/rovr/commit/32a389fe3c5465b6daec4b0d89751019414c72b9)
- `icons`: use fnmatch instead of using scuffed methods [4c848a1](https://github.com/NSPC911/rovr/commit/4c848a158615646144c3b7aac7255540218e8348)
- `preview`: use pygments instead of tree-sitter [e95350f](https://github.com/NSPC911/rovr/commit/e95350f49f80e8e76e2ceb35567ffd910bd87ccc)
- `style`: fix errors related to ty alpha 28 [ce59c07](https://github.com/NSPC911/rovr/commit/ce59c0777b35f5260af945030c32c0935d933e64)
- `cd-on-quit`: use more robust functions [32a389f](https://github.com/NSPC911/rovr/commit/32a389fe3c5465b6daec4b0d89751019414c72b9)

### Fixed

- `screens`: add click to exit modal screen [d84e9a8](https://github.com/NSPC911/rovr/commit/d84e9a89c228b609c940763056317d0eec6e3503)
- `finder`: use pseudo exclusive worker to prevent error spam [c9a7741](https://github.com/NSPC911/rovr/commit/c9a77413073b8c9d0bd3b5738f1512417fbc9971)
- `archive`: just gamble which archive type it is [7fe26f6](https://github.com/NSPC911/rovr/commit/7fe26f60e934b9e2301cac44f6ff825c7940d5ce)
- `cli`: don't load everything when using certain functions [18558b9](https://github.com/NSPC911/rovr/commit/18558b9876b89bdddd63241ffde2768d38c15b0c)

### Removed

- `process + screens`: remove permission asker modal [8caa4f9](https://github.com/NSPC911/rovr/commit/8caa4f9ffefe80225c1cf93eaf5418dd3d0ce6e9)

## [0.6.0.dev1] - 2025-11-24

### Added

- `app`: use textual's tree instead of a custom tree [a1d7449](https://github.com/NSPC911/rovr/commit/a1d744939305f9e396ecfc356fedcf70e03c6b63)
- `app+config`: add support for modes [#154](https://github.com/NSPC911/rovr/pull/154)
- `config`: auto-detect editor to use [5f1d7f8](https://github.com/NSPC911/rovr/commit/5f1d7f87b0e2cd7bed40205c931273daa849b3c1)
- `config`: add support for more keys [294d9bb](https://github.com/NSPC911/rovr/commit/294d9bb5294f1a9150b5184e4299f2a8b579b2a2)
- `editor`: add config to suspend when opening editor [ed605da](https://github.com/NSPC911/rovr/commit/ed605da0c4f8a26ece28d8a4da18ca26c79ed5c2)
- `editor`: add config to open all files in the editor [8189699](https://github.com/NSPC911/rovr/commit/8189699602e5e59e5a0c65b131d80c2fdbcc6ac6)
- `preview`: add pdf preview support with poppler [#153](https://github.com/NSPC911/rovr/pull/153)

### Changed

- `preview`: open image in thread [db617a0](https://github.com/NSPC911/rovr/commit/db617a06453cac3a04b712dbe25ce8c3d681bcb2)

## [0.5.0] - 2025-11-15

### Added

- add sort order switcher (##145) [f458a54](https://github.com/NSPC911/rovr/commit/f458a54d269f7c9f09ebe7c4497f055649a21d73)
- `app`: add scrolloff behaviour to filelist (##139) [c2a38fb](https://github.com/NSPC911/rovr/commit/c2a38fb27e11f080518152519ae01927eb75d544)
- `app`: add show key option + slight refactor [756bb38](https://github.com/NSPC911/rovr/commit/756bb3812af10e7d1b6f280d874864e3cde65a1d)
- `app`: add tree view command [4fc1a80](https://github.com/NSPC911/rovr/commit/4fc1a8070f1cf62fc67e1fc385b70c3d4272dbce)
- `app`: add a state manager (##146) [5ad938f](https://github.com/NSPC911/rovr/commit/5ad938f97cc45b4534de4486b244e22b30f78c90)

### Changed

- [BREAKING] improve preview container and config functions (##135) [530c507](https://github.com/NSPC911/rovr/commit/530c50771fdee3e5e0456bce94088c4cd0b338d8)
- [BREAKING] `app`: expand compact mode into two options [b2afee6](https://github.com/NSPC911/rovr/commit/b2afee604f1bc10881a343f3d3fe86a9874bca55)
- [BREAKING] `app`: remove cd on quit in favour of `--cwd-file` (##126) [9b4c6b7](https://github.com/NSPC911/rovr/commit/9b4c6b7c580c1f2945a969448082f1a78ee22fb8)
- [BREAKING] `schema`: decline some keycodes [ac0b736](https://github.com/NSPC911/rovr/commit/ac0b736c1f268f2b635737197cebd01bd208e0b1)
- `app`: show any stylesheet errors as is [a1aae91](https://github.com/NSPC911/rovr/commit/a1aae911a254d143a757f00e5fa08e58e929e475)
- `deps`: bump astro, starlight, and vite for documentation
- `ci`: update formatting, ty, and documentation workflows
- `docs`: document undocumented features and rephrase content (##147)
- `logo`: change ascii logo [1a15b7f](https://github.com/NSPC911/rovr/commit/1a15b7fa1907b7fde6babd7d8793d390ee86ed48)
- `app`: improve borders, compact mode, and css change handling
- `config`: improve required adder and resource loading
- `fileinuse`: add skip + retry buttons and toggle (##137)
- `filelist`: improve archive preview performance and container refactor
- `preview`: add progress showcase [c332da1](https://github.com/NSPC911/rovr/commit/c332da1fc1a8d71cabe68bf33886cea6f2204f07)
- `processes`: improve permission error handling [4246b72](https://github.com/NSPC911/rovr/commit/4246b721447b5875c3a8a83bf3b0c7b38c0dff3c)
- `zoxide`: switch to proper worker and asyncio
- `perf`: reduce string compression, switch to base64, and improve path_utils performance
- `logging`: switch to using self.log instead of print
- `finder`: switch to asyncio [faecb1a](https://github.com/NSPC911/rovr/commit/faecb1a4a910446a0cc4560568cd89e4c0d873b0)
- `session`: use list[str] for session directories [92bdb07](https://github.com/NSPC911/rovr/commit/92bdb071d4e840f450cffb00fc5f84ed76dc30b1)

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

[Unreleased]: https://github.com/NSPC911/rovr/compare/v0.9.1.post2...HEAD
[0.9.1.post2]: https://github.com/NSPC911/rovr/compare/v0.9.1.post1...v0.9.1.post2
[0.9.1.post1]: https://github.com/NSPC911/rovr/compare/v0.9.1...v0.9.1.post1
[0.9.1]: https://github.com/NSPC911/rovr/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/NSPC911/rovr/compare/v0.8.2.post1...v0.9.0
[0.8.2]: https://github.com/NSPC911/rovr/compare/v0.8.1...v0.8.2.post1
[0.8.1]: https://github.com/NSPC911/rovr/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/NSPC911/rovr/compare/v0.8.0rc1...v0.8.0
[0.8.0rc1]: https://github.com/NSPC911/rovr/compare/v0.8.0.dev3...v0.8.0rc1
[0.8.0.dev3]: https://github.com/NSPC911/rovr/compare/v0.8.0.dev2...v0.8.0.dev3
[0.8.0.dev2]: https://github.com/NSPC911/rovr/compare/v0.8.0.dev1...v0.8.0.dev2
[0.8.0.dev1]: https://github.com/NSPC911/rovr/compare/v0.7.0...v0.8.0.dev1
[0.7.0]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev3...v0.7.0
[0.7.0.dev3]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev2...v0.7.0.dev3
[0.7.0.dev2]: https://github.com/NSPC911/rovr/compare/v0.7.0.dev1...v0.7.0.dev2
[0.7.0.dev1]: https://github.com/NSPC911/rovr/compare/v0.6.0...v0.7.0.dev1
[0.6.0]: https://github.com/NSPC911/rovr/compare/v0.6.0rc1...v0.6.0
[0.6.0rc1]: https://github.com/NSPC911/rovr/compare/v0.6.0.dev2...v0.6.0rc1
[0.6.0.dev2]: https://github.com/NSPC911/rovr/compare/v0.6.0.dev1...v0.6.0.dev2
[0.6.0.dev1]: https://github.com/NSPC911/rovr/compare/v0.5.0...v0.6.0.dev1
[0.5.0]: https://github.com/NSPC911/rovr/compare/v0.4.0...v0.5.0
