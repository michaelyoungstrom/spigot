# 🚰 Spigot

A webhook queueing solution for jenkins designed with AWS.

# AWS

The following aws infrastructure is needed to utilize the code in this repository.

## Diagram


![Alt text](docs/spigot.jpg "AWS Infrastructure")

## AWS Setup

The following will need to be configured in the API Gateway:

* An API Stage Variable called **spigot_state** set to ON or OFF
* The Method Request will need:
    * A query_string parameter called **from_queue**
    * An HTTP Request header called **X-Github-Event**
* The Integration Request will need:
    * A body mapping template as follows:
    ```
    {
      "spigot_state": "$stageVariables.spigot_state",
      "from_queue": "$input.params('from_queue')",
      "body": $input.json('$'),
      "headers": {
        #foreach($header in $input.params().header.keySet())
        "$header": "$util.escapeJavaScript($input.params().header.get($header))" #if($foreach.hasNext),#end
        #end
      }
    }
    ```
* The Method Response will need:
    * A 200 HTTP Status
    * A 50 HTTP Status
* The Integration Response will need:
    * A default Lambda Error Regex mapping to a 200 Method response status
    * A Lambda Error Regex of **(\n|.)+** mapping to a 500 Method response status

The Lambdas will need:
* An environment variable called **LOG_LEVEL** with the desired cloud watch log level