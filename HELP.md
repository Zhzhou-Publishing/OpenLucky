## Windows Debugging

Problem:

> Traceback (most recent call last):
>  File "D:\openlucky\cmd\openlucky.py", line 5, in <module>
> ModuleNotFoundError: No module named 'lib'

Resolution: 

```powershell
$env:PYTHONPATH = $PWD
python .\cmd\openlucky.py help
```
