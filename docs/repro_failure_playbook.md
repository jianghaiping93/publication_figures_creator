# Reproducibility Failure Playbook

## Common Failure Buckets
- `missing_python_module`: Install missing Python packages listed in logs.
- `missing_r_package`: Install missing R packages with `install.packages()`.
- `missing_matlab_function`: Add required toolbox or function path.
- `missing_data`: Download input datasets referenced by README or script.
- `path_error`: Fix relative paths or set the working directory.
- `timeout`: Increase timeout or reduce dataset size.

## Fix Workflow
1. Run `scripts/build_failure_fix_queue.py` to generate `data/metadata/repro_fix_queue.csv`.
2. Batch-install dependencies by language, then re-run `scripts/run_reproducibility_regression.sh`.
3. For missing data, download to the path expected by the script or update config paths.

## Notes
- Always log fixes in `PROJECT_TRACKER.md` under “重复问题与解决方案”.
- Prefer adding small wrapper scripts rather than editing upstream repos.
