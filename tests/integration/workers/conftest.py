# Experiment for #2538, never to merge: the nested pytest sessions of these
# four files are left out, to measure whether the post-test tail of the CI step
# (18 to 41 min since #2531) goes with them.
collect_ignore = [
    "test_worker_exit_watchdog_2538.py",
    "test_worker_jvm_exit_2519.py",
    "test_worker_nested_session_jvm_2530.py",
    "test_worker_skip_storm_count_2490.py",
]
