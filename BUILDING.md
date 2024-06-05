Building
========

For instructions on performing a release, see the [Contribution Guide](./CONTRIBUTING.md#performing-a-release).

Python
------

Memoria is built using the Python build system [Hatch][hatch]. To build a wheel or source tarball, you must:

1. Ensure Sass runs against any files in the [templates][templates-folder] and [static][static-folder] web content
   folders.

   ```sh
   # For example, using NPX:
   npx sass src/memoria/web/www/static/:src/memoria/web/www/static/ \
            src/memoria/web/www/templates/:src/memoria/web/www/templates/
   ```

2. Build the package with `hatch build`:

   ```sh
   hatch build
   ```

   The resulting source archive and wheel will be output in `./dist`.

[hatch]: https://github.com/pypa/hatch
[templates-folder]: ./src/memoria/web/www/templates/
[static-folder]: ./src/memoria/web/www/static/

Containers
----------

The [Containerfile](./Containerfile) builds Memoria entirely, including running Sass:

```sh
podman build -t ghcr.io/sidneys1/memoria .
# Or
podman-compose build memoria

# If using the Docker toolchain you may need to provide the -f parameter:

docker build -f Containerfile -t ghcr.io/sidneys1/memoria .
# Or
docker-compose -f compose.yaml build memoria
```
