# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

import os

assets_dir = os.path.dirname(__file__)
bases = ("production", "staging", "snapshot")


def walk():
    for base in bases:
        for asset_base, packages, _ in os.walk(os.path.join(assets_dir, base)):
            for package in packages:
                for _, versions, _ in os.walk(os.path.join(asset_base, package)):
                    for version in versions:
                        yield base, package, version
                    break
            break


def get_meta(base, package, version):
    import yaml

    meta_filename = os.path.join(assets_dir, base, package, version, "meta.yml")
    if os.path.exists(meta_filename):
        with open(meta_filename) as f:
            return yaml.safe_load(f)


def get_remote_entries(package, repo):
    from github import GithubException

    for branch in bases:
        try:
            contents = repo.get_contents(package, ref=branch)
        except GithubException:
            continue

        while contents:
            content = contents.pop(0)
            if content.type == "dir":
                contents += repo.get_contents(content.path, ref=branch)
            else:
                yield content
        break


def download_remote_entries(package, entries, outdir):
    from requests_futures.sessions import FuturesSession
    from concurrent.futures import as_completed

    session = FuturesSession()
    futures = []

    for entry in entries:
        future = session.get(entry.download_url)
        future.entry = entry
        futures.append(future)

    for future in as_completed(futures):
        res = future.result()
        res.raise_for_status()

        filename = future.entry.path.replace(package, outdir)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            f.write(res.content)

    return len(futures)
