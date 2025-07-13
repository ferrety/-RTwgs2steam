# Wh4k: Rogue Trader savefile converter from GamePass to Steam

Script to convert Wh40k: Rogue trader Xbox Game Pass saves to Steam-compatible format

Make backups for GamePass and Steam save files before use!


## Requirements

- Python 3.8 or higher
- Wh40k Rogue Trader (both Xbox Game Pass and Steam versions)


## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Install requirements with uv
4. Run the script directly with Python or via bat file


## Limitations
Will not be able to convert all save files, use `--interactive` parameter to see which 
saves script thinks it can covert

## Usage

### Option 1: Run the the convert_saves.bat
Running convert_saves.bat will ask to to install uv if it's not available.
Will use --interactive mode, i.e., ists all save files.

### Option 2: Run the converter from shell
```bash
uv run python xbox_to_steam_save_converter.py
```

### Command Line Options

```bash
uv run python xbox_to_steam_save_converter.py -h
```


## File Paths

**Xbox Game Pass saves location:**
```
%USERPROFILE%\AppData\Local\Packages\OwlcatGames.3387926822CE4_197r75gc6ce9t\SystemAppData\wgs\
```

**Steam saves location:**
```
%USERPROFILE%\AppData\LocalLow\Owlcat Games\Warhammer 40000 Rogue Trader\Saved Games\
```

## Troubleshooting

- **Owlcat folder not found**: The script will search for any folder with "Owlcat" in the name if the exact path isn't found
- **No save folders found**: Make sure you have at least one save in Xbox Game Pass version
- **Extraction failed**: Ensure the save file isn't corrupted and try again
- **Steam directory creation**: The script will automatically create the Steam save directory if it doesn't exist

## Output

The converted save will be named `gamepass_save[containername].zks` and placed in your Steam save directory. 


