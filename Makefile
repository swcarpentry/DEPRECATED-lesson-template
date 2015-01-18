# R Markdown files.
SRC_RMD = $(wildcard ??-*.Rmd)
DST_RMD = $(patsubst %.Rmd,%.md,$(SRC_RMD))

# All Markdown files (hand-written and generated).
SRC_MD = $(wildcard *.md) $(DST_RMD)
DST_HTML = $(patsubst %.md,%.html,$(SRC_MD))

# All outputs.
DST_ALL = $(DST_HTML)

# Inclusions.
INCLUDES = \
	-Vheader="$$(cat _includes/header.html)" \
	-Vbanner="$$(cat _includes/banner.html)" \
	-Vfooter="$$(cat _includes/footer.html)" \
	-Vjavascript="$$(cat _includes/javascript.html)"

# Chunk options for knitr (used in R conversion).
R_CHUNK_OPTS = tools/chunk-options.R

# Default action is to show what commands are available.
all : commands

## preview  : Build website locally for checking.
preview : $(DST_ALL)

# Pattern for slides (different parameters and template).
motivation.html : motivation.md _layouts/slides.revealjs
	pandoc -s -t revealjs \
	--template=_layouts/slides \
	-o $@ $<

# Pattern to build a generic page.
%.html : %.md _layouts/page.html
	pandoc -s -t html \
	--template=_layouts/page \
	--filter=tools/filters/blockquote2div.py \
	--filter=tools/filters/id4glossary.py \
	$(INCLUDES) \
	-o $@ $<

## unittest : Run unit test (for Python 2 and 3)
unittest: tools/check.py tools/validation_helpers.py tools/test_check.py
	cd tools/ && python2 test_check.py
	cd tools/ && python3 test_check.py

# Pattern to convert R Markdown to Markdown.
%.md: %.Rmd $(R_CHUNK_OPTS)
	Rscript -e "knitr::knit('$$(basename $<)', output = '$$(basename $@)')"

## commands : Display available commands.
commands : Makefile
	@sed -n 's/^##//p' $<

## settings : Show variables and settings.
settings :
	@echo 'SRC_RMD:' $(SRC_RMD)
	@echo 'DST_RMD:' $(DST_RMD)
	@echo 'SRC_MD:' $(SRC_MD)
	@echo 'DST_HTML:' $(DST_HTML)

## clean    : Clean up temporary and intermediate files.
clean :
	@rm -rf $$(find . -name '*~' -print)

# very-clean : Remove generated HTML.
very-clean :
	@rm -f $(DST_MD)
