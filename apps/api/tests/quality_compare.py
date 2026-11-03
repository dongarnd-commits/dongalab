"""Compare frozen synthetic gold against exact commit bytes or this worktree.

The five variable pure modules are compiled in memory. Historical checkout,
product/source mutation, DB, external AI and OCR execution are not performed.
Each invocation writes a NEW output file; existing evidence is never replaced.
"""
from hashlib import sha256
from pathlib import Path
import argparse
import importlib
import json
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
MODULES = (
    'app.company.improvement_language',
    'app.company.improvement_structure',
    'app.capability.recommendations',
    'app.capability.asset_solutions',
    'app.company.improvement_rules',
)
PURE_SUPPORT = ('apps/api/app/capability/search.py',
                'apps/api/app/notice/domain.py',
                'apps/api/app/company/documents.py',
                'apps/api/tests/test_asset_solutions.py')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def normalize_lines(raw):
    return raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def byte_record(raw):
    crlf = raw.count(b'\r\n')
    lone_lf = raw.count(b'\n') - crlf
    lone_cr = raw.count(b'\r') - crlf
    style = 'MIXED' if sum(bool(n) for n in (crlf, lone_lf, lone_cr)) > 1 else 'CRLF' if crlf else 'LF' if lone_lf else 'CR' if lone_cr else 'NONE'
    return dict(sha256=sha256(raw).hexdigest(), bytes=len(raw), line_endings=style,
                crlf=crlf, lone_lf=lone_lf, lone_cr=lone_cr,
                lf_normalized_sha256=sha256(normalize_lines(raw)).hexdigest())


def module_path(name):
    return 'apps/api/' + name.replace('.', '/') + '.py'


def evaluate_selected(code, corpus):
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(ROOT / 'apps/api'), str(ROOT / 'apps/api/tests')]
    worktree_head = git('rev-parse', 'HEAD').decode().strip()
    commit = None if code == 'worktree' else git('rev-parse', '--verify', code + '^{commit}').decode().strip()
    frozen_path = Path(corpus).resolve()
    frozen = json.loads(frozen_path.read_text(encoding='utf-8'))
    selected_bytes = {}

    def selected(path):
        if path not in selected_bytes:
            selected_bytes[path] = git('show', commit + ':' + path) if commit else (ROOT / path).read_bytes()
        return selected_bytes[path]

    # These imports remain in the current interpreter. Refuse a historical run
    # when their meaning differs; line ending differences alone are explicit.
    for path in PURE_SUPPORT:
        if normalize_lines(selected(path)) != normalize_lines((ROOT / path).read_bytes()):
            raise ValueError('SUPPORT_SOURCE_DIFFERS_FROM_SELECTED_COMMIT: ' + path)

    for name in MODULES:
        parent, key = name.rsplit('.', 1)
        package = importlib.import_module(parent)
        path = module_path(name)
        module = types.ModuleType(name)
        module.__file__ = ('git:' + commit + '/' if commit else str(ROOT) + '/') + path
        module.__package__ = parent
        sys.modules[name] = module
        setattr(package, key, module)
        # bytes from git show are compiled without newline rewriting.
        exec(compile(selected(path), module.__file__, 'exec'), module.__dict__)

    evaluator = importlib.import_module('quality_evaluator')
    result = evaluator.evaluate(frozen_path)
    variable_paths = {module_path(name) for name in MODULES}
    source_paths = sorted(set(evaluator.SOURCE_FILES) | set(PURE_SUPPORT))
    sources = {}
    for path in source_paths:
        chosen, runtime = selected(path), (ROOT / path).read_bytes()
        is_variable = path in variable_paths
        sources[path] = dict(selected=byte_record(chosen), worktree=byte_record(runtime),
            execution='EXACT_SELECTED_BYTES_COMPILED_IN_MEMORY' if is_variable else
                      'WORKTREE_PURE_SUPPORT_IMPORT' if path in PURE_SUPPORT else 'VERSION_REFERENCE_NOT_EXECUTED',
            support_lf_equivalent=normalize_lines(chosen) == normalize_lines(runtime) if path in PURE_SUPPORT else None)

    for case, row in zip(frozen['cases'], result['results'], strict=True):
        if case['id'] != row['id']:
            raise ValueError('CORPUS_RESULT_ORDER_MISMATCH')
        if 'support_status' in case:
            row['support_status'] = case['support_status']
            row['support_limit'] = case.get('support_limit', '')
    result['schema'] = 'analysis-quality-comparison-v2'
    result['scope'] = frozen.get('evaluation_status', 'SYNTHETIC_FINITE_REGRESSION')
    result['code_head'] = commit or worktree_head
    result['code_selection'] = dict(requested=code, kind='COMMIT' if commit else 'WORKTREE',
        selected_commit=commit, worktree_head=worktree_head,
        worktree_dirty=bool(git('status', '--porcelain', '--untracked-files=no').strip()),
        variable_modules=list(MODULES),
        execution='Five pure modules compiled from exact git-show bytes or exact worktree bytes; support imports verified separately.')
    # source_sha256 describes the SELECTED source, rather than accidentally
    # reporting the working tree when a historical implementation was executed.
    result['source_sha256'] = {path:row['selected']['sha256'] for path,row in sources.items()}
    result['source_loading'] = sources
    result['evaluation_harness'] = {path:byte_record((ROOT/path).read_bytes()) for path in
        ('apps/api/tests/quality_compare.py', 'apps/api/tests/quality_evaluator.py', 'apps/api/tests/test_asset_solutions.py')}
    result['gold_sha256'] = sha256(json.dumps([dict(id=c['id'],kind=c['kind'],gold=c['gold']) for c in frozen['cases']],
        ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    result['case_ids'] = [c['id'] for c in frozen['cases']]
    result['corpus_metadata'] = {key:value for key,value in frozen.items() if key != 'cases'}
    unsupported = [r for r in result['results'] if r.get('support_status','').startswith('UNSUPPORTED_')]
    result['summary']['declared_unsupported_grammar_cases'] = len(unsupported)
    result['summary']['declared_unsupported_grammar_failed'] = sum(not r['passed'] for r in unsupported)
    result['summary']['assertions'] = sum(len(r['checks']) for r in result['results'])
    result['summary']['failed_assertions'] = sum(not c['passed'] for r in result['results'] for c in r['checks'])
    result['report_errors'] = [dict(id=r['id'],error=r['processing_failure']) for r in result['results'] if 'processing_failure' in r]
    result['limitations'] += [
        'Round2 cases have already been exposed. This is regression evidence, not an unseen holdout.',
        'Changes to gold and changes to product code must be compared separately. Original raw gold and first-evaluation JSON are retained.',
        'Free-text scalar grammar limitations remain failures in the same 24-case denominator.',
        'Exact commit bytes and current support-import bytes may differ in line endings; source_loading records both and verifies LF-equivalent pure support.',
        'Generic parser rejection of an unsupported or damaged input is not successful extraction; OCR versions are references and OCR was not executed.',
    ]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', required=True, help='Git commit/ref or literal worktree')
    parser.add_argument('--corpus', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('OUTPUT_ALREADY_EXISTS: refusing to replace preserved evaluation evidence')
    result = evaluate_selected(args.code, args.corpus)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(result,ensure_ascii=False,indent=2) + '\n')
    print(json.dumps(dict(code=result['code_selection'], summary=result['summary'],
        failed_case_ids=[r['id'] for r in result['results'] if not r['passed']],
        corpus_sha256=result['corpus_sha256'],gold_sha256=result['gold_sha256'],
        output=str(args.output)),ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
