from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
from threading import Lock
import zipfile

import humanize

from ProcessTimer import MeasureExecutionTime

ZipWorker = ThreadPoolExecutor()
DontCompressFileExtensions = (".mp4", ".mkv", ".zip", "tar.gz")
SHA256ResultFileLock: Lock = Lock()
SHA256 = hashlib.sha256()
Algorithms: int
try:
    Algorithms = zipfile.ZIP_ZSTANDARD
    logging.info("您使用的Python运行时支持Zstd，将使用Zstandard进行压缩")
except AttributeError:
    Algorithms = zipfile.ZIP_DEFLATED
    logging.warning("您使用的Python运行时不支持Zstd，将使用Deflate进行压缩，建议升级到Python 3.14或更高版本以获得更好的压缩性能")

def ZipDirectoryTree(ZipFileName: str, TargetDirectory: Path):
    with zipfile.ZipFile(ZipFileName, "w", Algorithms) as ZipFile:
        for FolderName, SubFolders, FileNames in os.walk(TargetDirectory):
            for FileName in FileNames:
                FilePath = os.path.join(FolderName, FileName)
                CompressLevel = 0 if FileName.endswith( DontCompressFileExtensions ) else 6
                ZipFile.write(FilePath, arcname=os.path.relpath(FilePath, TargetDirectory), compresslevel=CompressLevel)                    

def LogDirectoryTree(RootDirectory: Path, Prefix: str= ""):
    Entries = sorted(RootDirectory.iterdir())
    for Index, Entry in enumerate(Entries):
        Connector = "└── " if Index == len(Entries) - 1 else "├── "
        logging.info(f"{Prefix}{Connector}{Entry}")
        if Entry.is_dir():
            Extension = "    " if Index == len(Entries) - 1 else "│   "
            LogDirectoryTree(Entry, Prefix + Extension)

def BackupDatabase(ShellCommand: list[str], OutputFileName: str, ErrorLogFileName: str, DatabaseName: str, RunAsUser: str | None = None):
    logging.info(f"正在备份数据库：{DatabaseName}")
    try:
        with open(OutputFileName, "bw+") as OutputFile, open(ErrorLogFileName, "bw+") as ErrorLogFile:
            DatabaseDumpResult = subprocess.run(
                args=ShellCommand,
                stdout=OutputFile,
                stderr=ErrorLogFile,
                user=RunAsUser)
            if DatabaseDumpResult.returncode == 0:
                logging.info(f"{DatabaseName}备份成功。")
                logging.debug(f"{ShellCommand}的返回值：{DatabaseDumpResult.returncode}")
                logging.info(f"{DatabaseName}备份文件已保存：{OutputFileName}")
                logging.info(f"{DatabaseName}备份文件大小：{humanize.naturalsize(os.path.getsize(OutputFileName))}")
            else:
                logging.error(f"{DatabaseName}备份失败。")
                logging.debug(f"{ShellCommand}的返回值：{DatabaseDumpResult.returncode}")
                logging.debug(f"{ShellCommand}输出的StdErr：{ErrorLogFile.read().decode('utf-8')}")
                logging.info(f"{DatabaseName}错误日志已保存：{ErrorLogFileName}")
    except FileNotFoundError as Exception:
        logging.error(f"由于可执行文件{ShellCommand[0]}不存在，故跳过对{DatabaseName}的备份。")
        logging.debug(f"异常信息：{Exception}")
    except PermissionError as Exception:
        logging.error(f"由于权限不足，故无法备份{DatabaseName}。请切换到root或使用sudo重试。")
        logging.debug(f"异常信息：{Exception}")
    finally:
        if os.path.getsize(ErrorLogFileName) == 0:
            os.remove(ErrorLogFileName)
        if os.path.getsize(OutputFileName) == 0:
            os.remove(OutputFileName)
        logging.info(f"{DatabaseName}数据库备份操作已完成。")

def BackupWebsite(WebsiteLocation: Path, WebsiteZipFileName: str):
    ZipWorker.submit(ZipDirectoryTree, WebsiteZipFileName, WebsiteLocation)

def BackupCertbot(CertbotLocation: Path, CertbotZipFileName: str):
    ZipWorker.submit(ZipDirectoryTree, CertbotZipFileName, CertbotLocation)

def ComputeSingleFFileSHA256(FileName: Path, ResultFile: Path):
    with open(FileName, "rb") as DataFile:
            while DataChunk := DataFile.read(65536):
                SHA256.update(DataChunk)
    with SHA256ResultFileLock, open(ResultFile, "a", encoding="utf-8") as ChecksumFile:
        ChecksumFile.write(f"{FileName}: {SHA256.hexdigest()}\n")

def GenerateSHA256Checksum(ChecksumFileName: Path, Directory: Path = Path(".")):
    ChecksumWorker = ThreadPoolExecutor()
    Files = [FileName for FileName in Directory.iterdir()]
    for FileName in Files:
        ChecksumWorker.submit(ComputeSingleFFileSHA256, FileName, ChecksumFileName)
    ChecksumWorker.shutdown(wait=True)

def BackupCustomPath(PathListFile: Path):
    if PathListFile.exists() == False:
        logging.warning(f"自定义路径列表文件 {PathListFile} 不存在，跳过自定义路径备份。")
        return
    Paths: list[Path] = []
    with open(PathListFile, "rt", encoding="utf-8") as File:
        Paths = [Path(Line.strip()) for Line in File.readlines() if Line.strip() != "" and Line.strip().startswith("#") == False]
    if len(Paths) == 0:
        logging.info("自定义路径列表文件中没有有效条目，跳过自定义路径备份。")
        return
    for BackupPath in Paths:
        if BackupPath.exists() == False:
            logging.warning(f"自定义路径 {BackupPath} 不存在，跳过对该条目的备份。")
            continue
        if BackupPath.is_file():
            logging.info(f"正在备份自定义文件：{BackupPath}")
            ZipWorker.submit(shutil.copy, BackupPath, os.getcwd())
        elif BackupPath.is_dir():
            logging.info(f"正在备份自定义目录：{BackupPath}")
            ZipWorker.submit(ZipDirectoryTree, f"{BackupPath.name}.zip", BackupPath)

@MeasureExecutionTime(StageName="打包所有文件")
def PackAllFiles(ZipFileName: str, Directory: Path):
    ZipDirectoryTree(ZipFileName, Directory)