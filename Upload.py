import datetime
import logging
import os
from threading import Lock, Thread
import time
from typing import Optional
from urllib.parse import urlparse

import boto3
import humanize
import schedule
from types_boto3_s3 import S3Client
from types_boto3_s3.type_defs import ListObjectsV2OutputTypeDef

from ProcessTimer import MeasureExecutionTime

R2_Endpoint = os.getenv("R2_Endpoint")
if R2_Endpoint is None:
    logging.warning("R2_Endpoint没有作为环境变量被提供，这将导致备份文件不会被上传到云端。")
if R2_Endpoint is not None:
    URL = urlparse(R2_Endpoint)
    R2_Endpoint = f"{URL.scheme}://{URL.netloc}"
R2_Access_Key = os.getenv("R2_Access_Key")
if R2_Access_Key is None:
    logging.warning("R2_Access_Key没有作为环境变量被提供，这将导致备份文件不会被上传到云端。")
R2_Secret_Key = os.getenv("R2_Secret_Key")
if R2_Secret_Key is None:
    logging.warning("R2_Secret_Key没有作为环境变量被提供，这将导致备份文件不会被上传到云端。")
R2_Bucket_Name = os.getenv("R2_Bucket_Name")
if R2_Bucket_Name is None:
    logging.warning("R2_Bucket_Name没有作为环境变量被提供，这将导致备份文件不会被上传到云端。")

S3: S3Client = boto3.client(
    "s3",
    aws_access_key_id=R2_Access_Key,
    aws_secret_access_key=R2_Secret_Key,
    endpoint_url=R2_Endpoint,
    region_name="auto")
AllObjectsInBucket: Optional[ListObjectsV2OutputTypeDef] = None
R2_Free_Space = 10 * (1000 ** 3) # 10GB
BytesHasBeenTransferred: int = 0
BytesHasBeenTransferredPast1Second: int = 0
ProgressLock = Lock()
TaskHasEnded = False
FileSize: int 

def GetBucketTotalSize(ForceFetch: bool = False) -> tuple[int, str]:
    assert S3 is not None
    assert R2_Bucket_Name is not None

    global AllObjectsInBucket
    Total_Size = 0
    if AllObjectsInBucket is None:
        AllObjectsInBucket = S3.list_objects_v2(Bucket=R2_Bucket_Name)
        if "Contents" not in AllObjectsInBucket:
            logging.info("存储桶内没有任何文件。")
            return 0, humanize.naturalsize(0)
    if ForceFetch == True:
        AllObjectsInBucket = S3.list_objects_v2(Bucket=R2_Bucket_Name)
    try:
        for Object in AllObjectsInBucket["Contents"]: # type: ignore
            Total_Size += Object["Size"] # type: ignore
    except KeyError:
        return 0, humanize.naturalsize(0)
    Size_Humanize = humanize.naturalsize(Total_Size)
    return Total_Size, Size_Humanize

def OptimizeStorage(FileSize: int):
    assert S3 is not None
    assert R2_Bucket_Name is not None
    
    if GetBucketTotalSize()[0] == 0:
        return
    ObjectNameToLastModifiedDict = {
        Name: LastModifiedDate
        for Name, LastModifiedDate in sorted( (
                ( Object.get("Key"), Object.get("LastModified") or datetime.datetime.now() )
                for Object in AllObjectsInBucket["Contents"]), # type: ignore
            key=lambda item: item[1],
            reverse=True ) }
    while FileSize + GetBucketTotalSize()[0] > R2_Free_Space:
        DeleteFileName, DeleteFileLastModifiedDate = ObjectNameToLastModifiedDict.popitem()
        assert DeleteFileName is not None
        S3.delete_object(Bucket=R2_Bucket_Name, Key=DeleteFileName)
        AllObjectsInBucket["Contents"] = [ # type: ignore
            Object for Object in AllObjectsInBucket["Contents"] # type: ignore
            if Object.get("Key") != DeleteFileName ]
        logging.warning("存储空间不足，已删除最旧的备份文件：{0}，最后修改时间：{1}。".format(DeleteFileName, DeleteFileLastModifiedDate.strftime("%Y-%m-%d %H:%M:%S")))
    GetBucketTotalSize(ForceFetch=True)

def WriteProgress(TransferredBytes: int):
    global BytesHasBeenTransferredPast1Second, BytesHasBeenTransferred, ProgressLock, FileSize
    with ProgressLock:
        BytesHasBeenTransferredPast1Second += TransferredBytes
        BytesHasBeenTransferred = min(BytesHasBeenTransferred + TransferredBytes, FileSize)
def ShowProgress():
    global BytesHasBeenTransferredPast1Second, BytesHasBeenTransferred, ProgressLock
    with ProgressLock:
        logging.info(f"已上传：{humanize.naturalsize(BytesHasBeenTransferred)}，当前速度：{humanize.naturalsize(BytesHasBeenTransferredPast1Second)}/秒")
        BytesHasBeenTransferredPast1Second = 0
def RunTask():
    while TaskHasEnded == False:
        schedule.run_pending()
        time.sleep(0.3)

@MeasureExecutionTime("上传备份文件")
def UploadFile(FilePath: str):
    global TaskHasEnded, FileSize
    assert S3 is not None
    assert R2_Bucket_Name is not None

    logging.info(f"当前存储桶内的所有文件总共占用了：{GetBucketTotalSize()[1]} 的空间。")
    FileSize = os.path.getsize(FilePath)
    OptimizeStorage(FileSize)
    schedule.every(1).seconds.do(ShowProgress)
    TaskThread = Thread(target=RunTask, daemon=True)
    TaskThread.start()
    S3.upload_file(FilePath, 
                   R2_Bucket_Name, 
                   os.path.basename(FilePath), 
                   Callback=WriteProgress)
    schedule.clear()
    TaskHasEnded = True
    TaskThread.join()