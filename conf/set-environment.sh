export PYTHONPATH="$PYTHONPATH:$(pdm info --packages)/lib"
export PATH="$PATH:$(pdm info --packages)/bin:$HOME/.garden/bin"
