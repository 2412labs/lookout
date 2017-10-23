BUCKET := YOUR-DEV-BUCKET
PREFIX := YOUR-BUCKET-PREFIX
REGION := us-east-1
STACK_NAME := "lookout"
PY_VERSION := 3.6

BASE := $(shell /bin/pwd)
PYTHON := $(shell /usr/bin/which python$(PY_VERSION))

invoke:
	sam local invoke $(f) \
	 	--event lambda/$(f)/event.json \
		--env-vars env.json

package:
	sam package \
		--template-file template.yml \
		--s3-bucket $(BUCKET) \
		--s3-prefix $(PREFIX) \
		--output-template-file project.yml \
		--region $(REGION)

deploy:
	sam deploy \
		--template-file project.yml \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(REGION)

release:
	@make package deploy

deps:
	docker run -v $$PWD:/var/task -it lambci/lambda:build-python3.6 /bin/bash -c 'make do_deps'

do_deps:
	for i in $(shell find lambda -mindepth 1 -maxdepth 1 -type d); do \
		cd "$(BASE)/$$i"; \
		if [ -a "$(BASE)/$$i/requirements.txt" ]; then \
			"pip$(PY_VERSION)" \
				install \
				-t "$(BASE)/$$i/" \
				-r "$(BASE)/$$i/requirements.txt"; \
		fi; \
	done
