import os
import humanize

def GetDirectorySize(Path: str) -> tuple[int, str]:
    Total = 0
    for DirectoryPath, DirectoryNames, FileNames in os.walk(Path):
        for File in FileNames:
            FilePath = os.path.join(DirectoryPath, File)
            if os.path.isfile(FilePath):
                Total += os.path.getsize(FilePath)
    return Total, humanize.naturalsize(Total)