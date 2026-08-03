---
title: "AWS CLI with MinIO Server"
url: "/integrations/aws-cli-with-minio/"
weight: 30
minio_origin: true
silo_modified: true
---

<a id="aws-cli-with-minio-server"></a>

[![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io)

AWS CLI is a unified tool to manage AWS services. It is frequently the tool used to transfer data in and out of AWS S3. It works with any S3 compatible cloud storage service.

In this recipe we will learn how to configure and use AWS CLI to manage data with MinIO Server.

## 1. Prerequisites {#prerequisites}

Install MinIO Server from [here](https://silo.pgsty.com/operations/deployments/installation/).

## 2. Installation {#installation}

Install AWS CLI from [https://aws.amazon.com/cli/](https://aws.amazon.com/cli/)

## 3. Configuration {#configuration}

To configure AWS CLI, type `aws configure` and specify the MinIO key information.

Access credentials shown in this example belong to [https://play.min.io:9000](https://play.min.io:9000). These credentials are open to public. Feel free to use this service for testing and development. Replace with your own MinIO keys in deployment.

```sh
aws configure
AWS Access Key ID [None]: Q3AM3UQ867SPQQA43P2F
AWS Secret Access Key [None]: zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG
Default region name [None]: us-east-1
Default output format [None]: ENTER

```

Additionally enable AWS Signature Version ‘4’ for MinIO server.

```sh
aws configure set default.s3.signature_version s3v4

```

## 4. Commands {#commands}

### To list your buckets {#to-list-your-buckets}

```sh
aws --endpoint-url https://play.min.io:9000 s3 ls
2016-03-27 02:06:30 deebucket
2016-03-28 21:53:49 guestbucket
2016-03-29 13:34:34 mbtest
2016-03-26 22:01:36 mybucket
2016-03-26 15:37:02 testbucket

```

### To list contents inside bucket {#to-list-contents-inside-bucket}

```sh
aws --endpoint-url https://play.min.io:9000 s3 ls s3://mybucket
2016-03-30 00:26:53      69297 argparse-1.2.1.tar.gz
2016-03-30 00:35:37      67250 simplejson-3.3.0.tar.gz

```

### To make a bucket {#to-make-a-bucket}

```sh
aws --endpoint-url https://play.min.io:9000 s3 mb s3://mybucket
make_bucket: s3://mybucket/

```

### To add an object to a bucket {#to-add-an-object-to-a-bucket}

```sh
aws --endpoint-url https://play.min.io:9000 s3 cp simplejson-3.3.0.tar.gz s3://mybucket
upload: ./simplejson-3.3.0.tar.gz to s3://mybucket/simplejson-3.3.0.tar.gz

```

### To delete an object from a bucket {#to-delete-an-object-from-a-bucket}

```sh
aws --endpoint-url https://play.min.io:9000 s3 rm s3://mybucket/argparse-1.2.1.tar.gz
delete: s3://mybucket/argparse-1.2.1.tar.gz

```

### To remove a bucket {#to-remove-a-bucket}

```sh
aws --endpoint-url https://play.min.io:9000 s3 rb s3://mybucket
remove_bucket: s3://mybucket/

```
