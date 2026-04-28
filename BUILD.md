# Build

## Windows

### build cli

```cmd
python -m PyInstaller --onefile --name openlucky --distpath ./bin cli/openlucky.py
```

### build desktop app

```cmd
cd app/
yarn build:win:portable
```

### build installer package

```cmd
ISCC.exe OpenLucky.iss
```

## macOS

### build macOS cli

#### Standard build (slow startup)

```zsh
python3 -m PyInstaller --onefile --name openlucky --distpath bin cli/openlucky.py
```

#### Optimized build (recommended - fast startup)

```zsh
python3 -m PyInstaller --onedir --name openlucky \
--contents-directory cli/lib \
--distpath bin cli/openlucky.py
```

### Build macOS desktop app and installer

#### Step 1: Build the CLI tool

Make sure to run this command from the **project root directory** before building the desktop app:

```cmd
python3 -m PyInstaller --onedir --name openlucky \
--contents-directory cli/lib \
--distpath bin cli/openlucky.py
```

#### Step 2: Build the Electron app

```cmd
cd app/
yarn build:mac
```

The built DMG file will be in `app/dist-electron/` directory.

**Note:** The Electron app automatically includes the CLI tool files from `bin/openlucky/` during the build process. The CLI tool is packaged in the app's Resources folder and the app is configured to use it both in development and production.
