@ECHO OFF
SET CURRENTDIR=%CD%
CD "your\path\to\dev_scripts_py"
python ds.py "%CURRENTDIR%" %*
CD "%CURRENTDIR%"
