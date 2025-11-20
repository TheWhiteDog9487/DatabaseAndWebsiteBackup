import logging
import os
from pathlib import Path
import shutil
from datetime import datetime

import humanize

from Backup import BackupCertbot, BackupCustomPath, BackupDatabase, BackupWebsite, GenerateSHA256Checksum, LogDirectoryTree, PackAllFiles
from PrepareBackup import GetDirectorySize
from Upload import GetBucketTotalSize, UploadFile

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
BackupDirectorySizeLimit: int = 10 * 1024 * 1024 * 1024  # 10 GiB
ArchiveZipFileName: str = f"{CurrentTime}.zip"
ChecksumFileName: str = "sha256.txt"
CustomPathListFileName: str = "CustomPathList.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
humanize.i18n.activate("zh_CN") # type: ignore
logging.info(f"MySQL保存命令：{MySQLDumpCommand}")
logging.info(f"PostgreSQL保存命令：{PostgreSQLDumpCommand}")
logging.info(f"网站根目录：{WebsiteLocation}")
logging.info(f"当前时间：{CurrentTime}")

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
        Files = [File for File in os.listdir(BackupRootDirectory) if os.path.isfile(os.path.join(BackupRootDirectory, File))]
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
BackupDatabase(MySQLDumpCommand, MySQLDumpedFileName, MySQLDumpErrorLogFileName, "MySQL")
BackupDatabase(PostgreSQLDumpCommand, PostgreSQLDumpedFileName, PostgreSQLDumpErrorLogFileName, "PostgreSQL", "postgres")
logging.info("数据库备份完成。")

logging.info(f"正在备份网站根目录：{WebsiteLocation}")
BackupWebsite(WebsiteLocation, WebsiteZipFileName)
logging.info(f"网站根目录备份已保存：{WebsiteZipFileName}")
logging.info(f"网站根目录备份文件大小：{humanize.naturalsize(os.path.getsize(WebsiteZipFileName))}")

logging.info(f"正在备份Certbot目录：{CertbotLocation}")
BackupCertbot(CertbotLocation, CertbotZipFileName)
logging.info(f"Certbot目录备份已保存：{CertbotZipFileName}")
logging.info(f"Certbot目录备份文件大小：{humanize.naturalsize(os.path.getsize(CertbotZipFileName))}")

logging.info("开始备份自定义路径。")
BackupCustomPath(BackupRootDirectory.parent / CustomPathListFileName)
logging.info("自定义路径备份完成。")

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

logging.info("开始上传压缩文件到R2存储桶。")
UploadFile(ArchiveZipFileName)
logging.info(f"已上传备份文件：{ArchiveZipFileName}，文件大小：{humanize.naturalsize(os.path.getsize(ArchiveZipFileName))}。")
logging.info(f"当前存储桶内的所有文件总共占用了：{GetBucketTotalSize()[1]} 的空间。")