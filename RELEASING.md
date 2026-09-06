# Publishing to PyPI

The `.github/workflows/publish.yml` workflow publishes when a `v*` tag is pushed.
It runs tests on Python 3.10 and 3.14, requires the tag to match the package version,
builds the wheel and source distribution, validates their metadata, and checks wheel
installation before uploading the same artifacts to PyPI.

Publishing uses GitHub OIDC through PyPI Trusted Publishing. No PyPI API token or
GitHub repository secret is needed. Only the publishing job receives `id-token: write`.

## One-time PyPI setup

For the first release, sign in to https://pypi.org/manage/account/publishing/ and add
a **pending publisher** using the GitHub form:

| Field | Value |
| --- | --- |
| PyPI project name | `pdf-diff-sbs` |
| Owner | `matplo` |
| Repository name | `pdf-diff-sbs` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

The workflow name is the filename only, not the path or the workflow's display name.
The GitHub repository has a `pypi` environment restricted to `v*` tags. If the PyPI
project already exists under your account, add the same publisher under the project's
Publishing settings instead of adding a pending publisher.

See the official [pending publisher instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [Trusted Publishing workflow documentation](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## First release

The prepared version is `0.1.1`; the existing `v0.1.0` tag predates the publishing
workflow and remains unchanged. After configuring the publisher, run from a clean,
up-to-date checkout of `main`:

```bash
git tag -a v0.1.1 -m "Release 0.1.1"
git push origin v0.1.1
```

Pushing the tag starts the upload automatically after successful validation.
The first successful upload creates the PyPI project. Watch the **Publish to PyPI**
workflow in GitHub Actions for the result.

## Later releases

1. Update `project.version` in `pyproject.toml` and commit and push the change.
2. Push a matching `vVERSION` tag on that commit.
3. Check that the publishing workflow succeeds.

Use a new version for each release. Do not move an existing release tag or reuse a
published version. To validate without publishing, use **Run workflow** on
`publish.yml`; manual runs always skip the upload job. An ordinary push to `main`
also does not publish.

If a tag run fails because its publisher has not been configured, add the publisher
and rerun the failed publishing job in GitHub Actions.
