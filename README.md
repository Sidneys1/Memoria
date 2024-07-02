<div align="center">

![Memoria Splash Logo](./src/memoria/web/www/static/splash.png)

# Memoria

A selfhosted service for indexing and searching personal web history.

[![Container Image CI](https://github.com/Sidneys1/Memoria/actions/workflows/deploy-image.yml/badge.svg?branch=main&event=push)](https://github.com/Sidneys1/Memoria/actions/workflows/deploy-image.yml)
[![Build and Publish Releases](https://github.com/Sidneys1/Memoria/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Sidneys1/Memoria/actions/workflows/python-publish.yml)
![PyPI - Version](https://img.shields.io/pypi/v/memoria_search?style=flat&logo=pypi&label=Python%20Package&color=%2371ca60)

</div>

Memoria ingests URLs from browsing history, then scrapes and indexes the web content to create a personalized search
engine.

**Sections**<br>
🚀 [§ Running Memoria](#running-memoria)<br>
⚙️ [§ Configuration](#configuration)<br>
🧩 [§ Plugins](#plugins)

**Other Documentation**<br>
📃 [Changelog](./CHANGELOG.md)<br>
📦 [Building](./BUILDING.md)<br>
🤝 [Contributing](./CONTRIBUTING.md)<br>
⚖️ [License](./LICENSE)<br>
📑 [Plugin Development](./docs/Plugin%20Development.md)

Running Memoria
---------------

To run Memoria you will need an Elasticsearch instance. The "Running With Containers" example will start one for you, or
you can [deploy one manually][es] and [configure Memoria](#configuration) to connect to it. Once Memoria is running via
one of the methods below you can access the web interface at `http://localhost/`.

<details><summary>Running With Python</summary>

```sh
# Install from PyPI:
python3 -m pip install memoria_search
# Or from source code:
python3 -m pip install .

# Run:
python3 -m memoria.web --port 80

# Or run from source code without installing (you may need to install some dependencies):
PYTHONPATH=./src python -m memoria.web --port 80
```

**Notes**:
- Your distribution may require that you [create a virtual environment][venv] to install Python packages.
- Memoria is currently designed to run under Python 3.12. Your mileage may vary attempting to run under Python 3.11.

</details>

<details><summary>Running With Containers</summary>

Self-contained Compose (including an Elasticsearch instance):
```sh
# With Docker Compose or Podman Compose:
podman-compose --profile elasticsearch up

# Cleanup:
podman-compose down --volumes
```

Single Docker container (for use with an existing Elasticsearch instance):
```sh
# Build or pull
podman build -t ghcr.io/sidneys1/memoria .
podman pull ghcr.io/sidneys1/memoria

# With plain Docker or Podman
podman run --name memoria -e MEMORIA_ELASTIC_HOST=http://hostname:9200/ -p 80 ghcr.io/sidneys1/memoria

# Cleanup:
podman container rm memoria
podman image rm ghcr.io/sidneys1/memoria
```

**Note** that Podman commands may require `sudo` to run, or that you
[configure your Podman environment to run rootless][pmr].

</details>

<details><summary>Advanced Container Deployment</summary>

You can deploy Memoria as a container. The provided [`Containerfile`](./Containerfile) builds a lightweight image based
on `python:3.12-alpine`, which runs Memoria under [Uvicorn][uv] on the exposed port 80.

```sh
podman build -t sidneys1/memoria .
```

You can also deploy Memoria with [Docker Compose][dc] or [Podman Compose][pc] (as shown here).

The file [`compose.yaml`](./compose.yaml) shows the most basic Compose strategy, building and launching a Memoria
container. You can use Memoria with an existing Elasticsearch instance like so[^1]:

```sh
# You may want to use the `memoria_elastic_password` secret by uncommenting the
# relevant sections of `compose.yaml` and running:
printf 'my-password-here' | podman secret create memoria_elastic_password -

export ELASTIC_HOST=http://hostname:9200/
podman-compose up --build 
```

[^1]: See [§Configuration](#configuration) for more environment variables and configuration options.

A Compose profile named `elasticsearch` is also provided that will additionally launch an Elasticsearch container.

```sh
# To start self-contained. See notes below regarding default credentials.
podman-compose up --build --profile elasticsearch
```

</details>

> [!NOTE]
> Currently the only way to import browser history is by uploading a browser history database on the Settings page. More import strategies are [coming soon&trade;](https://github.com/Sidneys1/Memoria/issues/1).

Configuration
-------------

### Options

Memoria has several deployment configuration options that control overall behavior. These can be set via environment
variables or container secrets. The following configuration options are provided:

<details>

<table>
    <thead>
        <tr><td></td>
            <th>Name</th> <th>Description</th> <th>Default</th></tr>
    </thead>
    <tbody>
        <tr><th rowspan="4">Importing</th>
            <td><code>downloader</code></td>     <td>The downloader plugin<sup><a href="#plugins">§</a></sup> to use</td>    <td><code>AiohttpDownloader</code></td></tr>
        <tr><td><code>extractor</code></td>      <td>The extractor plugin<sup><a href="#plugins">§</a></sup> to use</td>     <td><code>HtmlExtractor</code></td></tr>
        <tr><td><code>filter_stack</code></td>   <td>A list of filter plugins<sup><a href="#plugins">§</a></sup> to use</td> <td><code>["HtmlContentFinder"]</code></td></tr>
        <tr><td><code>import_threads</code></td> <td>The maximum number of processes to use to download history items</td>   <td>

$\frac{cpus}{2}$[^2]</td></tr>
    </tbody>
    <tbody>
        <tr><th rowspan="4">Databases</th>
            <td><code>database_uri</code></td>     <td>Connection URI to the Memoria database</td>   <td><code>sqlite+aiosqlite:///./data/memoria.db</code></td></tr>
        <tr><td><code>elastic_host</code></td>     <td>Elasticsearch connection URI</td>             <td><code>http://elasticsearch:9200</code></td></tr>
        <tr><td><code>elastic_user</code></td>     <td rowspan="2">Elasticsearch Authentication</td> <td><code>elastic</code></td></tr>
        <tr><td><code>elastic_password</code></td>                                                   <td><em>None</em></td></tr>
    </tbody>
</table>

[^2]: Or `1` if CPU count cannot be determined.

Any of these settings can be configured with uppercase environment variables prefixed with `MEMORIA_` (e.g.,
`MEMORIA_ELASTIC_PASSWORD`). Additionally, settings can be read from files from `/run/secrets`[^3], which will take
precedence over any environment variables. For example, to set `elastic_password` with a Docker or Podman secret, you
can:

```sh
printf 'my-password-here' | podman secret create memoria_elastic_password -
podman run --name memoria --secret memoria_elastic_password -p 80 sidneys1/memoria
```

</details>

[^3]: The secrets directory can be overridden with the `SECRETS_DIR` environment variable.

Plugins
-------

Memoria utilizes a plugin architecture that allows for different methods of downloading URLs, transforming the
downloaded content, and extracting indexable plain text from the content. Selecting which plugins Memoria will use for
web content retrieval and processing is described in [§Configuration](#configuration).

<details>

There are currently three types of Memoria Plugins used during web content retrieval and processing:
- **Downloaders**<br>
  Downloaders are responsible for accessing a URL and retrieving its content from the internet. They can provide this
  content in many different formats to the next plugin in the stack. The most basic Downloaders (like the built-in
  default, `AiohttpDownloader`) only support downloading raw HTML to provide to the remaining plugins.

- **Filters**<br>
  Filters transform input from the previous plugin in the stack (either the Downloader or another Filter). They can
  change the content format or modify it in place.
  
  By default Memoria uses the built in `HtmlContentFinder` plugin to remove extraneous HTML elements and prune the input
  to a single `<main>`, `<article>`, or `<... id="content">` element (if one exists).

- **Extractors**<br>
  Extractors are the last plugin to run, and are responsible for converting the input from the previous plugin (either
  the Downloader or the last Filter) into plain text that will be stored in Elasticsearch for indexing and searching.
  
  By default Memoria uses the built in `HtmlExtractor` plugin to convert the input HTML into plain text. It also searches
  the original downloaded HTML (before any potential modification by Filter plugins) for `<meta ...>` values that could
  be used to enrich the Elasticsearch document, such as `"author"` or `"description"`.

Other types of plugins:
- **Scraping Rule Filters**<br>
  Scraping rule filter plugins allow the Scraping Rules in the Settings UI to be extended with new functionality. These
  filters help determine which history URLs will be retrieved and scraped.

</details>

<!-- TODO: section on scraping rule plugins -->

> [!TIP]
> See the [📑 Plugin Development](./docs/Plugin%20Development.md) guide for information on developing your own Memoria plugins.

[es]: https://www.elastic.co/guide/en/elasticsearch/reference/current/getting-started.html
[venv]: https://docs.python.org/3/tutorial/venv.html
[pmr]: https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md
[uv]: https://www.uvicorn.org/
[dc]: https://docs.docker.com/compose/
[pc]: https://github.com/containers/podman-compose

<!-- cSpell:ignore PYTHONPATH aiohttp StackOverflow CPUs aiosqlite -->
<!-- cSpell:words Sidneys1 Uvicorn Downloaders Containerfile -->
