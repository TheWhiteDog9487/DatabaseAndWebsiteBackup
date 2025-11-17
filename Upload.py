import datetime
import logging
import os
import sys

import boto3
import humanize
from types_boto3_s3 import S3Client

from ProcessTimer import MeasureExecutionTime

try:
    R2_Endpoint = sys.argv[sys.argv.index("R2_Endpoint") + 1]
except ValueError:
    print("R2_Endpoint not provided. Please provide it as a command line argument.")
    sys.exit(1)
try:
    R2_Access_Key = sys.argv[sys.argv.index("R2_Access_Key") + 1]
except ValueError:
    print("R2_Access_Key not provided. Please provide it as a command line argument.")
    sys.exit(1)
try:
    R2_Secret_Key = sys.argv[sys.argv.index("R2_Secret_Key") + 1]
except ValueError:
    print("R2_Secret_Key not provided. Please provide it as a command line argument.")
    sys.exit(1)
try:
    R2_Bucket_Name = sys.argv[sys.argv.index("R2_Bucket_Name") + 1]
except ValueError:
    print("R2_Bucket_Name not provided. Please provide it as a command line argument.")
    sys.exit(1)

S3: S3Client = boto3.client(
    "s3",
    aws_access_key_id=R2_Access_Key,
    aws_secret_access_key=R2_Secret_Key,
    endpoint_url=R2_Endpoint,
    region_name="auto" )
ObjectLastModifiedMap: dict[str, datetime.datetime] = {}
R2_Free_Space = 10 * (1024 ** 3) # 10GB

def GetBucketTotalSize() -> tuple[int, str]:
    global ObjectLastModifiedMap
    Total_Size = 0
    Response = S3.list_objects_v2(Bucket=R2_Bucket_Name)
    for Object in Response.get("Contents", []) :
        Total_Size += Object.get("Size") or 0
        ObjectName = Object.get("Key") or ""
        LastModified = Object.get("LastModified") or datetime.datetime.now()
        ObjectLastModifiedMap[ObjectName] = LastModified
    ObjectLastModifiedMap = { k: v for k, v in sorted(ObjectLastModifiedMap.items(), key=lambda item: item[1], reverse=True) }
    Size_Humanize = humanize.naturalsize(Total_Size)
    return Total_Size, Size_Humanize

def OptimizeStorage(FileSize: int):
    while FileSize + GetBucketTotalSize()[0] > R2_Free_Space:
        DeleteFileName, DeleteFileLastModifiedDate = ObjectLastModifiedMap.popitem()
        S3.delete_object(Bucket=R2_Bucket_Name, Key=DeleteFileName)
        logging.warning("存储空间不足，已删除最旧的备份文件：{0}，最后修改时间：{1}。".format(DeleteFileName, DeleteFileLastModifiedDate.strftime("%Y-%m-%d %H:%M:%S")))

@MeasureExecutionTime("上传备份文件")
def UploadFile(FilePath: str):
    logging.info(f"当前存储桶内的所有文件总共占用了：{GetBucketTotalSize()[1]} 的空间。")
    FileSize = os.path.getsize(FilePath)
    OptimizeStorage(FileSize)
    S3.upload_file(FilePath, 
                   R2_Bucket_Name, 
                   os.path.basename(FilePath), 
                   Callback= lambda TransferredBytes: 
                        print(f"已上传 {humanize.naturalsize(TransferredBytes)}") )