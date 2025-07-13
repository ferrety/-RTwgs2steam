# Wh4k: Rogue Trader savefile converter from GamePass to Steam

Script to convert Wh40k: Rogue trader Xbox Game Pass saves to Steam-compatible format

Converted saves will be named `gamepass_save_[containername].zks` and placed in Steam save directory. 

Make backups for GamePass and Steam save files before use!

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Run the script using bat file or  uv/Python

## Usage

### Option 1: Run the convert_saves.bat
Running convert_saves.bat will ask to install uv if it's not available.
Will use --interactive mode

### Option 2: Run the converter from shell
```bash
uv run python RTwgs2steam.py
```

## Limitations
Will not be able to convert all save files
Interactive mode (use paramter -i) shows files that script thinks it can convert


## File Paths
Are hardcoded to python file

**Xbox Game Pass saves location:**
```
%USERPROFILE%\AppData\Local\Packages\OwlcatGames.3387926822CE4_197r75gc6ce9t\SystemAppData\wgs\
```

**Steam saves location:**
```
%USERPROFILE%\AppData\LocalLow\Owlcat Games\Warhammer 40000 Rogue Trader\Saved Games\
```

## Troubleshooting

- **No save folders found**: Make sure you have at least one save in Xbox Game Pass version
- **Steam directory creation**: The script will try to automatically create the Steam save directory if it doesn't exist
- **Windows Protected you PC**: Click `More Info` -> `Run anyway`

## Help
```bash
uv run python RTwgs2steam.py --help
```

