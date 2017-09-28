SHELL := /usr/bin/env bash

LAMBDA_NAME='send_from_queue'

clean:
	@echo 'Cleaning $(LAMBDA_NAME)'
	@rm -f *pyc
	@rm -f $(LAMBDA_NAME).zip
	@rm -f target
	@find . -maxdepth 1 -mindepth 1 -type d -not -name 'test' | \
		xargs -I {} rm -Rf {}

requirements:
	@echo 'Downloading dependencies for $(LAMBDA_NAME)'
	@pip install -r requirements.txt -t .

package: requirements
	@echo 'Packaging $(LAMBDA_NAME)'
	@echo $(TARGET_URL) > target
	@zip -r $(LAMBDA_NAME).zip . \
		-x test/\* -x Makefile \
		-x requirements.txt

deploy:
	@echo 'Pushing $(LAMBDA_NAME) to $(SPIGOT_S3_BUCKET)'
	@aws s3 cp $(LAMBDA_NAME).zip s3://$(SPIGOT_S3_BUCKET)
	@aws lambda update-function-code --function-name $(LAMBDA_NAME) --s3-bucket $(SPIGOT_S3_BUCKET) --s3-key $(LAMBDA_NAME).zip
