import pytest

from tools import release_version
from tools.release_version import release_tag, require_newer


@pytest.mark.parametrize('ref', [
    'refs/tags/phonedrop-v1.0.1', 'refs/heads/release/phonedrop-v1.0.1',
])
def test_release_ref_resolves_new_version(ref):
    assert release_tag(ref) == 'phonedrop-v1.0.1'


@pytest.mark.parametrize('ref', [
    'refs/heads/main', 'refs/heads/feature/phonedrop', 'refs/tags/v1.0.1',
    'refs/tags/phonedrop-v01.0.1', 'refs/tags/phonedrop-v1.0.1-rc1',
    'refs/tags/phonedrop-v1.0.1\nmalicious=true',
])
def test_release_ref_rejects_unrelated_or_nonstable_versions(ref):
    with pytest.raises(ValueError):
        release_tag(ref)


@pytest.mark.parametrize('candidate', ['phonedrop-v1.0.0', 'phonedrop-v0.9.9'])
def test_cannot_overwrite_or_make_older_version_latest(candidate):
    with pytest.raises(ValueError):
        require_newer(candidate, ['v9.0.0', 'phonedrop-v1.0.0'])


def test_version_comparison_is_numeric_and_ignores_qrdrop():
    require_newer('phonedrop-v1.0.10', ['v9.0.0', 'phonedrop-v1.0.9'])
    with pytest.raises(ValueError):
        require_newer('phonedrop-v1.0.9', ['phonedrop-v1.0.10'])


def test_all_previous_versions_are_checked_not_only_latest_or_first():
    with pytest.raises(ValueError):
        require_newer('phonedrop-v1.1.0', ['phonedrop-v1.0.0', 'phonedrop-v2.0.0'])


@pytest.mark.parametrize('tag_commit', ['tested-commit', 'different-commit'])
def test_existing_unpublished_tag_must_match_tested_commit(tmp_path, monkeypatch, tag_commit):
    output = tmp_path / 'outputs'
    for key, value in {'GITHUB_REF': 'refs/tags/phonedrop-v1.0.1',
                       'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_SHA': 'tested-commit',
                       'GITHUB_OUTPUT': str(output)}.items():
        monkeypatch.setenv(key, value)
    responses = iter(['phonedrop-v1.0.0\n',
                      '[{"ref":"refs/tags/phonedrop-v1.0.1"}]', tag_commit])
    monkeypatch.setattr(release_version.subprocess, 'check_output', lambda *args, **kwargs: next(responses))
    if tag_commit == 'tested-commit':
        release_version.main()
        assert output.read_text() == 'tag=phonedrop-v1.0.1\nversion=1.0.1\n'
    else:
        with pytest.raises(ValueError, match='different commit'):
            release_version.main()
        assert not output.exists()


def test_github_failure_stops_release_without_writing_outputs(tmp_path, monkeypatch):
    output = tmp_path / 'outputs'
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/release/phonedrop-v1.0.1')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.setenv('GITHUB_OUTPUT', str(output))
    def unavailable(*args, **kwargs):
        raise release_version.subprocess.CalledProcessError(1, 'gh')
    monkeypatch.setattr(release_version.subprocess, 'check_output', unavailable)
    with pytest.raises(release_version.subprocess.CalledProcessError):
        release_version.main()
    assert not output.exists()
