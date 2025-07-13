#!/usr/bin/env python3
"""
Xbox Game Pass to Steam Save Converter for Warhammer 40000 Rogue Trader

This script converts Xbox Game Pass saves to Steam-compatible format by:
1. Locating Xbox saves in the WGS folder
2. Finding the latest save folder
3. Extracting and processing save files
4. Converting to Steam format (.zks)
5. Copying to Steam save directory
"""

import argparse
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Define save paths as strings with forward slashes for cross-platform compatibility
STEAM_SAVE_PATH = r'AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader/Saved Games'

WGS_FOLDER_PATH = r'AppData/Local/Packages/OwlcatGames.3387926822CE4_197r75gc6ce9t/SystemAppData/wgs'


class XboxToSteamConverter:
    """Handles conversion of Xbox Game Pass saves to Steam format."""

    def __init__(self, steam_save_path: Optional[str] = None):
        self.user_profile = os.environ.get('USERPROFILE', '')
        self.wgs_path = Path(self.user_profile) / WGS_FOLDER_PATH
        if steam_save_path:
            self.steam_save_path = Path(steam_save_path)
        else:
            self.steam_save_path = Path(self.user_profile) / STEAM_SAVE_PATH

    # Removed find_owlcat_folder, now using fixed wgs_path
                
    def find_latest_save_folder(self) -> Optional[Path]:
        """Find the latest save folder in the fixed WGS directory."""
        if not self.wgs_path.exists():
            print(f"Error: WGS directory not found at {self.wgs_path}")
            return None

        print(f"Searching for save folders in: {self.wgs_path}")

        save_folders = [f for f in self.wgs_path.iterdir()
                        if f.is_dir() and len(f.name) > 20 and '_' in f.name]

        if not save_folders:
            print("Error: No save folders found")
            return None

        save_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_folder = save_folders[0]

        print(f"Found {len(save_folders)} save folder(s)")
        print(f"Latest save folder: {latest_folder.name}")
        print(f"Modified: {datetime.fromtimestamp(latest_folder.stat().st_mtime)}")

        return latest_folder
        
    def find_latest_container_folder(self, save_folder: Path) -> Optional[Path]:
        """Find the latest container folder within the save folder."""
        print(f"Looking for container folders in: {save_folder}")
        
        # Find container folders (exclude the container file)
        container_folders = [f for f in save_folder.iterdir() 
                           if f.is_dir() and len(f.name) == 32]  # Container folders are 32 hex chars
        
        if not container_folders:
            print("Error: No container folders found")
            return None
            
        # Sort by modification time and get the latest
        container_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_container = container_folders[0]
        
        print(f"Found {len(container_folders)} container folder(s)")
        print(f"Latest container: {latest_container.name}")
        print(f"Modified: {datetime.fromtimestamp(latest_container.stat().st_mtime)}")
        
        return latest_container
        
    def analyze_save_files(self, container_folder: Path) -> Tuple[Path, Path, Path, Path]:
        """Analyze files in container folder and identify each type by size."""
        files = [f for f in container_folder.iterdir() if f.is_file()]

        if len(files) < 4:
            raise ValueError(f"Expected at least 4 files, found {len(files)}")

        # Sort files by size (largest first)
        files.sort(key=lambda x: x.stat().st_size, reverse=True)

        print("Files found (sorted by size):")
        for i, file in enumerate(files):
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"{i+1}. {file.name} ({size_mb:.2f} MB)")

        save_file = files[0]  # Largest - actual save data
        highres_image = files[1]  # Second largest - high res screenshot
        lowres_image = files[2]  # Third largest - low res screenshot  
        header_file = files[3]  # Smallest - header file

        return save_file, highres_image, lowres_image, header_file
        
    def extract_save_data(self, save_file: Path, temp_dir: Path) -> Path:
        """Extract the main save file (which is a zip archive)."""
        extract_dir = temp_dir / 'extracted_save'
        extract_dir.mkdir(exist_ok=True)
        
        print(f"Extracting save data from: {save_file.name}")
        
        try:
            with zipfile.ZipFile(save_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                print(f"Extracted {len(zip_ref.namelist())} files")
        except zipfile.BadZipFile:
            raise ValueError(f"Failed to extract {save_file.name} - not a valid zip file")
            
        return extract_dir
        
    def copy_and_rename_files(self, highres_image: Path, lowres_image: Path, 
                            header_file: Path, extract_dir: Path):
        """Copy and rename the supporting files to the extracted directory."""
        print("Copying and renaming supporting files...")
        
        # Copy and rename files
        shutil.copy2(highres_image, extract_dir / 'highres.png')
        shutil.copy2(lowres_image, extract_dir / 'header.png')
        shutil.copy2(header_file, extract_dir / 'header.json')
        
        print("Files renamed:")
        print(f"  {highres_image.name} -> highres.png")
        print(f"  {lowres_image.name} -> header.png")
        print(f"  {header_file.name} -> header.json")

    def fix_dlc_issues(self, extract_dir: Path):
        """Fix DLC issues by clearing DLC-related fields in player.json and header.json."""
        print("Fixing DLC issues...")

        # Fix header.json
        header_json_path = extract_dir / "header.json"
        if header_json_path.exists():
            try:
                with open(header_json_path, "r", encoding="utf-8") as f:
                    header_data = json.load(f)

                if "m_DlcRewards" in header_data:
                    header_data["m_DlcRewards"] = []
                    print("  Cleared m_DlcRewards in header.json")

                with open(header_json_path, "w", encoding="utf-8") as f:
                    json.dump(header_data, f, indent=2)

            except (json.JSONDecodeError, Exception) as e:
                print(f"  Warning: Could not fix header.json: {e}")

        # Fix player.json
        player_json_path = extract_dir / "player.json"
        if player_json_path.exists():
            try:
                with open(player_json_path, "r", encoding="utf-8") as f:
                    player_data = json.load(f)

                dlc_fields_fixed = []
                if "m_StartNewGameAdditionalContentDlcStatus" in player_data:
                    player_data["m_StartNewGameAdditionalContentDlcStatus"] = []
                    dlc_fields_fixed.append("m_StartNewGameAdditionalContentDlcStatus")

                if "UsedDlcRewards" in player_data:
                    player_data["UsedDlcRewards"] = []
                    dlc_fields_fixed.append("UsedDlcRewards")

                if "ClaimedDlcRewards" in player_data:
                    player_data["ClaimedDlcRewards"] = []
                    dlc_fields_fixed.append("ClaimedDlcRewards")

                if dlc_fields_fixed:
                    print(f"  Cleared {', '.join(dlc_fields_fixed)} in player.json")

                with open(player_json_path, "w", encoding="utf-8") as f:
                    json.dump(player_data, f, indent=2)

            except (json.JSONDecodeError, Exception) as e:
                print(f"  Warning: Could not fix player.json: {e}")

        if not header_json_path.exists() and not player_json_path.exists():
            print("  No JSON files found to fix")

    def create_steam_save(
        self,
        extract_dir: Path,
        output_path: Path,
        highres_image: Path,
        lowres_image: Path,
        header_file: Path,
        fix_dlc: bool = False,
    ) -> Path:
        """Create the Steam-compatible .zks file."""
        # First copy and rename the supporting files to extract_dir
        self.copy_and_rename_files(highres_image, lowres_image, header_file, extract_dir)

        # Fix DLC issues if requested
        if fix_dlc:
            self.fix_dlc_issues(extract_dir)

        zks_file = output_path / 'gamepass_save.zks'
        
        print(f"Creating Steam save file: {zks_file}")
        
        with zipfile.ZipFile(zks_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in extract_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(extract_dir)
                    zip_ref.write(file_path, arcname)
                    
        size_mb = zks_file.stat().st_size / (1024 * 1024)
        print(f"Created {zks_file.name} ({size_mb:.2f} MB)")
        
        return zks_file
        
    def copy_to_steam_directory(self, zks_file: Path) -> bool:
        """Copy the converted save to Steam directory."""
        print(f"Copying to Steam directory: {self.steam_save_path}")
        
        # Create Steam save directory if it doesn't exist
        self.steam_save_path.mkdir(parents=True, exist_ok=True)
        
        destination = self.steam_save_path / zks_file.name
        
        try:
            shutil.copy2(zks_file, destination)
            print(f"Successfully copied to: {destination}")
            return True
        except Exception as e:
            print(f"Error copying to Steam directory: {e}")
            return False

    def convert_save(self, dryrun: bool = False, fix_dlc: bool = False) -> bool:
        """Main conversion process."""
        print("=== Xbox Game Pass to Steam Save Converter ===")
        print("For Warhammer 40000 Rogue Trader\n")

        try:
            save_folder = self.find_latest_save_folder()
            if not save_folder:
                return False

            container_folder = self.find_latest_container_folder(save_folder)
            if not container_folder:
                return False

            save_file, highres_image, lowres_image, header_file = self.analyze_save_files(container_folder)

            if dryrun:
                temp_path = Path(r"c:/temp/RTWGS")
                temp_path.mkdir(parents=True, exist_ok=True)
                extract_dir = self.extract_save_data(save_file, temp_path)
                zks_file = self.create_steam_save(
                    extract_dir,
                    temp_path,
                    highres_image,
                    lowres_image,
                    header_file,
                    fix_dlc,
                )
                print(f"\nDry run: Converted save file {zks_file}")
                print("No files were copied to the Steam save directory.")
                return True
            else:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    extract_dir = self.extract_save_data(save_file, temp_path)
                    zks_file = self.create_steam_save(
                        extract_dir,
                        temp_path,
                        highres_image,
                        lowres_image,
                        header_file,
                        fix_dlc,
                    )
                    success = self.copy_to_steam_directory(zks_file)
                    if success:
                        print("\n✅ Conversion completed successfully!")
                        print("You can now load the save in Steam version of the game.")
                        return True
                    else:
                        print("\n❌ Conversion failed during final copy.")
                        return False
        except Exception as e:
            print(f"\n❌ Error during conversion: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Xbox Game Pass to Steam Save Converter")
    parser.add_argument(
        "--steam-save-path", "-s",
        type=str,
        default=None,
        help="Custom Steam save path. Default is the standard Steam save location."
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Leave the converted save file in the temp directory and do not copy to Steam folder.",
    )
    parser.add_argument(
        "--fix-dlc",
        action="store_true",
        help="Remove DLC references from the save files.",
    )
    args = parser.parse_args()

    converter = XboxToSteamConverter(steam_save_path=args.steam_save_path)

    try:
        success = converter.convert_save(dryrun=args.dryrun, fix_dlc=args.fix_dlc)
        if not success:
            print("\nConversion failed. Please check the error messages above.")
            input("Press Enter to exit...")
            return 1

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        input("Press Enter to exit...")
        return 1

    input("\nPress Enter to exit...")
    return 0


if __name__ == "__main__":
    exit(main())
