*Details from the [Contribution Guide].*

**Before Merging:**
- [ ] Update the version in [`__about__.py`] (see the Contribution Guide guide for more information).
- [ ] Update the relevant section of the [Changelog] with release notes.
  You may need to view the commit history since the last release to identify any changes that were missed.

**Merging:**
- [ ] Merge this PR manually with a signed merge commit.
  ```sh
  # Using "v0.1a" as an example version
  git checkout main
  git merge --no-ff --sign --edit ${source branch}
  ```
  An editor will open to edit the commit message, which should be the content of the changelog with some tweaks (see the [Contribution Guide]).

  Don't forget to `git push` the merge commit.

**After Merging:**
- [ ] Create a signed and annotated tag with the current release's changelog:

  ```sh
  git tag --gpg-sign $VERSION # e.g., v0.1a
  ```
  An editor will open to edit the annotation, which should be the content of the changelog with some tweaks (see the [Contribution Guide]).

  Don't forget to `git push origin refs/tags/$VERSION`
- [ ] Create a GitHub Release for the new tag. The title should be the release version (e.g., `v0.1a`).
  The release notes will be the same tweaked changelog contents (see the [Contribution Guide]).
  If the release is a pre-release (`a`, `b`, or `rc` suffixes) make sure to check the "Set as a pre-release" box.

[Contribution Guide]: https://github.com/Sidneys1/Memoria/blob/main/CONTRIBUTING.md#performing-a-release
[`__about__.py`]: https://github.com/Sidneys1/Memoria/blob/main/src/memoria/__about__.py#L1
[Changelog]: https://github.com/Sidneys1/Memoria/blob/main/CHANGELOG.md?plain=1#L9-L10
