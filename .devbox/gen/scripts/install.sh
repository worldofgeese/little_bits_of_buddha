set -e

if [ -z "$__DEVBOX_SKIP_INIT_HOOK_5662063ccc92166df8b66aa311c32f9a1e6bed9489e336c9f39ff490aeb0535c" ]; then
    . "/home/node/.openclaw/workspace/projects/little_bits_of_buddha/.devbox/gen/scripts/.hooks.sh"
fi

pdm install
