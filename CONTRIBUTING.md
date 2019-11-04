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
