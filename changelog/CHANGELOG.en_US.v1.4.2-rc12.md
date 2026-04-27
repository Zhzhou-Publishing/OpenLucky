# Changelog for v1.4.2-rc12

## Bug Fixes

- Fixed image resize occasionally being reported as failed when the output file existed but was momentarily inaccessible after the child process exited
- Disambiguated IPC events for the "select working directory" flow to avoid collisions with other working-directory preparation paths

## Improvements

- Streamlined post-resize success check by relying on the child process exit code instead of a redundant file existence probe
