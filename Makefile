SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
.PHONY: clean requirements

help:
	@echo ''
	@echo 'Makefile for '
	@echo '    make help                 display this help information'
	@echo '    make clean                remove local dependencies and build artifacts'
	@echo '    make requirements         install requirements for testing and deployment'
	@echo '    make quality              run pylint on the unit tests and util scripts''
	@echo '    make test                 run unit tests on the lambda functions'
	@echo '    make package              zip the lambda code with any dependencies'
	@echo '    make deploy               push the lambda packages to an s3 bucket'

clean:
	@rm -f utils/*.pyc
	@cd lambdas/process_webhooks && make clean
	@cd lambdas/send_from_queue && make clean

requirements:
	@pip install -r requirements.txt
	@pip install -r lambdas/process_webhooks/requirements.txt
	@pip install -r lambdas/send_from_queue/requirements.txt

quality:
	@pylint lambdas utils

test:
	@coverage run -m pytest lambdas
	@coverage report

package:
	@cd lambdas/process_webhooks && make package
	@cd lambdas/send_from_queue && make package

deploy:
	@cd lambdas/process_webhooks && make deploy
	@cd lambdas/send_from_queue && make deploy
