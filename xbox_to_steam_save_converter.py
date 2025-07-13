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

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table


class ContainerInfo(NamedTuple):
    """Information about a save container."""

    save_folder: Path
    container_folder: Path
    created_date: datetime
    file_count: int
    save_name: Optional[str]


# Define save paths as strings with forward slashes for cross-platform compatibility
STEAM_SAVE_PATH = (
    r"AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader/Saved Games"
)
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
        self.console = Console()

    def discover_all_containers(self) -> List[ContainerInfo]:
        """Discover all save containers in the WGS directory."""
        if not self.wgs_path.exists():
            raise FileNotFoundError(f"WGS directory not found at {self.wgs_path}")

        containers = []

        # Find all save folders
        save_folders = [
            f
            for f in self.wgs_path.iterdir()
            if f.is_dir() and len(f.name) > 20 and "_" in f.name
        ]

        for save_folder in save_folders:
            # Find container folders within each save folder
            container_folders = [
                f for f in save_folder.iterdir() if f.is_dir() and len(f.name) == 32
            ]  # 32 hex chars

            for container_folder in container_folders:
                # Count files in container
                files = [f for f in container_folder.iterdir() if f.is_file()]

                # Skip empty containers
                if len(files) < 5:
                    continue

                # Get creation time
                created_date = datetime.fromtimestamp(container_folder.stat().st_ctime)

                # Extract save name from header file
                save_name = self.extract_save_name_from_header(container_folder)

                containers.append(
                    ContainerInfo(
                        save_folder=save_folder,
                        container_folder=container_folder,
                        created_date=created_date,
                        file_count=len(files),
                        save_name=save_name,
                    )
                )

        # Sort by creation date (newest first)
        containers.sort(key=lambda x: x.created_date, reverse=True)
        return containers

    def display_containers_table(self, containers: List[ContainerInfo]) -> None:
        """Display containers in a formatted table."""
        table = Table(title="Available Save Containers")
        table.add_column("Index", justify="right", style="cyan", no_wrap=True)
        table.add_column("Save Name", style="bright_green")
        table.add_column("Created", style="blue")

        namelen = (
            min(
                max(len(container.save_name) for container in containers)
                if containers
                else 10,
                60,
            )
            + 1
        )

        for i, container in enumerate(containers, 1):
            # Display save name or fallback to "Unknown"
            save_name = (
                container.save_name if container.save_name else "[dim]Unknown[/dim]"
            )

            table.add_row(
                str(i),
                save_name[:namelen] + "..."
                if container.save_name and len(container.save_name) > 40
                else save_name,
                container.created_date.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)

    def parse_selection_input(self, input_str: str, max_count: int) -> List[int]:
        """Parse user selection input and return list of indices."""
        input_str = input_str.strip().lower()

        if input_str == "all":
            return list(range(1, max_count + 1))

        selections: List[int] = []
        parts = input_str.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # Handle ranges like "3-7"
                try:
                    start, end = map(int, part.split("-"))
                    selections.extend(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"Invalid range format: {part}")
            else:
                # Handle single numbers
                try:
                    selections.append(int(part))
                except ValueError:
                    raise ValueError(f"Invalid number: {part}")

        # Validate indices
        for idx in selections:
            if idx < 1 or idx > max_count:
                raise ValueError(f"Index {idx} out of range (1-{max_count})")

        return sorted(list(set(selections)))  # Remove duplicates and sort

    def select_containers_interactive(
        self, containers: List[ContainerInfo]
    ) -> List[ContainerInfo]:
        """Allow user to select containers interactively."""
        if not containers:
            self.console.print("[red]No containers found![/red]")
            return []

        self.display_containers_table(containers)

        self.console.print("\n[bold]Selection options:[/bold]")
        self.console.print("• Single: [cyan]1[/cyan]")
        self.console.print("• Multiple: [cyan]1,3,5[/cyan]")
        self.console.print("• Range: [cyan]3-7[/cyan]")
        self.console.print("• All: [cyan]all[/cyan]")
        self.console.print("• Quit: [cyan]q[/cyan] or [cyan]quit[/cyan]")

        while True:
            try:
                selection = Prompt.ask("\nSelect containers", default="1")

                # Check for quit option
                if selection.strip().lower() in ("q", "quit"):
                    self.console.print("[yellow]Selection cancelled[/yellow]")
                    return []

                indices = self.parse_selection_input(selection, len(containers))
                selected_containers = [containers[i - 1] for i in indices]

                self.console.print(
                    f"\n[green]Selected {len(selected_containers)} container(s)[/green]"
                )
                return selected_containers

            except ValueError as e:
                self.console.print(f"[red]Error: {e}[/red]")
                self.console.print("Please try again.")

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

    def convert_multiple_saves(
        self,
        containers: List[ContainerInfo],
        dryrun: bool = False,
        fix_dlc: bool = False,
    ) -> bool:
        """Convert multiple container saves to Steam format."""
        success_count = 0

        for i, container in enumerate(containers, 1):
            self.console.print(
                f"\n[bold cyan]Processing container {i}/{len(containers)}[/bold cyan]"
            )
            self.console.print(f"Save folder: {container.save_folder.name}")
            self.console.print(f"Container: {container.container_folder.name}")

            try:
                save_file, highres_image, lowres_image, header_file = (
                    self.analyze_save_files(container.container_folder)
                )

                if dryrun:
                    temp_path = Path(r"c:/temp/RTWGS")
                    temp_path.mkdir(parents=True, exist_ok=True)
                    extract_dir = self.extract_save_data(save_file, temp_path)

                    # Use container name in output filename
                    output_name = (
                        f"gamepass_save_{container.container_folder.name[:8]}.zks"
                    )
                    zks_file = self.create_steam_save_with_name(
                        extract_dir,
                        temp_path,
                        highres_image,
                        lowres_image,
                        header_file,
                        output_name,
                        fix_dlc,
                    )
                    self.console.print(f"[green]✓ Converted: {zks_file}[/green]")
                    success_count += 1
                else:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        extract_dir = self.extract_save_data(save_file, temp_path)

                        # Use container name in output filename
                        output_name = (
                            f"gamepass_save_{container.container_folder.name[:8]}.zks"
                        )
                        zks_file = self.create_steam_save_with_name(
                            extract_dir,
                            temp_path,
                            highres_image,
                            lowres_image,
                            header_file,
                            output_name,
                            fix_dlc,
                        )

                        if self.copy_to_steam_directory(zks_file):
                            self.console.print(
                                f"[green]✓ Converted and copied: {output_name}[/green]"
                            )
                            success_count += 1
                        else:
                            self.console.print(
                                f"[red]✗ Failed to copy: {output_name}[/red]"
                            )

            except Exception as e:
                self.console.print(f"[red]✗ Error processing container: {e}[/red]")

        if success_count == len(containers):
            self.console.print(
                f"\n[green]✅ All {success_count} containers converted successfully![/green]"
            )
            return True
        elif success_count > 0:
            self.console.print(
                f"\n[yellow]⚠ {success_count}/{len(containers)} containers converted[/yellow]"
            )
            return True
        else:
            self.console.print(
                "\n[red]❌ No containers were converted successfully[/red]"
            )
            return False

    def create_steam_save_with_name(
        self,
        extract_dir: Path,
        output_path: Path,
        highres_image: Path,
        lowres_image: Path,
        header_file: Path,
        output_name: str,
        fix_dlc: bool = False,
    ) -> Path:
        """Create Steam-compatible .zks file with custom name."""
        # First copy and rename the supporting files to extract_dir
        self.copy_and_rename_files(
            highres_image, lowres_image, header_file, extract_dir
        )

        # Fix DLC issues if requested
        if fix_dlc:
            self.fix_dlc_issues(extract_dir)

        zks_file = output_path / output_name

        print(f"Creating Steam save file: {zks_file}")

        with zipfile.ZipFile(zks_file, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(extract_dir)
                    zip_ref.write(file_path, arcname)

        size_mb = zks_file.stat().st_size / (1024 * 1024)
        print(f"Created {zks_file.name} ({size_mb:.2f} MB)")

        return zks_file

    def list_containers_command(self) -> bool:
        """List all available containers and allow selection for conversion."""
        try:
            self.console.print("[bold]Discovering save containers...[/bold]")
            containers = self.discover_all_containers()

            if not containers:
                self.console.print(
                    "[red]No save containers found in WGS directory[/red]"
                )
                return False

            selected_containers = self.select_containers_interactive(containers)

            if not selected_containers:
                self.console.print("[yellow]No containers selected[/yellow]")
                return False

            # Ask if user wants to convert the selected containers
            if Confirm.ask("\nConvert selected containers to Steam format?"):
                fix_dlc = Confirm.ask("Fix DLC issues?", default=False)
                dryrun = Confirm.ask(
                    "Dry run (don't copy to Steam folder)?", default=False
                )

                return self.convert_multiple_saves(selected_containers, dryrun, fix_dlc)
            else:
                self.console.print("[yellow]Conversion cancelled[/yellow]")
                return True

        except Exception as e:
            self.console.print(f"[red]Error listing containers: {e}[/red]")
            return False

    def extract_save_name_from_header(self, container_folder: Path) -> Optional[str]:
        """Extract save name from the header JSON file (smallest file in container)."""
        try:
            files = [f for f in container_folder.iterdir() if f.is_file()]
            if not files:
                return None

            # Sort files by size and get second smallest (header file)
            files.sort(key=lambda x: x.stat().st_size)
            header_file = files[1]

            # Try to read the JSON and extract the Name field
            with open(header_file, "r", encoding="utf-8") as f:
                header_data = json.load(f)
                return header_data.get("Name", None)

        except (json.JSONDecodeError, FileNotFoundError, PermissionError, Exception):
            # If we can't read the header file for any reason, return None
            return None

@click.command()
@click.option(
    "--steam-save-path",
    "-s",
    type=str,
    default=None,
    help="Custom Steam save path. Default is the standard Steam save location.",
)
@click.option(
    "--dryrun",
    is_flag=True,
    help="Leave the converted save file in the temp directory and do not copy to Steam folder.",
)
@click.option(
    "--fix-dlc", is_flag=True, help="Remove DLC references from the save files."
)
@click.option(
    "--list-containers",
    "-l",
    is_flag=True,
    help="List all available save files and allow interactive selection.",
)
def main(
    steam_save_path: Optional[str], dryrun: bool, fix_dlc: bool, list_containers: bool
):
    """Xbox Game Pass to Steam Save Converter for Warhammer 40000 Rogue Trader."""
    converter = XboxToSteamConverter(steam_save_path=steam_save_path)

    try:
        if list_containers:
            success = converter.list_containers_command()
        else:
            success = converter.convert_save(dryrun=dryrun, fix_dlc=fix_dlc)

        if not success:
            click.echo("\nOperation failed. Please check the error messages above.")
            input("Press Enter to exit...")
            return 1

    except KeyboardInterrupt:
        click.echo("\n\nOperation cancelled by user.")
        return 1
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}")
        input("Press Enter to exit...")
        return 1

    input("\nPress Enter to exit...")
    return 0


if __name__ == "__main__":
    main()
