SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
.PHONY: clean requirements

help:
	@echo ''
	@echo 'Makefile for '
	@echo '    make help                 display this help information'
	@echo '    make requirements         install all dependencies'
	@echo '    make requirements.test    install testing, linting & utility tools'
	@echo '    make quality              run pylint'

requirements: requirements.test

requirements.test:
	@pip install -r requirements/testing.txt

quality:
	@pylint lambdas utils
