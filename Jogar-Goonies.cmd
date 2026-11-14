@echo off
setlocal
set "DISK=%~dp0GOON-DAC.DSK"
if not exist "%DISK%" goto :missing_disk

if defined XROAR_EXE goto :check_emulator
set "XROAR_EXE=%~dp0xroar.exe"
if exist "%XROAR_EXE%" goto :check_emulator
set "XROAR_EXE=%USERPROFILE%\Downloads\xroar-1.12-w64\xroar.exe"
if exist "%XROAR_EXE%" goto :check_emulator
set "XROAR_EXE="
for %%I in (xroar.exe) do set "XROAR_EXE=%%~$PATH:I"

:check_emulator
if not defined XROAR_EXE goto :missing_emulator
if not exist "%XROAR_EXE%" goto :missing_emulator
for %%I in ("%XROAR_EXE%") do set "XROAR_DIR=%%~dpI."
start "" /b /wait "%XROAR_EXE%" -rompath "%XROAR_DIR%" -machine coco3 -ram 512 -tv-input rgb -load-fd0 "%DISK%" -no-disk-write-back -type "PCLEAR 1:RUN\"START\"\r"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :launch_error
exit /b 0

:missing_disk
echo GOON-DAC.DSK deve estar na mesma pasta que este arquivo.
goto :failure

:missing_emulator
echo XRoar nao encontrado. Defina XROAR_EXE com o caminho de xroar.exe.
goto :failure

:launch_error
echo Nao foi possivel iniciar o XRoar.

:failure
pause
exit /b 1


