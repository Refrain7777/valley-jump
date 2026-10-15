@echo off
chcp 65001 >nul
cd /d D:\Py_Cursor

echo 正在安装网页打包工具 pygbag ...
python -m pip install pygbag -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if errorlevel 1 (
  echo 安装失败，请关掉代理后再试一次。
  pause
  exit /b 1
)

echo.
echo 开始打包并启动网页。请用浏览器打开稍后出现的地址。
echo 手机请先和电脑连同一个 WiFi，然后访问 电脑IP:8000
echo 按 Ctrl+C 可停止。
echo.
python -m pygbag --width 960 --height 540 --ume_block 0 --bind 0.0.0.0 D:\Py_Cursor
pause
