import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

import os
from pathlib import Path
import shutil
from datetime import datetime
import sys

import humanize.i18n
Original_naturalsize = humanize.naturalsize
def New_naturalsize(
    value: float | str,
    binary: bool = True,
    gnu: bool = False,
    format: str = "%.1f"):
    return Original_naturalsize(value=value, binary=binary, gnu=gnu, format=format)
humanize.naturalsize = New_naturalsize

from Backup import BackupCertbot, BackupCustomPath, BackupDatabase, BackupWebsite, GenerateSHA256Checksum, LogDirectoryTree, PackAllFiles, ZipWorker
from PrepareBackup import GetDirectorySize, ParsePassArguments
from Upload import GetBucketTotalSize, R2_Access_Key, R2_Bucket_Name, R2_Endpoint, R2_Secret_Key, UploadFile

CurrentTime: str = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
MySQLDumpCommand: list[str] = ["mysqldump", "-A"]
MySQLDumpedFileName: str = "MySQL.sql"
MySQLDumpErrorLogFileName: str = "MySQLError.log"
PostgreSQLDumpCommand: list[str] = ["pg_dumpall"]
PostgreSQLDumpedFileName: str = "PostgreSQL.sql"
PostgreSQLDumpErrorLogFileName: str = "PostgreSQLError.log"
WebsiteLocation: Path = Path("/var/www").resolve()
WebsiteZipFileName: str = "WebsiteRoot.zip"
CertbotLocation: Path = Path("/etc/letsencrypt").resolve()
CertbotZipFileName: str = "Certbot.zip"
BackupRootDirectory: Path = Path("Backup").resolve()    
BackupDirectorySizeLimit: int = 20 * (1024 ** 3)  # 20 GiB
ArchiveZipFileName: str = f"{CurrentTime}.zip"
ChecksumFileName: Path = Path("sha256.txt")
CustomPathListFileName: Path = Path("CustomPathList.txt")
SkipDatabaseBackup, SkipWebsiteBackup, SkipCertbotBackup, SkipCustomPathBackup, SkipUpload =  ParsePassArguments()

humanize.i18n.activate("zh_CN")
logging.info(f"MySQL保存命令：{MySQLDumpCommand}")
logging.info(f"PostgreSQL保存命令：{PostgreSQLDumpCommand}")
logging.info(f"网站根目录：{WebsiteLocation}")
logging.info(f"当前时间：{CurrentTime}")

if (sys.platform.startswith("linux") == False):
    logging.fatal("本程序仅支持Linux平台。")
    sys.exit(1)

logging.info("备份开始。")

if BackupRootDirectory.exists() == False:
    logging.info(f"备份根目录 {BackupRootDirectory} 不存在，正在创建。")
    BackupRootDirectory.mkdir()
else:
    logging.info(f"备份目录体积限制：{humanize.naturalsize(BackupDirectorySizeLimit)}")
    while True:
        TotalSize, TotalSizeHumanize = GetDirectorySize(BackupRootDirectory)
        logging.info(f"当前备份目录体积：{TotalSizeHumanize}")
        if TotalSize <= BackupDirectorySizeLimit:
            logging.info("备份目录体积在限制范围内，备份继续。")
            break
        Files = [File.name for File in BackupRootDirectory.iterdir() if File.is_file()]
        if len(Files) == 0:
            break
        Files.sort()
        Oldest = Files[0]
        OldestPath = os.path.join(BackupRootDirectory, Oldest)
        logging.warning(f"备份目录已超出体积限制，正在删除最旧的备份：{OldestPath}，文件大小：{humanize.naturalsize(os.path.getsize(OldestPath))}")
        os.remove(OldestPath)
os.chdir(BackupRootDirectory)

os.mkdir(CurrentTime)
os.chdir(CurrentTime)

logging.info("开始数据库备份。")
if SkipDatabaseBackup == True:
    logging.warning("由于传入了跳过数据库备份的参数，故跳过数据库备份。")
else:
    ZipWorker.submit(BackupDatabase, MySQLDumpCommand, MySQLDumpedFileName, MySQLDumpErrorLogFileName, "MySQL")
    ZipWorker.submit(BackupDatabase, PostgreSQLDumpCommand, PostgreSQLDumpedFileName, PostgreSQLDumpErrorLogFileName, "PostgreSQL", "postgres")

if SkipWebsiteBackup == True:
    logging.warning("由于传入了跳过网站备份的参数，故跳过网站备份。")
else:
    logging.info(f"开始备份网站根目录：{WebsiteLocation}")
    BackupWebsite(WebsiteLocation, WebsiteZipFileName)

if SkipCertbotBackup == True:
    logging.warning("由于传入了跳过Certbot备份的参数，故跳过Certbot备份。")
else:
    logging.info(f"开始备份Certbot目录：{CertbotLocation}")
    BackupCertbot(CertbotLocation, CertbotZipFileName)

if SkipCustomPathBackup == True:
    logging.warning("由于传入了跳过自定义路径备份的参数，故跳过自定义路径备份。")
else:
    logging.info("开始备份自定义路径。")
    BackupCustomPath(BackupRootDirectory.parent / CustomPathListFileName)

ZipWorker.shutdown(wait=True)
for File in os.listdir("."):
    logging.info(f"{File} 的大小为：{ humanize.naturalsize( os.path.getsize(File) ) }")

logging.info("开始计算备份文件的SHA256校验和。")
GenerateSHA256Checksum(ChecksumFileName)
logging.info("备份文件的SHA256校验和计算完成。")
logging.info(f"SHA256校验和已保存：{ChecksumFileName}")

logging.info("所有备份操作已完成。")
os.chdir("..")

logging.info(f"开始打包备份文件夹为：{ArchiveZipFileName}")
PackAllFiles(ArchiveZipFileName, Path(CurrentTime))
logging.info(f"备份文件夹已经打包完成，压缩文件大小：{humanize.naturalsize(os.path.getsize(ArchiveZipFileName))}")

logging.info(f"即将删除备份文件夹，内容如下：")
LogDirectoryTree(Path(CurrentTime))
shutil.rmtree(CurrentTime)
logging.info(f"已删除原始备份文件夹：{CurrentTime}")

if SkipUpload == True:
    logging.warning("由于传入了跳过上传备份的参数，故跳过上传备份。")
else:
    if all( S3_Config is not None for S3_Config in (R2_Endpoint, R2_Access_Key, R2_Secret_Key, R2_Bucket_Name) ) == True:
        logging.info("开始上传压缩文件到R2存储桶。")
        UploadFile(ArchiveZipFileName)
        logging.info(f"已上传备份文件：{ArchiveZipFileName}，文件大小：{humanize.naturalsize(os.path.getsize(ArchiveZipFileName))}。")
        logging.info(f"当前存储桶内的所有文件总共占用了：{GetBucketTotalSize(ForceFetch=True)[1]} 的空间。")
    else:
        logging.warning("由于缺少访问存储桶所需的必要信息，故跳过上传备份")
        logging.warning("具体情况请查看程序开始运行时打印的WARNING日志。")

logging.info("备份过程全部完成。")