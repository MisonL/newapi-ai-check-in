import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_ignored(paths: list[str]) -> set[str]:
	if not paths:
		return set()
	result = subprocess.run(
		['git', 'check-ignore', '--stdin'],
		input='\n'.join(paths),
		text=True,
		cwd=PROJECT_ROOT,
		capture_output=True,
		check=False,
	)
	return set(result.stdout.splitlines())


def test_historical_review_records_are_not_kept_in_repository_tree():
	legacy_paths = [
		PROJECT_ROOT / 'docs' / 'reviews',
		PROJECT_ROOT / 'tmp-artifacts',
		PROJECT_ROOT / 'web' / 'test-results',
	]

	existing_files = sorted(
		file.relative_to(PROJECT_ROOT).as_posix()
		for path in legacy_paths
		if path.exists()
		for file in path.rglob('*')
		if file.is_file()
	)
	unignored_files = sorted(set(existing_files) - _git_ignored(existing_files))

	assert unignored_files == []


def test_completed_superpowers_plan_records_are_not_kept_as_history():
	historical_records = sorted(
		path.relative_to(PROJECT_ROOT).as_posix()
		for directory in [
			PROJECT_ROOT / 'docs' / 'superpowers' / 'plans',
			PROJECT_ROOT / 'docs' / 'superpowers' / 'specs',
		]
		for path in directory.glob('20*.md')
	)

	assert historical_records == []


def test_generated_artifact_locations_are_ignored_by_git():
	ignored_paths = [
		'docs/reviews/CR-LOCAL.md',
		'docs/reviews/artifacts/screenshot.png',
		'tmp-artifacts/output.txt',
		'test-results/output.txt',
		'web/test-results/.last-run.json',
		'.pytest_cache/v/cache/nodeids',
		'.ruff_cache/CACHEDIR.TAG',
		'runtime_data/control_plane.db',
	]

	assert _git_ignored(ignored_paths) == set(ignored_paths)


def test_generated_artifact_locations_are_excluded_from_docker_context():
	dockerignore_patterns = {
		line.strip().rstrip('/')
		for line in (PROJECT_ROOT / '.dockerignore').read_text().splitlines()
		if line.strip() and not line.strip().startswith('#')
	}
	excluded_paths = [
		'docs/reviews',
		'tmp-artifacts',
		'test-results',
		'web/test-results',
		'.pytest_cache',
		'.ruff_cache',
		'runtime_data',
	]

	missing_paths = [path for path in excluded_paths if path not in dockerignore_patterns]

	assert missing_paths == []
