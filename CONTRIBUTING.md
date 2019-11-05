So you want to develop for GruntBot
=========

Setting up local DynamoDB
------------

See the following:
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.DownloadingAndRunning.html
https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html
https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Tools.CLI.html

Invoking local DynamoDB
--------

As per the above links, run this in the place that you installed it:
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb

Working with the CLI
--------

Start here:
```
aws dynamodb help
```

For example:
```
aws dynamodb create-table --cli-input-json file://schema/raid_fyi_initialization.json --endpoint-url http://localhost:8000
```

Checking on tables:
```
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

Loading up a table from a JSON:
```
aws dynamodb batch-write-item --request-items file://test_out.json --endpoint-url http://localhost:8000
```

Checking the entire contents of a table:
```
aws dynamodb scan --table-name [table name] --endpoint-url http://localhost:8000
```
