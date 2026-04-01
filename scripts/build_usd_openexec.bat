@echo off
REM Sprint 2 Phase 0: Build USD 26.03 with OpenExec on Windows
REM Headless build: no imaging, no usdview, no ptex, no embree

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64

echo === MSVC Environment Initialized ===
where cl.exe
cl.exe 2>&1 | findstr "Version"

echo === Starting USD Build ===
py -3.12 C:\Users\User\OpenUSD-26.03\build_scripts\build_usd.py ^
    --no-imaging ^
    --no-usdview ^
    --no-ptex ^
    --no-embree ^
    --no-tests ^
    --no-examples ^
    --no-tutorials ^
    --no-docs ^
    C:\USD\26.03

echo === Build Complete (exit code: %ERRORLEVEL%) ===
