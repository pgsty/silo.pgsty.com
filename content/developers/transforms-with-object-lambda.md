---
title: "Transforms with Object Lambda"
url: "/developers/transforms-with-object-lambda/"
weight: 210
icon: fa-solid fa-wand-magic-sparkles
minio_origin: true
silo_modified: true
---

<a id="transforms-with-object-lambda"></a>
<a id="developers-object-lambda"></a>

MinIO’s Object Lambda enables developers to programmatically transform objects on demand. You can transform objects as needed for your use case, such as redacting personally identifiable information (PII), enriching data with information from other sources, or converting between formats.

## Overview {#overview}

An [Object Lambda handler](#minio-object-lambda-handers) is a small code module that transforms the contents of an object and returns the results. Like [Amazon S3 Object Lambda functions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/transforming-objects.html), you trigger a MinIO Object Lambda handler function with a GET request from an application. The handler retrieves the requested object from MinIO, transforms it, and returns the modified data back to MinIO to send to the original application. The original object remains unchanged.

Each handler is an independent process, and multiple handlers can transform the same data. This allows you to use the same object for different purposes without maintaining different versions of the original.

<a id="minio-object-lambda-handers"></a>

## Object Lambda Handlers {#object-lambda-handlers}

You can write a handler function in any language capable of sending and receiving HTTP requests. It must be able to:

- Listen for an HTTP POST request.
- Retrieve the original object using a URL.
- Return the transformed contents and authorization tokens.

### Create a Function {#create-a-function}

A handler function should perform the following steps:

1. Extract the object details from the incoming POST request.

   The `getObjectContext` property of the JSON request payload contains details about the original object. To construct the response, you need the following values:

   | Value | Description |
   | --- | --- |
   | `inputS3Url` | A [presigned URL](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedGetObject) for the original object. The calling application generates the URL and sends it in the original request. This allows the handler to access the original object without the MinIO credentials usually required. The URL is valid for one hour. |
   | `outputRoute` | A token that allows MinIO to validate the destination for the transformed object. Return this value with the response in an `x-amz-request-route` header. |
   | `outputToken` | A token that allows MinIO to validate the response. Return this value in the response in an `x-amz-request-token` header. |
2. Retrieve the original object from MinIO.

   Use the presigned URL to retrieve the object from the MinIO deployment. The contents of the object are in the body of the response.
3. Transform the object as desired.

   Perform any operations needed to generate a transformed object. Since the calling application is waiting for a response, you may wish to avoid potentially long running operations.
4. Construct a response containing the following information:

   - The transformed object contents.
   - An `x-amz-request-route` header with the `outputRoute` token.
   - An `x-amz-request-token` header with the `outputToken` token.
5. Return the response back to Object Lambda.

   MinIO validates the response and sends the transformed data back to the original calling application.

{{% alert color="info" %}}
**Response headers**

Handlers **must** include the `outputRoute` and `outputToken` values in the appropriate response headers. This allows MinIO to correctly validate the response from the handler.
{{% /alert %}}

### Register the Handler {#register-the-handler}

To enable MinIO to call the handler, register the handler function as a webhook with the following [MinIO server Object Lambda environment variables](/reference/minio-server/settings/object-lambda/#minio-server-envvar-object-lambda-webhook):

**[`MINIO_LAMBDA_WEBHOOK_ENABLE_functionname`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_ENABLE)**

> Enable or disable Object Lambda for a handler function. For multiple handlers, set this environment variable for each function name.

**[`MINIO_LAMBDA_WEBHOOK_ENDPOINT_functionname`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_ENDPOINT)**

> Register an endpoint for a handler function. For multiple handlers, set this environment variable for each function endpoint.

MinIO also supports the following environment variables for authenticated webhook endpoints:

**[`MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN_functionanme`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN)**

> Specify the opaque string or JWT authorization token for authenticating to the webhook.

**[`MINIO_LAMBDA_WEBHOOK_CLIENT_CERT_functionname`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_CLIENT_CERT)**

> Specify the client certificate to use for mTLS authentication to the webhook.

**[`MINIO_LAMBDA_WEBHOOK_CLIENT_KEY_functionname`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_CLIENT_CERT)**

> Specify the private key to use for mTLS authentication to the webhook.

Restart MinIO to apply the changes.

Alternatively, configure Object Lambda with the [MinIO Client](/reference/minio-mc/#minio-client) command line tool. For more information, see [Object Lambda function settings](/reference/minio-server/settings/object-lambda/#minio-server-envvar-object-lambda-webhook).

### Trigger From an Application {#trigger-from-an-application}

To request a transformed object from your application:

1. Connect to the MinIO deployment.
2. Set the Object Lambda target by adding a `lambdaArn` parameter with the ARN of the desired handler.
3. Generate a [presigned URL](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedGetObject) for the original object.
4. Use the generated URL to retrieve the transformed object.

   MinIO sends the request to the target Object Lambda handler. The handler returns the transformed contents back to MinIO, which validates the response and sends it back to the application.

## Example {#example}

Transform the contents of an object using Python, Go, and `curl`:

- Create and register an Object Lambda handler.
- Create a bucket and an object to transform.
- Request and display the transformed object contents.

Prerequisites:

- An existing [MinIO](/operations/deployments/installation/#minio-installation) deployment
- Working Python (3.8+) and Golang development environments
- [The MinIO Go SDK](/developers/go/minio-go/)

### Create a Handler {#create-a-handler}

The sample handler, written in Python, retrieves the target object using a [presigned URL](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedGetObject) generated by the caller. The handler then transforms the object’s contents and returns the new text. It uses the [Flask web framework](https://flask.palletsprojects.com/en/2.2.x/) and Python 3.8+.

The following command installs Flask and other needed dependencies:

```shell
pip install flask requests
```

The handler calls `swapcase()` to change the case of each letter in the original text. It then sends the results back to MinIO, which returns it to the caller.

```py
from flask import Flask, request, abort, make_response
import requests

app = Flask(__name__)
@app.route('/', methods=['POST'])
def get_webhook():
   if request.method == 'POST':
      # Get the request event from the 'POST' call
      event = request.json

      # Get the object context
      object_context = event["getObjectContext"]

      # Get the presigned URL
      # Used to fetch the original object from MinIO
      s3_url = object_context["inputS3Url"]

      # Extract the route and request tokens from the input context
      request_route = object_context["outputRoute"]
      request_token = object_context["outputToken"]

      # Get the original S3 object using the presigned URL
      r = requests.get(s3_url)
      original_object = r.content.decode('utf-8')

      # Transform the text in the object by swapping the case of each char
      transformed_object = original_object.swapcase()

      # Return the object back to Object Lambda, with required headers
      # This sends the transformed data to MinIO
      # and then to the user
      resp = make_response(transformed_object, 200)
      resp.headers['x-amz-request-route'] = request_route
      resp.headers['x-amz-request-token'] = request_token
      return resp

   else:
      abort(400)

if __name__ == '__main__':
   app.run()
```

#### Start the Handler {#start-the-handler}

Use the following command to start the handler in your local development environment:

```shell
python lambda_handler.py
```

The output resembles the following:

```shell
 * Serving Flask app 'lambda_handler'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

#### Start MinIO {#start-minio}

Once the handler is running, start MinIO with the [`MINIO_LAMBDA_WEBHOOK_ENABLE`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_ENABLE) and [`MINIO_LAMBDA_WEBHOOK_ENDPOINT`](/reference/minio-server/settings/object-lambda/#envvar.MINIO_LAMBDA_WEBHOOK_ENDPOINT) environment variables to register the function with MinIO. To identify the specific Object Lambda handler, append the name of the function to the name of the environment variable.

The following command starts MinIO in your local development environment:

```shell
MINIO_LAMBDA_WEBHOOK_ENABLE_myfunction=on MINIO_LAMBDA_WEBHOOK_ENDPOINT_myfunction=http://localhost:5000 minio server /data
```

Replace `myfunction` with the name of your handler function and `/data` with the location of the MinIO directory for your local deployment. The output resembles the following:

```shell
MinIO Object Storage Server
Copyright: 2015-2023 MinIO, Inc.
License: GNU AGPLv3 <https://www.gnu.org/licenses/agpl-3.0.html>
Version: RELEASE.2023-03-24T21-41-23Z (go1.19.7 linux/arm64)

Status:         1 Online, 0 Offline.
API: http://192.168.64.21:9000  http://127.0.0.1:9000
RootUser: minioadmin
RootPass: minioadmin
Object Lambda ARNs: arn:minio:s3-object-lambda::myfunction:webhook
```

### Test the Handler {#test-the-handler}

To test the Lambda handler function, first create an object to transform. Then invoke the handler, in this case with `curl`, using the presigned URL from a Go function.

1. Create a bucket and object for the handler to transform.

   ```shell
   mc alias set myminio/ http://localhost:9000 minioadmin minioadmin
   mc mb myminio/myfunctionbucket
   cat > testobject << EOF
   Hello, World!
   EOF
   mc cp testobject myminio/myfunctionbucket/
   ```
2. Invoke the Handler

   The following Go code uses the [The MinIO Go SDK](/developers/go/minio-go/) to generate a presigned URL and print it to `stdout`.

   ```go
   package main

   import (
      "context"
      "log"
      "net/url"
      "time"
      "fmt"

      "github.com/minio/minio-go/v7"
      "github.com/minio/minio-go/v7/pkg/credentials"
   )

   func main() {

      // Connect to the MinIO deployment
      s3Client, err := minio.New("localhost:9000", &minio.Options{
         Creds:  credentials.NewStaticV4("my_admin_user", "my_admin_password", ""),
         Secure: false,
      })
      if err != nil {
         log.Fatalln(err)
      }

      // Set the Lambda function target using its ARN
      reqParams := make(url.Values)
      reqParams.Set("lambdaArn", "arn:minio:s3-object-lambda::myfunction:webhook")

      // Generate a presigned url to access the original object
      presignedURL, err := s3Client.PresignedGetObject(context.Background(), "myfunctionbucket", "testobject", time.Duration(1000)*time.Second, reqParams)
      if err != nil {
         log.Fatalln(err)
      }

      // Print the URL to stdout
      fmt.Println(presignedURL)
   }
   ```

   In the code above, replace the following values:

   - Replace `my_admin_user` and `my_admin_password` with user credentials for a MinIO deployment.
   - Replace `myfunction` with the same function name set in the `MINIO_LAMBDA_WEBHOOK_ENABLE` and `MINIO_LAMBDA_WEBHOOK_ENDPOINT` environment variables.

   To retrieve the transformed object, execute the Go code with `curl` to generate a GET request:

   ```shell
   curl -v $(go run presigned.go)
   ```

   `curl` runs the Go code and then retrieves the object with a GET request to the presigned URL. The output resembles the following:

   ```shell
   *   Trying 127.0.0.1:9000...
   * Connected to localhost (127.0.0.1) port 9000 (#0)
   > GET /myfunctionbucket/testobject?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20230406%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20230406T184749Z&X-Amz-Expires=1000&X-Amz-SignedHeaders=host&lambdaArn=arn%3Aminio%3As3-object-lambda%3A%3Amyfunction%3Awebhook&X-Amz-Signature=68fe7e03929a7c0da38255121b2ae09c302840c06654d1b79d7907d942f69915 HTTP/1.1
   > Host: localhost:9000
   > User-Agent: curl/7.81.0
   > Accept: */*
   >
   * Mark bundle as not supporting multiuse
   < HTTP/1.1 200 OK
   < Content-Security-Policy: block-all-mixed-content
   < Strict-Transport-Security: max-age=31536000; includeSubDomains
   < Vary: Origin
   < Vary: Accept-Encoding
   < X-Amz-Id-2: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
   < X-Amz-Request-Id: 17536CF16130630E
   < X-Content-Type-Options: nosniff
   < X-Xss-Protection: 1; mode=block
   < Date: Thu, 06 Apr 2023 18:47:49 GMT
   < Content-Length: 14
   < Content-Type: text/plain; charset=utf-8
   <
   hELLO, wORLD!
   * Connection #0 to host localhost left intact
   ```
