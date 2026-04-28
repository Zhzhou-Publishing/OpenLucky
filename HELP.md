## Windows Debugging

Problem:

> Traceback (most recent call last):
>  File "D:\openlucky\cli\openlucky.py", line 5, in <module>
> ModuleNotFoundError: No module named 'cli'

Resolution: 

```powershell
$env:PYTHONPATH = $PWD
python .\cli\openlucky.py help
```

## Electron Build Symbol Link Problem

Windows Setting >> Security >> Developer Mode
