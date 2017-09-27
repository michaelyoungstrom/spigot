SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
.PHONY: clean requirements

help:
	@echo ''
	@echo 'Makefile for '
	@echo '    make help                 display this help information'
	@echo '    make clean                remove '
	@echo '    make requirements         install requirements for testing and deployment'
	@echo '    make quality              run pylint'
	@echo '    make package              zip the lambda code with any dependencies'
	@echo '    make deploy               push the lambda packages to an s3 bucket'

clean:
	@rm -f utils/*.pyc
	@cd lambdas/process_webhooks && make clean
	@cd lambdas/send_from_queue && make clean

requirements:
	@pip install -r requirements.txt

quality:
	@pylint lambdas utils

package:
	@cd lambdas/process_webhooks && make package
	@cd lambdas/send_from_queue && make package

deploy:
	@cd lambdas/process_webhooks && make deploy
	@cd lambdas/send_from_queue && make deploy
