This directory contains client-side hooks that lesson maintainers can
use to regenerate HTML files and update zip files if necessary.

With this hook enabled, lesson maintainers will no longer have to update
the lesson data zip file or execute `make preview` to regenerate HTML.
This will be done automatically as part of the post-commit hook.

If you want to commit only the regenerated HTML and/or the updated zip file, 
There are two options:

1. Regenerate HTML or update the zip file manually, just as you would
without the hooks. The post-commit `make preview` and the `zip` commands
won't update a file that's already up-to-date.
2. Submit an empty commit using `git commit --allow-empty`. Remember
to use a descriptive commit message even though you are using an
"empty" commit. After your commit, the post-commit script will add the
regenerated HTML and/or updated zip file.

To use the hooks, first edit the parameters `ZIP_FILE` and `DATA_DIR`
in the `post-commit` script. Then create symlinks in the `.git/hooks`
directory by executing the following commands from anywhere within the
project's file tree

```bash
# Go to the .git/hooks directory.
cd "$(git rev-parse --show-toplevel)"/.git/hooks
# Create symlinks.
ln -s -f ../../tools/maintainer_hooks/pre-commit pre-commit
ln -s -f ../../tools/maintainer_hooks/post-commit post-commit
# Go back to where you were.
cd -
```
