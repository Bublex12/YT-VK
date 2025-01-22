@echo off
echo Creating required directories...
mkdir config
mkdir downloads

echo Copying configuration files...
copy .env config\.env

echo Setup complete!
pause 