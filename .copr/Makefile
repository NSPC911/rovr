SPECFILE := .copr/rovr.spec
NAME := rovr
VERSION := $(shell python3 -c 'import pathlib,tomllib;print(tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])')
TARBALL := $(NAME)-$(VERSION).tar.gz

.PHONY: srpm
srpm:
	git archive --format=tar.gz --prefix=$(NAME)-$(VERSION)/ HEAD > $(TARBALL)
	rpmbuild -bs --define "_sourcedir $(PWD)" --define "_specdir $(PWD)/.copr" --define "_srcrpmdir $(outdir)" $(SPECFILE)
