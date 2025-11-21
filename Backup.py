from concurrent.futures import ProcessPoolExecutor
import hashlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import humanize

from ProcessTimer import MeasureExecutionTime

ZipWorker = ProcessPoolExecutor()
DontCompressFileExtensions = (".mp4", ".mkv", ".zip", "tar.gz")

try:
    logging.info("您的Python版本支持ZStandard，将使用Zstandard算法进行压缩。")
    Algorithms = zipfile.ZIP_ZSTANDARD
except AttributeError:
    logging.warning("当前Python版本不支持Zstandard算法，将使用Deflate算法进行压缩。")
    Algorithms = zipfile.ZIP_DEFLATED

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

@MeasureExecutionTime(StageName="数据库备份")
def BackupDatabase(ShellCommand: list[str], OutputFileName: str, ErrorLogFileName: str, DatabaseName: str, RunAsUser: str | None = None):
    logging.info(f"正在备份数据库：{DatabaseName}")
    try:
        DatabaseDumpResult = subprocess.run(
            args=ShellCommand,
            capture_output=True,
            user=RunAsUser)
        if DatabaseDumpResult.returncode == 0:
            logging.info(f"{DatabaseName}备份成功。")
            logging.debug(f"{ShellCommand}的返回值：{DatabaseDumpResult.returncode}")
            logging.debug(f"{ShellCommand}输出的StdOut：{DatabaseDumpResult.stdout}")
            with open(OutputFileName, "bw+") as File:
                File.write(DatabaseDumpResult.stdout)
            logging.info(f"{DatabaseName}备份文件已保存：{OutputFileName}")
            logging.info(f"{DatabaseName}备份文件大小：{humanize.naturalsize(os.path.getsize(OutputFileName))}")
        else:
            logging.error(f"{DatabaseName}备份失败。")
            logging.debug(f"{ShellCommand}的返回值：{DatabaseDumpResult.returncode}")
            logging.debug(f"{ShellCommand}输出的StdErr：{DatabaseDumpResult.stderr}")
            logging.debug(f"{ShellCommand}输出的StdOut：{DatabaseDumpResult.stdout}")
            with open(ErrorLogFileName, "bw+") as File:
                File.write(DatabaseDumpResult.stderr)
            logging.info(f"{DatabaseName}错误日志已保存：{ErrorLogFileName}")
    except FileNotFoundError as Exception:
        logging.error(f"由于可执行文件{ShellCommand[0]}不存在，故跳过对{DatabaseName}的备份。")
        logging.debug(f"异常信息：{Exception}")
    finally:
        logging.info(f"{DatabaseName}数据库备份操作已完成。")

@MeasureExecutionTime(StageName="网站根目录备份")
def BackupWebsite(WebsiteLocation: Path, WebsiteZipFileName: str):
    ZipWorker.submit(ZipDirectoryTree, WebsiteZipFileName, WebsiteLocation)
    logging.info(f"网站根目录备份已保存：{WebsiteZipFileName}")
    logging.info(f"网站根目录备份文件大小：{humanize.naturalsize(os.path.getsize(WebsiteZipFileName))}")

@MeasureExecutionTime(StageName="Certbot备份")
def BackupCertbot(CertbotLocation: Path, CertbotZipFileName: str):
    ZipWorker.submit(ZipDirectoryTree, CertbotZipFileName, CertbotLocation)
    logging.info(f"Certbot目录备份已保存：{CertbotZipFileName}")
    logging.info(f"Certbot目录备份文件大小：{humanize.naturalsize(os.path.getsize(CertbotZipFileName))}")

@MeasureExecutionTime(StageName="计算SHA256校验和")
def GenerateSHA256Checksum(ChecksumFileName: Path, Directory: Path = Path(".")):
    with open(ChecksumFileName, "tw+") as ChecksumFile:
        Files = [FileName for FileName in Directory.iterdir() if FileName.suffix in [".sql", ".zip"]]
        for FileName in Files:
            SHA256 = hashlib.sha256()
            with open(FileName, "rb") as DataFile:
                SHA256.update(DataFile.read())
            ChecksumFile.write(f"{FileName}: {SHA256.hexdigest()}\n")

@MeasureExecutionTime(StageName="自定义路径备份件")
def BackupCustomPath(PathListFile: Path):
    if PathListFile.exists() == False:
        logging.warning(f"自定义路径列表文件 {PathListFile} 不存在，跳过自定义路径备份。")
        return
    Paths: list[Path] = []
    with open(PathListFile, "rt", encoding="utf-8") as File:
        Paths = [Path(Line.strip()) for Line in File.readlines() if Line.strip() != "" and Line.strip().startswith("#") == False]
    for BackupPath in Paths:
        if BackupPath.exists() == False:
            logging.warning(f"自定义路径 {BackupPath} 不存在，跳过对该条目的备份。")
            continue
        if BackupPath.is_file():
            logging.info(f"正在备份自定义文件：{BackupPath}")
            ZipWorker.submit(shutil.copy, BackupPath, os.getcwd())
        elif BackupPath.is_dir():
            logging.info(f"正在备份自定义目录：{BackupPath}")
            ZipWorker.submit(ZipDirectoryTree, f"{BackupPath}.zip", BackupPath)

@MeasureExecutionTime(StageName="打包所有文件")
def PackAllFiles(ZipFileName: str, Directory: Path):
    ZipDirectoryTree(ZipFileName, Directory)