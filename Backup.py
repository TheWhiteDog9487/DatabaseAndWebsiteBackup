# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "humanize>=4.12.3",
# ]
# ///

from datetime import datetime
import subprocess
import sys
import zipfile
import os
import logging
import shutil
from time import time

import humanize

CurrentTime: str = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
MySQLDumpCommand: list[str] = ["mysqldump", "-A"]
MySQLDumpedFileName: str = "MySQL.sql"
MySQLDumpErrorLogFileName: str = "MySQLError.log"
PostgreSQLDumpCommand: list[str] = ["pg_dumpall"]
PostgreSQLDumpedFileName: str = "PostgreSQL.sql"
PostgreSQLDumpErrorLogFileName: str = "PostgreSQLError.log"
WebsiteLocation: str = "/var/www"
WebsiteZipFileName: str = "WebsiteRoot.zip"
BackupRootDirectory: str = "Backup"
BackupDirectorySizeLimit: int = 10 * 1024 * 1024 * 1024  # 10 GiB
ArchiveZipFileName = f"{CurrentTime}.zip"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
humanize.i18n.activate("zh_CN")
logging.info(f"MySQL保存命令：{MySQLDumpCommand}")
logging.info(f"PostgreSQL保存命令：{PostgreSQLDumpCommand}")
logging.info(f"网站根目录：{WebsiteLocation}")
logging.info(f"当前时间：{CurrentTime}")

def GetDirectorySize(Path: str) -> tuple[int, str]:
    Total = 0
    for DirectoryPath, DirectoryNames, FileNames in os.walk(Path):
        for File in FileNames:
            FilePath = os.path.join(DirectoryPath, File)
            if os.path.isfile(FilePath):
                Total += os.path.getsize(FilePath)
    return Total, humanize.naturalsize(Total)

TotalStartTime = time()
logging.info("备份开始。")

if os.path.exists(BackupRootDirectory) == False:
    logging.info(f"备份根目录 {BackupRootDirectory} 不存在，正在创建。")
    os.mkdir(BackupRootDirectory)
else:
    while True:
        TotalSize = GetDirectorySize(BackupRootDirectory)
        logging.info(f"当前备份目录体积：{humanize.naturalsize(TotalSize)}")
        logging.info(f"备份目录体积限制：{humanize.naturalsize(BackupDirectorySizeLimit)}")
        if TotalSize <= BackupDirectorySizeLimit:
            break
        SubDirectories = [Directory for Directory in os.listdir(BackupRootDirectory) if os.path.isdir(os.path.join(BackupRootDirectory, Directory))]
        if not SubDirectories:
            break
        SubDirectories.sort()
        Oldest = SubDirectories[0]
        OldestPath = os.path.join(BackupRootDirectory, Oldest)
        logging.warning(f"备份目录已超出体积限制，正在删除最旧的备份：{OldestPath}")
        shutil.rmtree(OldestPath)
os.chdir(BackupRootDirectory)

os.mkdir(CurrentTime)
os.chdir(CurrentTime)

def BackupDatabase(ShellCommand: list[str], OutputFileName: str, ErrorLogFileName: str, DatabaseName: str, RunAsUser: str | None = None):
    StartTime = time()
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
    EndTime = time()
    logging.info(f"{DatabaseName}备份耗时：{humanize.precisedelta(EndTime - StartTime)}")

DatabaseStageStart = time()
logging.info("开始数据库备份。")

BackupDatabase(MySQLDumpCommand, MySQLDumpedFileName, MySQLDumpErrorLogFileName, "MySQL")
BackupDatabase(PostgreSQLDumpCommand, PostgreSQLDumpedFileName, PostgreSQLDumpErrorLogFileName, "PostgreSQL", "postgres")

DatabaseStageEnd = time()
logging.info("数据库备份完成。")
logging.info(f"数据库备份耗时：{humanize.naturaldelta(DatabaseStageEnd - DatabaseStageStart)}")

if(len(os.listdir(".")) == 0):
    logging.warning(f"没有备份任何内容，删除空目录：{CurrentTime}")
    os.chdir("..")
    os.rmdir(CurrentTime)

WebsiteStageStart = time()
logging.info("网站根目录备份开始。")

logging.info(f"正在备份网站根目录：{WebsiteLocation}")
with zipfile.ZipFile("WebsiteRoot.zip", "w", compression=zipfile.ZIP_DEFLATED) as ZipFile:
    for FolderName, SubFolders, FileNames in os.walk(WebsiteLocation):
        for FileName in FileNames:
            ZipFile.write(os.path.join(FolderName, FileName), arcname=os.path.relpath(os.path.join(FolderName, FileName), WebsiteLocation), compresslevel= 0 if FileName.endswith((".mp4", ".mkv", ".zip", ".tar.gz")) else 6)
logging.info(f"网站根目录备份已保存：WebsiteRoot.zip")
logging.info(f"网站根目录备份文件大小：{humanize.naturalsize(os.path.getsize('WebsiteRoot.zip'))}")

WebsiteStageEnd = time()
logging.info("网站根目录备份完成。")
logging.info(f"网站根目录备份耗时：{humanize.precisedelta(WebsiteStageEnd - WebsiteStageStart)}")

TotalEndTime = time()
logging.info("备份完成时间。")
logging.info(f"备份总耗时：{humanize.precisedelta(TotalEndTime - TotalStartTime)}")
logging.info("所有备份操作已完成。")

os.chdir("..")
ZipStartTime = time()
ZipFileName = f"{CurrentTime}.zip"
logging.info(f"开始打包备份文件夹为：{ZipFileName}")

with zipfile.ZipFile(ZipFileName, "w") as BackupZipFile:
    for FolderName, SubFolders, FileNames in os.walk(CurrentTime):
        for FileName in FileNames:
            FilePath = os.path.join(FolderName, FileName)
            ArchiveName = os.path.relpath(FilePath, CurrentTime)
            BackupZipFile.write(
                FilePath,
                arcname=ArchiveName,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=0 if FileName.endswith(".zip") else 6)
logging.info("备份文件夹已经打包完成。")
logging.info(f"Zip文件大小：{humanize.naturalsize(os.path.getsize(ArchiveZipFileName))}")
ZipEndTime = time()
logging.info(f"打包耗时：{humanize.precisedelta(ZipEndTime - ZipStartTime)}")

def LogDirectoryTree(RootDirectory, Prefix=""):
    Entries = sorted(os.listdir(RootDirectory))
    for Index, Entry in enumerate(Entries):
        Path = os.path.join(RootDirectory, Entry)
        Connector = "└── " if Index == len(Entries) - 1 else "├── "
        logging.info(f"{Prefix}{Connector}{Entry}")
        if os.path.isdir(Path):
            Extension = "    " if Index == len(Entries) - 1 else "│   "
            LogDirectoryTree(Path, Prefix + Extension)

logging.info(f"即将删除备份文件夹，内容如下：")
LogDirectoryTree(CurrentTime)

DeleteStartTime = time()
shutil.rmtree(CurrentTime)
logging.info(f"已删除原始备份文件夹：{CurrentTime}")
DeleteEndTime = time()
logging.info(f"删除文件夹耗时：{humanize.precisedelta(DeleteEndTime - DeleteStartTime)}")