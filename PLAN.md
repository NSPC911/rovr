## Widget tests

### `tests/test_metadata_container.py`

**Source:** `src/rovr/footer/metadata_container.py`

`MetadataContainer.info_of_dir_entry()` is a self-contained method that builds a Unix-style permission string. It can be called directly on a bare `MetadataContainer()` instance without a running app.

| Scenario          | What to test                                           |
| ----------------- | ------------------------------------------------------ |
| Regular file      | Prefix char is `"-"`, followed by nine permission bits |
| Directory         | Prefix char is `"d"`                                   |
| Symlink           | Prefix char is `"l"`                                   |
| Unknown type      | Returns `"???????"`                                    |
| Inaccessible path | Returns `"?????????"` without raising                  |
