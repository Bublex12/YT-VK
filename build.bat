@echo off
echo Cleaning previous build...
rmdir /s /q build
rmdir /s /q dist

echo Building executable...
pyinstaller --clean youtube_downloader.spec

echo Done!
pause 