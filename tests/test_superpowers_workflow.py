from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_guidance_installs_superpowers_tdd_gate():
	documents = {
		'AGENTS.md': (PROJECT_ROOT / 'AGENTS.md').read_text(),
		'README.md': (PROJECT_ROOT / 'README.md').read_text(),
		'docs/superpowers/README.md': (PROJECT_ROOT / 'docs' / 'superpowers' / 'README.md').read_text(),
	}
	required_terms = {
		'AGENTS.md': [
			'superpowers:using-superpowers',
			'superpowers:test-driven-development',
			'superpowers:verification-before-completion',
			'Red-Green-Refactor',
		],
		'README.md': [
			'Superpowers',
			'TDD',
			'superpowers:*',
		],
		'docs/superpowers/README.md': [
			'Red-Green-Refactor',
			'RED',
			'GREEN',
			'REFACTOR',
			'superpowers:verification-before-completion',
		],
	}

	missing_terms = [
		f'{path}: {term}'
		for path, terms in required_terms.items()
		for term in terms
		if term not in documents[path]
	]

	assert missing_terms == []


def test_test_suite_has_no_historical_execution_patterns():
	test_roots = [PROJECT_ROOT / 'tests', PROJECT_ROOT / 'web' / 'tests']
	test_files = sorted(
		path
		for root in test_roots
		for pattern in ('test_*.py', '*.spec.ts')
		for path in root.rglob(pattern)
		if path.name != 'test_superpowers_workflow.py' and path.name != 'test_repository_hygiene.py'
	)
	forbidden_content = [
		'ENABLE_REAL_TEST',
		'tmp-artifacts',
		'test-results',
		'web/test-results',
	]
	forbidden_file_prefixes = ('aa-', 'zz-')

	violations = []
	for path in test_files:
		relative_path = path.relative_to(PROJECT_ROOT).as_posix()
		if path.name.startswith(forbidden_file_prefixes):
			violations.append(f'{relative_path}: ordered filename prefix')
		content = path.read_text()
		violations.extend(
			f'{relative_path}: {forbidden}'
			for forbidden in forbidden_content
			if forbidden in content
		)

	assert violations == []
