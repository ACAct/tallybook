#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 app.py
result=$?
if [ "$result" -ne 0 ]; then
  printf '\n启动未完成，请检查上方提示。按回车关闭。'
  read -r answer
fi
exit "$result"
