@echo off
@rem Compile Super Dynamite scripts and copy INT files to data\scripts\
@rem Run this from the CUSTOM folder.
@rem Requires the sfall script compiler or a configured P.BAT preprocessor.

set OUT=..\..\..\Fallout 2\data\scripts

@rem DYNMK2 (Super Dynamite - inactive)
copy DYNMK2.SSL temp.ssl
..\..\compile.exe temp.ssl
if %errorlevel% neq 0 goto ERROR
copy temp.int %OUT%\DYNMK2.int
del temp.ssl temp.int
echo Compiled DYNMK2.int OK

@rem DYNMK2ON (Super Active Dynamite - timed)
copy DYNMK2ON.SSL temp.ssl
..\..\compile.exe temp.ssl
if %errorlevel% neq 0 goto ERROR
copy temp.int %OUT%\DYNMK2ON.int
del temp.ssl temp.int
echo Compiled DYNMK2ON.int OK

echo Done.
goto END

:ERROR
echo Compile failed. Check for syntax errors.

:END
