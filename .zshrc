
# fnm
FNM_PATH="/Users/markkiehlmann/Library/Application Support/fnm"
if [ -d "$FNM_PATH" ]; then
  export PATH="/Users/markkiehlmann/Library/Application Support/fnm:$PATH"
  eval "`fnm env`"
fi
alias python=python3
export PATH="$PATH:/Users/markkiehlmann/Library/Python/3.11/bin"
export APP_ENV=dev

