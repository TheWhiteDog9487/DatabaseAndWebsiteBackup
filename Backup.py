import hashlib
import logging
import os
import shutil
import subprocess
import sys
import zipfile

import humanize

from ProcessTimer import MeasureExecutionTime


def ZipDirectoryTree(ZipFileName: str, TargetDirectory: str):
    with zipfile.ZipFile(ZipFileName, "w", zipfile.ZIP_ZSTANDARD) as ZipFile:
        for FolderName, SubFolders, FileNames in os.walk(TargetDirectory):
            for FileName in FileNames:
                ZipFile.write(os.path.join(FolderName, FileName), arcname=os.path.relpath(os.path.join(FolderName, FileName), TargetDirectory), compresslevel= 0 if FileName.endswith((".mp4", ".mkv", ".zip", ".tar.gz")) else 6)

def LogDirectoryTree(RootDirectory: str, Prefix: str= ""):
    Entries = sorted(os.listdir(RootDirectory))
    for Index, Entry in enumerate(Entries):
        Path = os.path.join(RootDirectory, Entry)
        Connector = "└── " if Index == len(Entries) - 1 else "├── "
        logging.info(f"{Prefix}{Connector}{Entry}")
        if os.path.isdir(Path):
            Extension = "    " if Index == len(Entries) - 1 else "│   "
            LogDirectoryTree(Path, Prefix + Extension)

@MeasureExecutionTime(StageName="数据库备份")
def BackupDatabase(ShellCommand: list[str], OutputFileName: str, ErrorLogFileName: str, DatabaseName: str, RunAsUser: str | None = None):
    if (sys.platform == "win32"):
        RunAsUser = None
        logging.warning("在Windows系统上运行时，无法指定用户。")
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

@MeasureExecutionTime(StageName="网站根目录备份")
def BackupWebsite(WebsiteLocation: str, WebsiteZipFileName: str):
    ZipDirectoryTree(WebsiteZipFileName, WebsiteLocation)

@MeasureExecutionTime(StageName="Certbot备份")
def BackupCertbot(CertbotLocation: str, CertbotZipFileName: str):
    ZipDirectoryTree(CertbotZipFileName, CertbotLocation)

@MeasureExecutionTime(StageName="计算SHA256校验和")
def GenerateSHA256Checksum(ChecksumFileName: str, Directory: str = "."):
    with open(ChecksumFileName, "tw+") as ChecksumFile:
        Files = [FileName for FileName in os.listdir(Directory) if FileName.endswith((".sql", ".zip"))]
        for FileName in Files:
            SHA256 = hashlib.sha256()
            with open(FileName, "rb") as DataFile:
                SHA256.update(DataFile.read())
            ChecksumFile.write(f"{FileName}: {SHA256.hexdigest()}\n")

@MeasureExecutionTime(StageName="自定义路径备份件")
def BackupCustomPath(PathListFile: str):
    if os.path.exists(PathListFile) == False:
        logging.warning(f"自定义路径列表文件 {PathListFile} 不存在，跳过自定义路径备份。")
        return
    Paths: list[str] = []
    with open(PathListFile, "rt", encoding="utf-8") as File:
        Paths = [Line.strip() for Line in File.readlines() if Line.strip() != "" and Line.strip().startswith("#") == False]
    for Path in Paths:
        if os.path.exists(Path) == False:
            logging.warning(f"自定义路径 {Path} 不存在，跳过对该条目的备份。")
            continue
        if os.path.isfile(Path):
            logging.info(f"正在备份自定义文件：{Path}")
            shutil.copyfile(Path, os.getcwd())
        elif os.path.isdir(Path):
            logging.info(f"正在备份自定义目录：{Path}")
            ZipDirectoryTree(f"{os.path.basename(Path)}.zip", Path)

@MeasureExecutionTime(StageName="打包所有文件")
def PackAllFiles(ZipFileName: str, Directory: str):
    ZipDirectoryTree(ZipFileName, Directory)
