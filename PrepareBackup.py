import os
import sys
from pathlib import Path
import humanize

def GetDirectorySize(Path: Path) -> tuple[int, str]:
    Total = 0
    for DirectoryPath, DirectoryNames, FileNames in os.walk(Path):
        for File in FileNames:
            FilePath = os.path.join(DirectoryPath, File)
            if os.path.isfile(FilePath):
                Total += os.path.getsize(FilePath)
    return Total, humanize.naturalsize(Total)

def ParsePassArguments() -> tuple[bool, bool, bool, bool, bool]:
    SkipDatabaseBackup: bool = False
    SkipWebsiteBackup: bool = False
    SkipCertbotBackup: bool = False
    SkipCustomPathBackup: bool = False
    SkipUpload: bool = False
    if "--skip-database-backup" in sys.argv:
        SkipDatabaseBackup = True
    if "--skip-website-backup" in sys.argv:
        SkipWebsiteBackup = True
    if "--skip-certbot-backup" in sys.argv:
        SkipCertbotBackup = True
    if "--skip-custom-path-backup" in sys.argv:
        SkipCustomPathBackup = True
    if "--skip-upload" in sys.argv:
        SkipUpload = True
    return SkipDatabaseBackup, SkipWebsiteBackup, SkipCertbotBackup, SkipCustomPathBackup, SkipUpload