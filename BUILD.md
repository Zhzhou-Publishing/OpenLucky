## Windows

## build cli
```bash
python -m PyInstaller --onefile --name openlucky --distpath bin cmd/openlucky.py
```

## build desktop app
```bash
cd app/
yarn build:win:portable
```

## build installer package
```
ISCC.exe OpenLucky.iss
```
