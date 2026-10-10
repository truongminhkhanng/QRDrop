"""Plan a new PhoneDrop release without mutating tags, releases or assets."""
import json
import os
from pathlib import Path
import re
import subprocess


TAG = re.compile(r'phonedrop-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')


def release_tag(ref):
    for prefix in ('refs/tags/', 'refs/heads/release/'):
        if ref.startswith(prefix):
            tag = ref[len(prefix):]
            if TAG.fullmatch(tag):
                return tag
    raise ValueError('Use phonedrop-vMAJOR.MINOR.PATCH as a tag or release branch.')


def require_newer(tag, existing):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError('Invalid PhoneDrop release version.')
    requested = tuple(map(int, match.groups()))
    for previous in existing:
        old = TAG.fullmatch(previous)
        if old and requested <= tuple(map(int, old.groups())):
            raise ValueError(f'{tag} must be newer than existing release {previous}.')


def main():
    tag = release_tag(os.environ['GITHUB_REF'])
    repo = os.environ['GITHUB_REPOSITORY']

    def gh(*args):
        return subprocess.check_output(['gh', 'api', *args], text=True).strip()

    existing = gh(f'repos/{repo}/releases?per_page=100', '--paginate',
                  '--jq', '.[].tag_name').splitlines()
    require_newer(tag, existing)
    refs = json.loads(gh(f'repos/{repo}/git/matching-refs/tags/phonedrop-v'))
    if any(ref['ref'] == f'refs/tags/{tag}' for ref in refs):
        # Resolve annotated tags as well as lightweight tags to the actual commit.
        target = gh(f'repos/{repo}/commits/{tag}', '--jq', '.sha')
        if target != os.environ['GITHUB_SHA']:
            raise ValueError('Existing tag points to a different commit; choose a new version.')
    version = tag.removeprefix('phonedrop-v')
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'tag={tag}\nversion={version}\n')
    print(f'Release ready: PhoneDrop {version} ({tag})')


if __name__ == '__main__':
    main()
